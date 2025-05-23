from logging import getLogger, basicConfig, DEBUG
from pathlib import Path
from typing import Iterable, TYPE_CHECKING
from re import sub, compile
from difflib import SequenceMatcher as smatch
from os import fspath


if __name__ == "__main__":
    # these are only required if the module is executed stand alone
    import sys

    sys.path.append(fspath(Path(__file__).parent.parent.parent))

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication()
    from utilities.pipe_utils import load_dotenv

    load_dotenv()
    from launcher.qtclasses.dialog_env_handler import EnvironmentHandler

    EnvironmentHandler()

from task_schema.plugins.shotgrid_plugin import ShotgridPlugin, ShotgridInstance
from launcher.qtclasses.toolbar_maya import MayaToolbar
from utilities.pipe_utils import TimeoutPath, hash_file
from mondo_scripts.excel_utils import read_xlsx, process_string

try:
    from utilities.maya.scripts import (
        # batch_playblast,
        # batch_turntable,
        # batch_arnold_render,
        # batch_turntable_arnold,
        # batch_ft_mayapy_base,
        batch_ft_generate_qc,
        # batch_ft_fml_houdini,
        batch_ft_render_houdini,
        batch_ft_render_houdini_v2,
        batch_ft_cache_houdini,
        batch_ft_render_nuke,

    )
except Exception as e:
    print("Error BATCH:")
    print(e)
    pass

logger = getLogger(__name__)


