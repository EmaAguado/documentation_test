from logging import getLogger, basicConfig, DEBUG
import os
from os import fspath
from pathlib import Path
from typing import Iterable
from re import compile, sub

import pandas

if __name__ == "__main__":
    # these are only required if the module is executed stand alone
    import sys
    from os import fspath

    sys.path.append(fspath(Path(__file__).parent.parent.parent))

from task_schema.plugins.shotgrid_plugin import ShotgridPlugin
from launcher.qtclasses.toolbar_maya import MayaToolbar
from utilities.pipe_utils import hash_file

logger = getLogger(__name__)

try:
    from utilities.maya.scripts import (
        batch_shot_version_base,
        batch_playblast,
        batch_turntable,
        batch_arnold_render,
        batch_turntable_arnold,
        batch_qa,
    )
except ImportError as e:
    logger.debug(e)


class GwaioProjectPlugin(ShotgridPlugin):
    TITLE = "Gwaio"
    # PLUGIN_UUID = "949f437a-c538-4f62-bb47-0d053250846e"
    SG_PROJECT_ID = 452
    SHOTGRID_URL = "https://mondotv.shotgunstudio.com"

    title = "Gwaio"
    _active_entities = ["My Tasks", "Asset", "Sequence", "Episode", "Shot"]
    add_tasks_from_plugin_kwargs = {"sg_entity_type": "My Tasks"}
    create_file_ext = ["from selected", "psd", "ma", "spp"]
    uses_deadline = False
    bdlregex = r"gwa_BDL_\d\d\d.*"

    def __new__(cls: "GwaioProjectPlugin", *args, **kwargs) -> "GwaioProjectPlugin":
        cls._local_root = Path(cls.env_handler.get_env("GWAIOPROJECT_LOCAL_PATH"))
        cls._server_root = Path(
            cls.env_handler.get_env(
                "GWAIOPROJECT_SERVER_PATH",
                Path("\\\\qsrv01.mondotvcanarias.lan\\data0\\PROJECTS\\GWAIOPROJECT"),
            )
        )
        cls.TEMPLATES_FOLDER = Path(cls._server_root, "templates")
        cls.BDLS_FOLDER = Path(cls._server_root, "BDL")
        cls.BDLS_PATH = Path(cls._server_root, "BDL")

        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # Because the batches may fail to be imported, we have to have
            # this in a try-except block
            self._jobs += [
                batch_shot_version_base,
                batch_playblast,
                batch_turntable,
                batch_arnold_render,
                batch_turntable_arnold,
                batch_qa,
            ]
        except NameError as e:
            logger.debug("Failed to add jobs to plugin.")
            logger.debug(e)
        self._toolbars += [
            [MayaToolbar,"Maya Toolbar","right"],
        ]
        self._preview_location = Path("preview")

        self.plugin_task_filters += [
            ["sg_status_list", "not_in", ["na", "wtg"]],
            ["entity.Asset.sg_status_list", "not_in", ["na"]],
        ]

        self.custom_artist_login_field = "code"#"sg_username"
        self.custom_artist_entity_name = "CustomEntity04"
        self.publishedfile_artist_entity_field = "sg_mondo_artist"
        self.timelog_artist_entity_field = "sg_mondo_artist"
        self.version_artist_entity_field = "sg_mondo_artist"
        self.custom_artist_task_field = "sg_mondo_artist"#MondoArtist


        self._version_includes_entity = True
        self.version_regex = r"\d\d\d"
        self._naming_regex = [
            r"^gwa_[a-z]{2}_[A-Za-z0-9]+_[A-Za-z0-9]+_[a-z]+_\d\d\d.*",
            r"^gwa(_\d\d\d){3}_([a-z]+)_v\d\d\d.*",
            r"^gwa(_\d\d\d){3}(_[a-z]+){1,3}_v\d\d\d.*",
        ]
        self._upload_status = "rev"
        self._fps = 25
        self._starting_frame = 101
        self._dict_previous_tasks = {
            "line": {"task": "sketch", "step": "ConceptArtStep"},
            "color": {"task": "line", "step": "ConceptArtStep"},
            "uvs": {"task": "model", "step": "ModelingStep"},
            "shading": {"task": "uvs", "step": "ModelingStep"},
            "fur": {"task": "shading", "step": "LookDevStep"},
            "blendShapes": {"task": "model", "step": "ModelingStep"},
            "rigging": {"task": "model", "step": "ModelingStep"},
            "animLib": {"task": "rigging", "step": "RiggingStep"},
            "blocking": {"task": "layout", "step": "LayoutStep"},
            "refine": {"task": "blocking", "step": "AnimationStep"},
            "fix": {"task": "refine", "step": "AnimationStep"},
            "fxclean": {"task": "fxrough", "step": "FxStep"},
            "lighting": {"task": "prelight", "step": "LightingStep"},
        }
        self._asset_folder_regex = fspath(self.local_root) + "/PROD/assets/work/*/*/*"
        self._asset_folder = fspath(self.local_root) + "/PROD/assets/work"
        self._qa_config = {
            "modelProd": [
                "CheckRepeatedNameNodes",
            ],
            "modelHigh": [
                "CheckRepeatedNameNodes",
                "CheckPastedNodes",
                "CheckUnknownNodes",
            ],
            "lighting": [
                "CheckStartFrame",
            ]
        }
        self._compulsory_publish_fields = ["description"]
        self._edl_target_task = "animatic"
        self._edl_shot_prefix = ""
        self._edl_sequence_prefix = ""
        self.edl_sequence_regex = compile(r"(?<=AP_SC_)\d{4}")
        self._edl_shot_regex = compile(r"(?<=gwa_)\d{3}_\d{3}_\d{3}")
        self.edl_version_regex = compile(r"(?<=_[Vv])\d\d\d")
        self._shot_task_tpl_id = 1069
        self._episode_edl_workflow = True
        self._edl_episode_regex = compile(r"gwa_\d{3}")
        self.CUSTOM_MAYA_TOOLS = Path(self.server_root, "tools/maya_tools")


    def get_task_filesystem(
        self, code, entity_type, task, step, asset_type, *args, **kwargs
    ):
        slug: str = None
        if entity_type == "Asset":
            asset_name, asset_variant = code.split("_")

            # Z:\PROJECTS\GRISU\PROD\assets\work\ch\bee\queen-tv01\lookDevStep\lookDevExport\files
            # Z:\PROJECTS\GRISU\PROD\episodes\work\102\220\010-01\animationStep\blocking

            slug = Path(
                "PROD/assets/work", asset_type, asset_name, asset_variant, step, task
            )

        elif entity_type == "Episode":
            slug = Path("PROD/episodes/work", code[4:], step, task)

        elif entity_type == "Shot":
            slug = Path(
                "PROD/episodes/work",
                code.split("_")[1],
                "sequences",
                *code.split("_")[2:4],
                step,
                task,
            )

        local_path = Path(self.local_root, slug)
        server_path = Path(self._server_root, slug)

        if slug is None:
            local_path = None
            server_path = None

        return local_path, server_path

    def file_added_callback(self) -> None:
        if (
            self.sg.find_one(
                "Task",
                [["id", "is", self.last_task_clicked.task_entity.get("id")]],
                ["sg_status_list"],
            ).get("sg_status_list")
            == "rdy"
        ):
            self.sg.update(
                "Task",
                self.last_task_clicked.task_entity.get("id"),
                {"sg_status_list": "ip"},
            )

    def return_next_version_name(self, ext: Iterable, version: int = None) -> dict:
        # gri_102_060_040_01_light_rfn_002.mov
        # gri_pr_toast_standard-tv01_look_lde_003_standardRenderTurntable
        task = self.last_task_clicked
        if task is not None:
            task_name = self.task_long_to_short(task.name)
            step = self.task_long_to_short(task.step)
            link = task.link_name
            type_ = task.asset_type
            v, last_file = self.return_last_file(ext, Path("files"))
            v = version or v

            match task.entity_type:
                case "Asset":
                    file_name = f"gwa_{type_}_{link}_{task_name}_{v+1:03}"
                case "Shot":
                    file_name = f"{link}_{task_name}_v{v+1:03}"
                case "Episode":
                    file_name = f"gwa_{link}_{task_name}_{v+1:03}"
            if last_file is None:
                last_file = Path(self.TEMPLATES_FOLDER)

            return {
                "local_path": Path(task.local_path, "files"),
                "file_name": file_name,
                "previous_file": last_file,
                "full_file_name": Path(task.local_path, f"{file_name}.{ext[0]}")
            }

    def create_assets_from_bdl(self, dict_with_items: dict, excel_file: Path):
        logger.debug("Starting asset generation phase.")
        logger.debug("Collecting SG data.")
        created_assets = self.return_all_assets()
        created_episodes = self.return_all_episodes()

        episode = f"{excel_file.name.split('_')[2]}"

        if episode not in created_episodes:
            ep = self.sg.create(
                "Episode", {"code": episode, "project": project}
            )
            created_episodes.update({episode: ep})
        else:
            ep = created_episodes[episode]

        project = {"type": "Project", "id": int(self.SG_PROJECT_ID)}

        logger.debug("Starting generation of BDL version in SG.")
        logger.debug("Hashing BDL file.")
        md5hash, sha1hash = hash_file(excel_file)
        sg_task = self.sg.find_one(
            "Task", [["entity", "is", ep], ["content", "is", "bdl"]]
        )

        description = f"Hashes: \nmd5: '{md5hash}'\nsha1: '{sha1hash}'"

        class PseudoBaseTask:
            entity = ep
            task_entity = sg_task

        logger.debug("Creating excel version in SG.")
        xlsx_version = self.publish_version(PseudoBaseTask, excel_file, description)
        logger.debug(f"Excel version created in SG: {xlsx_version}")

        for key, value in dict_with_items.items():
            print(value["series"])
            logger.debug(f"Working on item {value}")

            if not value["status"]:
                continue

            task_template = self.sg.find_one(
                "TaskTemplate",
                [["code", "is", f"FT - Asset - {value['series'][1]}"]],
            )
            data = {
                "code": value["asset_name"],
                "project": project,
                "sg_status_list": value["series"][4],
                "episodes": [ep],
                "sg_created_for_episode": ep,
                "task_template": task_template,
            }

            if value["asset_name"] not in created_assets:
                created_asset = self.sg.create("Asset", data)
                logger.debug(f"Asset {value['asset_name']} was created.")
                created_assets[value["asset_name"]] = created_asset
            else:
                created_asset = created_assets[value["asset_name"]]

            art_bid, model_bid, shading_bid, rig_bid = value["series"][7:11]

            for step, bid in [
                ("ConceptArtStep", art_bid),
                ("ModelingStep", model_bid),
                ("LookDevStep", shading_bid),
                ("RiggingStep", rig_bid),
            ]:
                if not bid:
                    continue
                all_tasks = self.sg.find(
                    "Task",
                    [
                        ["entity", "is", created_asset],
                        ["step.Step.code", "is", step],
                        ["sg_status_list", "is_not", "na"],
                    ],
                    ["content", "step.Step.code"],
                )
                for task in all_tasks:
                    self.sg.update(
                        "Task",
                        task["id"],
                        {"est_in_mins": bid / len(all_tasks) * 8 * 60},
                    )

            self.sg.update(
                "Asset",
                created_asset["id"],
                {
                    "episodes": [ep],
                    "sg_priority": value["priority"],
                    "description": value["comments"],
                },
                multi_entity_update_modes={"episodes": "add", "parents": "add"},
            )
            yield created_asset

    def return_seq_and_shot_from_clipname(self, clip_name: str):
        # * FROM CLIP NAME: AC101_SC003_TK0
        shot = clip_name.split(" ")[-1]
        _, ep, sq, sh, = clip_name.split("_")
        return f"gwa_{ep}_{sq}", f"gwa_{ep}_{sq}_{sh}"
    
    def read_excel(self, excel: Path):
        episode = excel.name.split("_")[2].replace("AC", "")
        existing_assets = self.return_all_assets()
        data_frame = (
            pandas.read_excel(excel, usecols=[0, 1, 2, 3])
            .replace(regex=[" "], value="_")
            .replace(regex=[r"_$"], value="")
        )
        data_frame.fillna("", inplace=True)
        df_tags = pandas.read_excel(excel, usecols=[4])
        df_tags.fillna("", inplace=True)
        results = dict()
        dupes = data_frame.duplicated(
            subset=data_frame.columns[1:3].tolist(), keep=False
        )

        row: pandas.Series
        for i, row in data_frame.iterrows():
            tags = (
                df_tags.iloc[i][0]
                if df_tags.columns.to_list()[0].lower() == "tags"
                else ""
            )
            asset_type, code, variant, prod_type = row[:4]
            asset_name = f"{code}_{variant}" if variant != "" else code
            asset_name = f"{asset_name.upper()[0]}{asset_name[1:]}"

            results[i] = {
                "series": [content for content in row[:4].tolist()] + [tags],
                "errors": list(),
                "episode": episode,  # AC
                "asset_name": asset_name,
                "exists": asset_name in existing_assets,
                "status": True,
            }

            if dupes[i]:
                results[i]["errors"].append("This asset is repeated.")

            if asset_type not in ["PR", "CH", "SFX", "FX", "BG", "SP", "RF"]:
                results[i]["errors"].append(f"Unknown asset type '{asset_type}'")

            for content in [*row[:2], row[3]]:
                if content in (None, ""):
                    results[i]["errors"].append("There are some empty fields.")

            for tag in (code, variant):
                if not tag.replace("_", "").isalnum() and tag != "":
                    results[i]["errors"].append(
                        f"There are non alphanumeric values: "
                        f"{sub('[^0-9a-zA-Z]+', '*', tag)}"
                    )

            if prod_type in ("CR", "VR"):
                if asset_name in existing_assets:
                    results[i]["exists"] = True
                    if (
                        existing_assets[asset_name].get(
                            "sg_created_for_episode.Episode.code"
                        )
                        != episode  # AC
                    ):
                        results[i]["errors"].append(
                            f"Asset exists and it is marked as {prod_type}"
                        )

            elif prod_type == "TR" and asset_name not in existing_assets:
                results[i]["errors"].append(
                    "Asset does not exist but it is marked as TR"
                )

            elif prod_type == "TR" and asset_name in existing_assets:
                results[i]["exists"] = True

            else:
                results[i]["errors"].append(f"Unknown production type {prod_type}")

            results[i]["status"] = len(results[i]["errors"]) == 0

        return [*data_frame.columns[:4].tolist(), "Tags"], results
    
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from os import environ

    basicConfig()
    logger = getLogger()
    logger.level = DEBUG

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

    app = QApplication()
    plugin = GwaioProjectPlugin()
