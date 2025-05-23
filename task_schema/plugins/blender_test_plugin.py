from logging import getLogger, basicConfig, DEBUG
from pprint import pprint
from os import fspath, remove
from pathlib import Path
from shutil import copy2
from typing import Iterable
from re import compile, search, sub
from difflib import SequenceMatcher as smatch

import pandas

if __name__ == "__main__":
    # these are only required if the module is executed stand alone
    import sys
    from os import fspath

    sys.path.append(fspath(Path(__file__).parent.parent.parent))

from task_schema.plugins.base_plugin import BaseTask
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


class BlenderTestPlugin(ShotgridPlugin):
    TITLE = "BlenderTest"
    # PLUGIN_UUID = "949f437a-c538-4f62-bb47-0d053250846e"
    SG_PROJECT_ID = 518
    SHOTGRID_URL = "https://mondotv.shotgunstudio.com"

    title = "BlenderTest"
    _active_entities = ["My Tasks", "Asset", "Sequence", "Episode", "Shot"]
    add_tasks_from_plugin_kwargs = {"sg_entity_type": "My Tasks"}
    create_file_ext = ["from selected", "psd", "ma", "spp", "xlsx"]
    uses_deadline = False
    bdlregex = r"bdt_\d\d\d_.*\.xlsx"

    def __new__(cls: "BlenderTestPlugin", *args, **kwargs) -> "BlenderTestPlugin":
        cls._local_root = Path(cls.env_handler.get_env("BLENDERTEST_LOCAL_PATH"))
        cls._server_root = Path(
            cls.env_handler.get_env(
                "BLENDERTEST_SERVER_PATH",
                Path("\\\\qsrv01.mondotvcanarias.lan\\demoproj_blender\\BlenderTest"),
            )
        )
        cls.TEMPLATES_FOLDER = Path(cls._server_root, "production/publish/templates")
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
        # self._toolbars += [
        #     [MayaToolbar,"Maya Toolbar","right"],
        # ]
        self._preview_location = Path("preview")

        self.plugin_task_filters += [
            ["sg_status_list", "not_in", ["na", "wtg"]],
            ["entity.Asset.sg_status_list", "not_in", ["na"]],
        ]

        self.custom_artist_login_field = "code"  # "sg_username"
        self.custom_artist_entity_name = "CustomEntity04"
        self.publishedfile_artist_entity_field = "sg_mondo_artist"
        self.timelog_artist_entity_field = "sg_mondo_artist"
        self.version_artist_entity_field = "sg_mondo_artist"
        self.custom_artist_task_field = "sg_mondo_artist"  # MondoArtist

        self._version_includes_entity = True
        self.version_regex = r"(?<=_[wv])\d\d\d"
        self._naming_regex = [
            r"^bdt_[a-z]{2}_[A-Za-z0-9]+_[A-Za-z0-9]+_[a-z]+_[wv]\d\d\d.*",
            r"^bdt(_\d\d\d)_([a-z]+)_[wv]\d\d\d.*",
            r"^bdt(_\d\d\d){2}_([a-z]+)_[wv]\d\d\d.*",
            r"^bdt(_\d\d\d){3}_([a-z]+)_[wv]\d\d\d.*",
            r"^bdt(_\d\d\d){3}(_[a-z]+){1,3}_[wv]\d\d\d.*",
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

        self._dict_file_templates = {
            "bdl": Path(self.TEMPLATES_FOLDER, "bdt_template_bdl.xlsx"),
            "skt": Path(self.TEMPLATES_FOLDER, "bdt_template_psd.psd"),
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
            ],
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
        self, code, entity_type, task, step, asset_type, state="work", *args, **kwargs
    ):
        slug: str = None
        if entity_type == "Asset":
            asset_name, asset_variant = code.split("_")

            # Z:\PROJECTS\GRISU\PROD\assets\work\ch\bee\queen-tv01\lookDevStep\lookDevExport\files
            # Z:\PROJECTS\GRISU\PROD\episodes\work\102\220\010-01\animationStep\blocking

            slug = Path(
                f"production/{state}/assets",
                asset_type,
                asset_name,
                asset_variant,
                task,
            )

        elif entity_type == "Episode":
            slug = Path(f"production/{state}/episodes", code, task)

        elif entity_type == "Shot":
            slug = Path(
                f"production/{state}/episodes",
                code.split("_")[1],
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
            v, last_file = self.return_last_file(ext)
            v = version or v
            match task.entity_type:
                case "Asset":
                    file_name = f"bdt_{type_}_{link}_{task_name}_w{v+1:03}"
                case "Shot":
                    file_name = f"bdt_{link}_{task_name}_w{v+1:03}"
                case "Episode":
                    file_name = f"bdt_{link}_{task_name}_w{v+1:03}"
            if last_file is None:
                last_file = self._dict_file_templates.get(task_name)
                if not last_file:
                    last_file = Path(self.TEMPLATES_FOLDER)

            return {
                "local_path": Path(task.local_path),
                "file_name": file_name,
                "previous_file": last_file,
                "full_file_name": Path(task.local_path, f"{file_name}.{ext[0]}"),
            }

    def work_to_publish(self, task: BaseTask = None):
        task = task or self.last_task_clicked
        if task is None:
            return None, None
        publish_local_path = Path(
            *[p if p != "work" else "publish" for p in task.local_path.parts]
        )
        publish_server_path = Path(
            *[p if p != "work" else "publish" for p in task.server_path.parts]
        )
        return publish_local_path, publish_server_path

    def return_next_publish_file(self, work_file: Path):
        task = self.last_task_clicked
        if task is None:
            return None, None
        publish_local_path, publish_server_path = self.work_to_publish(task)
        v = self.return_last_version_number(publish_server_path)
        task_name = self.task_long_to_short(task.name)
        link = task.link_name
        type_ = task.asset_type
        ext = work_file.suffix
        match task.entity_type:
            case "Asset":
                file_name = f"bdt_{type_}_{link}_{task_name}_v{v+1:03}"
            case "Shot":
                file_name = f"bdt_{link}_{task_name}_v{v+1:03}"
            case "Episode":
                file_name = f"bdt_{link}_{task_name}_v{v+1:03}"

        return Path(publish_local_path, f"{file_name}{ext}"), Path(
            publish_server_path, f"{file_name}{ext}"
        )

    def create_assets_from_bdl(self, dict_with_items: dict, excel_file: Path):
        logger.debug("Starting asset generation phase.")
        logger.debug("Collecting SG data.")
        created_assets = self.return_all_assets()
        created_episodes = self.return_all_episodes()
        project = {"type": "Project", "id": int(self.SG_PROJECT_ID)}
        episode = f"{excel_file.name.split('_')[1]}"

        if episode not in created_episodes:
            logger.debug(f"Episode not exists. Generating episode {episode}")
            ep_task_template = self.sg.find_one(
                "TaskTemplate", [["code", "is", f"gwaio_episode"]]
            )
            ep = self.sg.create(
                "Episode",
                {
                    "code": episode,
                    "project": project,
                    "task_template": ep_task_template,
                },
            )
            created_episodes.update({episode: ep})
        else:
            ep = created_episodes[episode]
            logger.debug(f"Episode {episode} found")

        md5hash, sha1hash = hash_file(excel_file)
        description = f"Hashes: \nmd5: '{md5hash}'\nsha1: '{sha1hash}'"

        match_version = self.sg.find_one(
            "Version",
            [["description", "is", description]],
        )
        if not match_version:
            logger.debug(f"Starting generation of BDL version in SG. Episode {episode}")
            logger.debug("Hashing BDL file.")
            sg_task = self.sg.find_one(
                "Task", [["entity", "is", ep], ["content", "is", "bdl"]]
            )
            logger.debug(f"BDL task found {sg_task}")

            class PseudoBaseTask:
                entity = ep
                task_entity = sg_task
        
            result = self.publish_version(PseudoBaseTask, excel_file, description)
            if not result.get("success"):
                raise Exception(
                    f"Error while publishing BDL file.\n{result.get('message')}"
                )
            logger.debug(f"Published BDL version in SG episode {episode}.")


        for key, value in dict_with_items.items():
            logger.debug(f"Working on item {value}")
            if not value["status"]:
                logger.debug(f"Error on item {value}. Fix it")
                yield True
                continue
            tags = (
                [value["series"][5]]
                if "," not in value["series"][5]
                else value["series"][5].split(",")
            )
            parents = (
                [value["series"][3]]
                if "," not in value["series"][3]
                else value["series"][3].split(",")
            )

            if value["asset_name"] not in created_assets:
                task_template = self.sg.find_one(
                    "TaskTemplate",
                    [["code", "is", f"gwaio_asset_{value['series'][0]}"]],
                )
                logger.debug(f"Task template found {task_template}.")
                data = {
                    "code": value["asset_name"],
                    "project": project,
                    "episodes": [ep],
                    "sg_created_for_episode": ep,
                    "sg_asset_type": value["series"][0],
                    "task_template": task_template,
                    "description": value["series"][4],
                    # "tags": tags,
                }
                logger.debug(data)
                created_asset = self.sg.create("Asset", data)
                logger.debug(f"Asset {value['asset_name']} was created.")
            else:
                created_asset = created_assets[value["asset_name"]]

            self.sg.update(
                "Asset",
                created_asset["id"],
                {
                    "episodes": [ep],
                    "description": value["series"][4],
                    "sg_parent_assemblies": [
                        v for k, v in created_assets.items() if k in parents
                    ],
                },
                multi_entity_update_modes={
                    "episodes": "add",
                    "sg_parent_assemblies": "add",
                },
            )
            created_assets[value["asset_name"]] = created_asset

            yield created_asset

    def publish_version(
        self,
        task: BaseTask,
        file: Path,
        description: str = "",
    ) -> bool:
        try:
            publish_local_file, publish_server_file = self.return_next_publish_file(
                file
            )
            if not publish_local_file or not publish_server_file:
                return {
                    "success": False,
                    "message": "The file could not be published on the server. Check that you have selected a correct file.",
                    "error": "The file could not be published on the server. Check that you have selected a correct file.",
                    "entity": None,
                }
            publish_local_file.parent.mkdir(exist_ok=True, parents=True)
            publish_server_file.parent.mkdir(exist_ok=True, parents=True)
            logger.debug(f"Publish version: {file} -> {publish_server_file}")
            copy2(file, publish_local_file)
            try:
                copy2(file, publish_server_file)
            except Exception as e:
                remove(publish_local_file)
                raise Exception(e)
        except Exception as e:
            return {
                "success": False,
                "message": f"Upload failed. {str(e)}",
                "error": str(e),
                "entity": None,
            }
        result = super().publish_version(task, publish_local_file, description)
        logger.debug(f"Shotgrid publish result: {result}")
        if not result.get("success"):
            remove(publish_local_file)
            remove(publish_server_file)

        return result

    def is_published_file(self, file):
        return (
            self.sg.find_one(
                "PublishedFile",
                [["description", "is", str(hash_file(file))]],
            )
            != None
        )

    def return_seq_and_shot_from_clipname(self, clip_name: str):
        # * FROM CLIP NAME: AC101_SC003_TK0
        shot = clip_name.split(" ")[-1]
        (
            _,
            ep,
            sq,
            sh,
        ) = clip_name.split("_")
        return f"bdt_{ep}_{sq}", f"bdt_{ep}_{sq}_{sh}"

    def read_excel(self, excel: Path):
        episode = excel.name.split("_")[1]
        existing_assets = self.return_all_assets()
        data_frame = (
            pandas.read_excel(excel, usecols=[0, 1, 2, 3, 4, 5])
            # .replace(regex=[" "], value="_")
            # .replace(regex=[r"_$"], value="")
        )
        data_frame.fillna("", inplace=True)
        results = dict()
        dupes = data_frame.duplicated(
            subset=data_frame.columns[1:3].tolist(), keep=False
        )

        # row: pandas.Series
        for i, row in data_frame.iterrows():
            logger.debug(f"Reading data: {[*row]}")
            try:
                asset_type, code, variant, parent_assets, description, tags = row[:6]
            except ValueError as e:
                logger.debug(f"Failed to parse row: {[*row]}")
                raise (e)

            asset_name = f"{code}_{variant}"

            results[i] = {
                "series": [content for content in row[:6].tolist()],
                "errors": list(),
                "warnings": list(),
                "episode": f"{episode}",
                "asset_name": asset_name,
                "exists": asset_name in existing_assets,
                "status": True,
            }

            if dupes[i]:
                results[i]["errors"].append("This asset is repeated.")

            if asset_type not in ["ch", "pr", "ve", "sp", "mp", "fx", "en"]:
                results[i]["errors"].append(f"Unknown asset type '{asset_type}'")

            if parent_assets:
                if not "," in parent_assets:
                    parent_assets = [parent_assets]
                else:
                    parent_assets = parent_assets.split(",")

                for parent_asset in parent_assets:
                    if parent_asset not in existing_assets:
                        candidate = next(
                            (
                                k
                                for k in existing_assets
                                if smatch(None, k, parent_asset).ratio() > 0.8
                            ),
                            None,
                        )
                        results[i]["errors"].append(
                            f"Parent asset {parent_asset} "
                            + "does not exist in SG, please create it first. "
                            + ("\n" if candidate else "")
                            + f"{('Maybe you meant '+ candidate + '?') if candidate is not None else ''}"
                        )

            if asset_name in existing_assets:
                results[i]["exists"] = True
                results[i]["warnings"].append(f"Asset already exists")

            for content in [*row[:2]]:
                if content in (None, ""):
                    results[i]["errors"].append("There are some empty fields.")

            for tag in (code, variant):
                if not tag.replace("_", "").isalnum() and tag != "":
                    results[i]["errors"].append(
                        f"There are non alphanumeric values: "
                        f"{sub('[^0-9a-zA-Z]+', '*', tag)}"
                    )

            results[i]["status"] = len(results[i]["errors"]) == 0

        return [*data_frame.columns[:6].tolist()], results


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from os import environ

    basicConfig()
    logger = getLogger()
    logger.level = DEBUG

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

    app = QApplication()
    plugin = BlenderTestPlugin()