class FurryTailsPlugin(ShotgridPlugin):
    TITLE = "FT"
    PLUGIN_UUID = "9dce2bce-c3aa-46c8-9f91-ead9f2c29e34"
    SG_PROJECT_ID = 829
    SHOTGRID_URL = "https://tomavision.shotgunstudio.com"
    SHOTGRID_SCRIPT_NAME = "FurryTailsManager"
    SHOTGRID_API_KEY = "gRwah-wopzohrkpf9lxdayxdm"

    # MAYA_LAUNCHER = Path("PIPELINE/dev/mtv/bat/launchMaya.bat")
    # title = "Furry Tails Plugin"
    _active_entities = ["My Tasks", "Asset", "Sequence", "Episode", "Shot"]
    # custom_artist_entity = "sg_tomavision_artist_assignment.CustomEntity07.code"
    custom_artist_entities = [
        "sg_tomavision_artist_assigned",
        "sg_tomavision_artist_assignment.CustomEntity07.code",
    ]
    title = "Furry Tails"
    uses_deadline = True
    add_tasks_from_plugin_kwargs = {"sg_entity_type": "My Tasks"}
    create_file_ext = ["from selected", "psd", "ma", "spp", "hip", "nk"]
    bdlregex = r"BDL_FT_(Film|Teaser|[A-Z][A-Za-z0-9]+)_.*"
    task_subfolders = {
        "all": ["files", "preview"],
        "shading": ["textures", "export", "files/maya", "files/painter"],
        "fur": ["masks", "collections"],
    }
    asset_task_fields_dict = {
        "Asset": {
            "sketch": "sg_asset_sketch_task",
            "line": "sg_asset_line_task",
            "color": "sg_asset_color_task",
            "expressions": "sg_asset_expressions_task",
        },
    }

    def __new__(cls: "FurryTailsPlugin", *args, **kwargs) -> "FurryTailsPlugin":
        # cls._local_root = Path(cls.env_handler.get_env("FURRYTAILS_LOCAL_PATH"))
        cls._local_root = Path(cls.env_handler.get_env("FT_LOCAL_PATH"))
        if (p := TimeoutPath("\\\\192.168.1.21\\FT_FurryTails")).exists():
            root_candidate = p
        elif (p := TimeoutPath("\\\\100.96.1.34\\FT_FurryTails")).exists():
            root_candidate = p
        else:
            root_candidate = None
        cls._server_root = Path(
            # cls.env_handler.get_env("FURRYTAILS_SERVER_PATH", root_candidate)
            cls.env_handler.get_env("FT_SERVER_PATH", root_candidate)
        )
        cls.RENDER_FARM_ROOT = Path("\\\\192.168.1.21\\FurryTails")
        cls.RENDER_FARM_FFMPEG_PATH = Path("\\\\192.168.1.21\\Render_Farm\\ffmpeg")
        cls.TEMPLATES_FOLDER = Path(cls._server_root, "03_FT_TEMPLATES/")
        cls.BDLS_FOLDER = Path(cls._server_root, "01_FT_WORKS")
        cls.SL_SERVER_PATH = Path(cls._server_root, "02_FT_RESOURCES/ANIMLIB")
        cls.GWAIO_DEADLINE_REPO_PATH = fspath(cls._server_root).replace(
            "FT_FurryTails", "Render_Farm/Repository"
        )
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.OCIO_FILE = Path(
            self.server_root,
            "02_FT_RESOURCES/PIPELINE/ocio_configs/Maya2022-default/config.ocio",
        )
        self.GWAIO_MAYA_LIGHT_TEMPLATE = fspath(
            Path(self._local_root, "/03_FT_TEMPLATES/maya/lookdev_studio.ma")
        )
        self.CUSTOM_MAYA_TOOLS = Path(
            self.server_root, "02_FT_RESOURCES/PIPELINE/utilities/maya"
        )
        self.plugin_task_filters = [
            ["sg_status_list", "not_in", ["na", "omt"]],
            ["project.Project.id", "is", int(self.SG_PROJECT_ID)],
            ["entity.Shot.sg_status_list", "not_in", ["omt"]],
            ["entity.Sequence.sg_status_list", "not_in", ["omt"]],
            ["entity.Asset.sg_status_list", "not_in", ["omt"]],
            ["entity.Episode.sg_status_list", "not_in", ["omt"]],
            {
        "filter_operator": "any",
        "filters": [
            ["entity.Episode.id", "is", 700],
            ["entity.Asset.episodes", "is", {"type": "Episode", "id":700}],
            ["entity.Sequence.episode", "is", {"type": "Episode", "id":700}],
            ["entity.Shot.sg_sequence.Sequence.episode", "is", {"type": "Episode", "id":700}]
        ]
    },
        ]
        try:
            self._jobs += [
                # batch_playblast,
                # batch_turntable,
                # batch_arnold_render,
                # batch_turntable_arnold,
                batch_ft_generate_qc,
                # batch_ft_fml_houdini,
                batch_ft_render_houdini,
                batch_ft_render_houdini_v2,
                batch_ft_cache_houdini,
                batch_ft_render_nuke,
                # batch_ft_mayapy_base
            ]
        except Exception as e:
            logger.debug("Failed to add jobs to plugin.")
            logger.debug(e)
        self._toolbars += [[MayaToolbar,"Maya Toolbar","right"]]

        self._edl_target_task = "animatic"
        self._edl_shot_prefix = "sh"
        self._edl_sequence_prefix = "sq"
        # self.edl_sequence_regex = compile(r"(?<=FT_)[A-Za-z]*_\d\d\d")
        self.edl_sequence_regex = compile(r"(?<=AP_SC_)\d{4}")
        # self._edl_shot_regex = compile(r"(?<=0)\d{3}(?=\-)")
        self._edl_shot_regex = compile(r"(?<=0)\d{3}$")
        # self.edl_version_regex = compile(r"(?<=_V)\d\d\d")
        self.edl_version_regex = compile(r"(?<=AP_SC_\d{4}_V)\d{3}")
        self._edl_episode_regex = compile(r"(?<=FT_)[A-Z][a-zA-Z0-9]+")
        self._edl_ep_in_sq = False
        self._shot_task_tpl_id = 587
        self._preview_location = Path("preview")
        self._textures_location = Path("textures")
        self._export_location = Path("export")
        self._fps = 24
        # self._playblast_res = "2048x858"
        self._playblast_res = "1920x1080"
        self._starting_frame = 1001
        self.publishedfile_artist_entity_field = "sg_tomavision_artist"
        self.timelog_artist_entity_field = "sg_tomavision_artist"
        self.custom_artist_login_field = "sg_email"
        self.custom_artist_entity_name = "CustomEntity07"
        self.custom_artist_task_field = "sg_tomavision_artist_assigned"
        self.version_artist_entity_field = "sg_tomavision_artist"
        self._qa_config = {
            "all_tasks": [
                "CheckRepeatedNameNodes",
                "CheckPastedNodes",
                # "CheckEmptyNamespaces",
                "CheckIntermediateShapes",
                "CheckNotConnectedGroupID",
                "CheckEnviromentVariables",
                "CheckUnusedShadingNodes",
                # "CheckImagePlanes",
                "CheckScriptNodes",
                # "CheckMeshesWhichHaveAnimation",
                "CheckMayaFileNamingConvention",
                "CheckUnusedAnimCurves",
                # "CheckUnweldedVertex",
                "CheckEmptyTransforms",
                "CheckEmptyReferenceNodes",
                "CheckCorrectFPS",
            ],
            "model": [
                "CheckLights",
                "CheckUnknownNodes",
                "CheckOutlinerAssets",
                # "CheckNodeHistory",
                # "CheckTopology",
                "CheckResidualCams",
                "CheckNoNamespaces",
                "CheckAssetsBaseGroupsTransforms",
            ],
            "modelBlocking": [
                "CheckLights",
                "CheckUnknownNodes",
                "CheckOutlinerAssets",
                # "CheckNodeHistory",
                "CheckResidualCams",
                "CheckNoNamespaces",
                "CheckAssetsBaseGroupsTransforms",
            ],
            "uvs": [
                "CheckUnknownNodes",
                "CheckLights",
                "CheckOutlinerAssets",
                "CheckResidualCams",
                # "CheckNodeHistory",
                # "CheckTopology",
                "CheckNoNamespaces",
                "CheckAssetsBaseGroupsTransforms",
            ],
            "rigging": [
                "CheckLights",
                "CheckOutlinerAssets",
                # "CheckTopology",
                "CheckResidualCams",
                "CheckAssetsBaseGroupsTransforms",
            ],
            "riggingLayout": [
                "CheckLights",
                "CheckOutlinerAssets",
                "CheckResidualCams",
                "CheckAssetsBaseGroupsTransforms",
            ],
            "shading": [
                "CheckLights",
                "CheckUnknownNodes",
                # "CheckNodeHistory",
                "CheckOutlinerAssets",
                "CheckResidualCams",
                "CheckNoNamespaces",
                # "CheckTopology",
                "CheckAssetsBaseGroupsTransforms",
            ],
            "story" : [
                "CheckEndFrame",
                "CheckStartFrame",
            ],
            "layout" : [
                "CheckEndFrame",
                "CheckStartFrame",
            ],
            "blocking" : [
                "CheckEndFrame",
                "CheckStartFrame",
            ],
            "refine" : [
                "CheckEndFrame",
                "CheckStartFrame",
            ],
            "fix" : [
                "CheckEndFrame",
                "CheckStartFrame",
            ],
            "prelight" : [
                "CheckEndFrame",
                "CheckStartFrame",
            ],
            "lighting" : [
                "CheckEndFrame",
                "CheckStartFrame",
            ],
        }

        self.plugin_task_filters += [
            # ["sg_status_list", "not_in", ["na", "wtg"]],
            ["entity.Asset.sg_status_list", "not_in", ["na"]],
            # ["entity.Shot.code", "starts_with", "gri_1"],
        ]
        self._shot_animatic_resolution = "420:176"#420x176 "428:240"

        self.version_regex = r"V\d\d\d"
        self._naming_regex = [
            # r"^FT_[A-Za-z0-9]+_[A-Za-z0-9]+-\d\d_[a-zA-Z0-9]+_V\d\d\d.*",
            r"^FT_(CH|PR|SP|EN|FX|MP|VE)+(_[A-Za-z0-9]+){3}_V\d\d\d(_[A-Za-z0-9]+){0,}.*",
            r"^FT(_\d\d\d){2}-\d\d(_[a-z]+){2}_V\d\d\d.*",
            r"^FT_[A-Za-z]+_(\d\d\d_){1,2}[a-z]{3}_V\d\d\d(_[A-Za-z0-9]+){0,}.*",
        ]
        self._upload_status = "pndsup"

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
        # self._compulsory_publish_fields = ["description", "timelog"]
        self._compulsory_publish_fields = []

    def get_task_filesystem(
        self, code, entity_type, task, step, asset_type, *args, **kwargs
    ):
        slug: str = None

        if entity_type == "Asset":
            asset_name, asset_variant = code.split("_")

            slug = Path("00_FT_ASSETS", asset_type, asset_name, asset_variant, task)

        elif entity_type == "Episode":
            slug = Path("01_FT_WORKS", code[4:], step, task)

        elif entity_type == "Shot":
            slug = Path(
                "01_FT_WORKS",
                code.split("_")[0],
                "sequences",
                code.split("_")[1],
                "shots",
                code.split("_")[2],
                task,
            )

        elif entity_type == "Sequence":
            slug = Path(
                "01_FT_WORKS",
                code.split("_")[0],
                "sequences",
                code.split("_")[1],
                task,
            )

        local_path = Path(self.local_root, slug)
        server_path = Path(self._server_root, slug)

        if slug is None:
            local_path = None
            server_path = None

        return local_path, server_path

    def return_next_version_name(self, ext: Iterable, version: int = None) -> dict:
        # gri_102_060_040_01_light_rfn_002.mov
        # gri_pr_toast_standard-tv01_look_lde_003_standardRenderTurntable
        task = self.last_task_clicked
        if task is not None:
            task_name = self.task_long_to_short(task.name)
            link = task.link_name
            v, last_file = self.return_last_file(ext, Path("files"))
            v = version or v
            match task.entity_type:
                case "Asset":
                    file_name = f"FT_{task.asset_type}_{link}_{task_name}_V{v+1:03}"
                case "Shot":
                    file_name = f"FT_{link}_{task_name}_V{v+1:03}"
                case "Sequence":
                    file_name = f"FT_{link}_{task_name}_V{v+1:03}"

            if last_file is None:
                last_file = Path(self.TEMPLATES_FOLDER)

            return {
                "local_path": Path(task.local_path, "files"),
                "file_name": file_name,
                "previous_file": last_file,
                "full_file_name": Path(task.local_path, f"{file_name}.{ext[0]}")
            }

    def read_excel(self, excel: Path):
        logger.debug(f"reading excel {excel}")
        episode = f"{excel.name.split('_')[2]}"
        logger.debug(f"BDL captured for episode {episode}")
        data_frame, dupes = read_xlsx(
            excel,
            usecols=[1, 3, 4, 5, 6, 7],
            skiprows=[*range(9)],
            replace_pairs=[
                {"regex": [" "], "value": "_"},
                {"regex": [r"_$"], "value": ""},
            ],
            fillna="",
            duped_cols=[1, 2],
            dropna=[1, 2],
            sheet_name=[
                "SETS",
                "SET_PROPS",
                "CHARS",
                "VEHICLES",
                "PROPS",
                "FX",
                "MATTE_PAINT",
            ],
        )
        results = dict()
        existing_assets = self.return_all_assets()

        for i, row in data_frame.iterrows():
            logger.debug([*row])
            try:
                asset_type, code, variant, prod_type, parent_assets = row[:5]
                # parent_asset: str = parent_asset.strip(" ").split(",")
            except ValueError as e:
                logger.debug(f"Failed to parse row: {[*row]}")
                raise (e)

            asset_name = f"{code}_{variant}"
            asset_name = f"{asset_name.upper()[0]}{asset_name[1:]}"

            results[i] = {
                "series": [content for content in row[:5].tolist()],
                "errors": list(),
                "episode": f"{episode}",
                "asset_name": asset_name,
                "exists": asset_name in existing_assets,
                "status": True,
            }

            # logger.debug(dupes)

            if dupes[i]:
                results[i]["errors"].append("This asset is repeated.")

            if asset_type.upper() not in ["CH", "PR", "VE", "SP", "MP", "FX", "EN"]:
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

            if prod_type in ("CR", "VR"):
                if asset_name in existing_assets:
                    results[i]["exists"] = True
                    if (
                        existing_assets[asset_name].get(
                            "sg_created_for_episode.Episode.code"
                        )
                        != f"{episode}"
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

            # for content in [*row[:2], row[3]]:
            #     if content in (None, ""):
            #         results[i]["errors"].append("There are some empty fields.")

            for tag in (code, variant):
                if not tag.replace("_", "").isalnum() and tag != "":
                    results[i]["errors"].append(
                        f"There are non alphanumeric values: "
                        f"{sub('[^0-9a-zA-Z]+', '*', tag)}"
                    )
            results[i]["status"] = len(results[i]["errors"]) == 0

        return [*data_frame.columns[:5].tolist()], results

    def read_excel(self, excel: Path):
        from task_schema.plugins.furrytails_plugin import FurryTailsPlugin as FT
        from pandas import read_excel

        df = read_excel(excel)
        df = df[df["ASSET_NAME"].notna()]  # remove rows with no name
        df[["PRIORITY"]] = df[["PRIORITY"]].fillna(1)
        df = df.drop_duplicates(subset=["ASSET_NAME"])
        df.loc[df["TYPE"] == "ENV", "TYPE"] = "EN"
        df.loc[df["STATUS"] == "IP", "STATUS"] = "ip"
        df.loc[df["STATUS"] == "NS", "STATUS"] = "wtg"
        df.loc[df["STATUS"] == "APV", "STATUS"] = "capv"
        df.loc[df["PRIORITY"] == 1, "PRIORITY"] = "Urgent"
        df.loc[df["PRIORITY"] == 2, "PRIORITY"] = "High priority"
        df.loc[df["PRIORITY"] == 3, "PRIORITY"] = "Neutral"
        df.loc[df["PRIORITY"] == 4, "PRIORITY"] = "Low priority"
        df["PRIORITY"].fillna(3, inplace=True)
        df["STATUS"].fillna("ip", inplace=True)
        df.fillna("", inplace=True)
        results = dict()
        episode = "Catrella"
        existing_assets = FT().return_all_assets()
        # to_clip = ""
        for i, serie in df.iterrows():
            asset_name = serie.get("ASSET_NAME")
            # to_clip += f"\n{asset_name}\t{process_string(asset_name)}"
            # print(f"{asset_name}\t\t{process_string(asset_name)}")
            serie["ASSET_NAME"] = process_string(asset_name)
            results[i] = {
                "series": serie.to_list(),
                "errors": list(),
                "episode": f"{episode}",
                "asset_name": serie["ASSET_NAME"],
                "exists": serie["ASSET_NAME"] in existing_assets,
                "status": True,
                "priority": serie["PRIORITY"],
                "comments": serie["COMMENTS"],
            }
        return df.columns.to_list(), results

    def create_assets_from_bdl(self, dict_with_items: dict, excel_file: Path):
        logger.debug("Starting asset generation phase.")
        logger.debug("Collecting SG data.")
        created_assets = self.return_all_assets()
        created_episodes = self.return_all_episodes()

        episode = f"{excel_file.name.split('_')[2]}"

        if episode not in created_episodes:
            msg = (
                f'The episode "{episode}" '
                "does not exist in SG, please create it first"
            )
            logger.debug(msg)
            raise Exception(msg)
        #     created_episodes.update({value["episode"]: ep})
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
            logger.debug(f"Working on item {value}")

            parents = (
                [value["series"][4]]
                if "," not in value["series"][4]
                else value["series"][4].split(",")
            )
            print(parents)
            if value["status"] and not value["exists"]:
                task_template = self.sg.find_one(
                    "TaskTemplate",
                    [["code", "is", f"FT - Asset - {value['series'][0]}"]],
                )
                data = {
                    "code": value["asset_name"],
                    "project": project,
                    "sg_status_list": "ip",
                    "episodes": [ep],
                    "sg_created_for_episode": ep,
                    "sg_production_type": value["series"][3],
                    "task_template": task_template,
                }
                if (
                    value["series"][3] in ["CR", "VR"]
                    and value["asset_name"] not in created_assets
                ):
                    created_asset = self.sg.create("Asset", data)
                    logger.debug(f"Asset {value['asset_name']} was created.")
                else:
                    created_asset = created_assets[value["asset_name"]]

                self.sg.update(
                    "Asset",
                    created_asset["id"],
                    {
                        "episodes": [ep],
                        "parents": [
                            v for k, v in created_assets.items() if k in parents
                        ],
                    },
                    multi_entity_update_modes={"episodes": "add", "parents": "add"},
                )

                created_assets[value["asset_name"]] = created_asset

                yield created_asset

            elif value["exists"] and value["status"]:
                logger.debug(
                    f"Asset {value['asset_name']} existed already so it was updated."
                )
                self.sg.update(
                    "Asset",
                    created_assets[value["asset_name"]]["id"],
                    {
                        "episodes": [ep],
                        "parents": [
                            v for k, v in created_assets.items() if k in parents
                        ],
                    },
                    multi_entity_update_modes={"episodes": "add", "parents": "add"},
                )

    def create_assets_from_bdl(self, dict_with_items: dict, excel_file: Path):
        logger.debug("Starting asset generation phase.")
        logger.debug("Collecting SG data.")
        created_assets = self.return_all_assets()
        created_episodes = self.return_all_episodes()

        episode = f"{excel_file.name.split('_')[2]}"

        if episode not in created_episodes:
            msg = (
                f'The episode "{episode}" '
                "does not exist in SG, please create it first"
            )
            logger.debug(msg)
            raise Exception(msg)
        #     created_episodes.update({value["episode"]: ep})
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
                # "sg_production_type": value["series"][3],
                "task_template": task_template,
            }

            # print(
            #     f"{art_bid=}{model_bid=}{shading_bid=}{rig_bid=} name={value['asset_name']}"
            #     f" type={value['series'][1]} status={value['series'][4]}"
            # )
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

            # created_assets[value["asset_name"]] = created_asset

            # elif value["exists"] and value["status"]:
            #     logger.debug(
            #         f"Asset {value['asset_name']} existed already so it was updated."
            #     )
            #     self.sg.update(
            #         "Asset",
            #         created_assets[value["asset_name"]]["id"],
            #         {
            #             "episodes": [ep],
            #             "parents": [
            #                 v for k, v in created_assets.items() if k in parents
            #             ],
            #         },
            #         multi_entity_update_modes={"episodes": "add", "parents": "add"},
            #     )


if __name__ == "__main__":
    from os import environ

    basicConfig()
    logger = getLogger()
    logger.level = DEBUG

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

    plugin = FurryTailsPlugin()
    # plugin.update_asset_task_fields_with_task_entities()
    
