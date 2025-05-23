from logging import getLogger, basicConfig, DEBUG
from pathlib import Path
from typing import Iterable
from re import compile, sub, search
from os import fspath, remove
import os.path
from os.path import getmtime
from shutil import copy2
from typing import TYPE_CHECKING

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

from task_schema.plugins.furrytails_plugin import FurryTailsPlugin
from utilities.pipe_utils import TimeoutPath

if TYPE_CHECKING:
    from task_schema.plugins.base_plugin import BaseTask

logger = getLogger(__name__)


class FurryTailsNewPlugin(FurryTailsPlugin):
    TITLE = "FT"  # to get the task template
    PLUGIN_UUID = "108fec79-1721-11ee-a215-9c7bef2d10d5"
    SHOTGRID_SCRIPT_NAME = "FurryTailsSecondManager"
    SHOTGRID_API_KEY = "atojdypbsirqtNhrbfufawu_4"

    title = "Furry Tails"  # for the plugin tab
    task_subfolders = {}

    def __new__(cls: "FurryTailsPlugin", *args, **kwargs) -> "FurryTailsPlugin":
        cls = super().__new__(cls)
        cls._local_root = Path(cls.env_handler.get_env("FT_LOCAL_PATH"))
        if (p := TimeoutPath("\\\\192.168.1.21\\FurryTails")).exists():
            root_candidate = p
        elif (p := TimeoutPath("\\\\100.96.1.34\\FurryTails")).exists():
            root_candidate = p
        else:
            root_candidate = None
        cls._server_root = Path(
            cls.env_handler.get_env("FT_SERVER_PATH", root_candidate)
        )
        cls.TEMPLATES_FOLDER = Path(cls._server_root, "library")
        cls.BDLS_FOLDER = Path(cls._server_root, "shots")
        cls.SL_SERVER_PATH = Path(cls._server_root, "/library/animations_Maya/Anim_lib")
        return cls

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.OCIO_FILE = Path(
            self.server_root,
            "library/ocio_configs/Maya2022-default/config.ocio",
        )
        self.GWAIO_MAYA_LIGHT_TEMPLATE = fspath(
            Path(self._local_root, "/library/lights/lookdev_studio.ma")
        )
        self.CUSTOM_MAYA_TOOLS = Path(self.server_root, "library/tools/Maya_scripts")
        self.CUSTOM_HOUDINI_TOOLS = Path(self.server_root, "library/Houdini")
        self.CUSTOM_NUKE_TOOLS = Path(self.server_root, "library/tools/Nuke_scripts")
        self._shot_task_tpl_id = 587
        self._preview_location = Path("")
        self._textures_location = Path("")
        self._export_location = Path("")
        self._asset_folder_regex = fspath(self.local_root) + "/assets/*/*/*"
        self._asset_folder = fspath(self.local_root) + "/assets"

        self._folders_to_sync = [
            # {"folder":f"{self.server_root/'animatic/sequences'}", "include": [".edl"]},
            # {"folder":f"{self.server_root/'library/tools/programs/ffmpeg'}"},
            # {"folder":f"{self.server_root/'library/templates'}"},
            # {"folder":f"{self.server_root/'library/lights'}"},
        ]

        self.version_regex = r"V\d\d\d"
        self._naming_regex = [
            r"^([A-Za-z0-9]+_){3}V\d\d\d(_[A-Za-z0-9]+){0,}.*",
            r"^sq(\d{4})_sh(\d{3})_[a-z]+_V\d\d\d.*",
            r"^sq(\d{4})_[a-z]+_V\d\d\d.*",
            r"^[A-Za-z\d]+_(sq){0,1}\d{3,4}_(sh){0,1}\d\d\d_[a-z]{3}_V\d\d\d(_[A-Za-z0-9]+){0,}.*",
        ]

        self._dict_previous_tasks = {
            "line": {"task": "sketch", "step": "ConceptArtStep"},
            "color": {"task": "line", "step": "ConceptArtStep"},
            "shading": {"task": "model", "step": "ModelingStep"},
            # "shading": {"task": "uvs", "step": "ModelingStep"},
            "fur": {"task": "shading", "step": "LookDevStep"},
            "blendShapes": {"task": "model", "step": "ModelingStep"},
            "rigging": {"task": "model", "step": "ModelingStep"},
            "riggingLayout": {"task": "model", "step": "ModelingStep"},
            "animLib": {"task": "rigging", "step": "RiggingStep"},
            "blocking": {"task": "layout", "step": "LayoutStep"},
            "refine": {"task": "blocking", "step": "AnimationStep"},
            "fix": {"task": "refine", "step": "AnimationStep"},
            "fxclean": {"task": "fxrough", "step": "FxStep"},
            "lighting": {"task": "prelight", "step": "LightingStep"},
        }

        self._dict_file_templates = {
            "ma": Path(self.TEMPLATES_FOLDER, "templates", "StartUp_Template.ma"),
            "hip": Path(self.TEMPLATES_FOLDER, "templates", "Assembling_Template.hip"),
            "psd": Path(self.TEMPLATES_FOLDER, "templates", "concept_template.psd"),
            "nk": Path(self.TEMPLATES_FOLDER, "comp","Template", "FT_sqXXXX_MasterComp.nk"),
        }

    def get_task_filesystem(
        self, code, entity_type, task, step, asset_type, *args, **kwargs
    ):
        slug = None
        SGTYPE2FOLDER = {
            "CH": "characters",
            "PR": "props",
            "EN": "sets",
            "SP": "props",
            "MP": "mattePaintings",
        }
        STEP2FOLDER = {
            "ConceptArtStep": "concept",
            "ModelingStep": "model",
            "LookDevStep": "shading",
            "RiggingStep": "rig",
            "LayoutStep": "layout",
            "Layout": "layout",
            "AnimationStep": "animation",
            "Animation": "animation",
            "LightingStep": "lighting",
            "CompositingStep": "compositing",
            "storyboardStep": "storyboard",
            "EditStep": "edit",
            "FXStep": "fx",
            "colorStep": "colorkey",
            "Editorial": "edit",
        }
        if entity_type == "Asset":
            # asset_name, asset_variant = code.split("_")
            slug = Path(
                "assets",
                SGTYPE2FOLDER.get(asset_type, ""),
                code,
                "wip",
                STEP2FOLDER.get(step, task),
            )

        elif entity_type == "Episode":
            if step == "AnimationStep" and task in ["animLib", "studio_library"]:
                slug = Path("library/animations_Maya")
            else:
                slug = Path("shots", code, "wip", STEP2FOLDER.get(step, task))

        elif entity_type == "Shot":
            # shots\Catrella\sq0010\sq001_sh010\animatic
            slug = [
                "shots",
                kwargs.get("episode") or "generic",
                kwargs.get("sequence") or "generic",
                code,
                "wip",
                STEP2FOLDER.get(step, task),
            ]
            if task == "animatic":
                slug.pop(-2)
            if task == "compositing":
                slug.pop(-3)
            slug = Path(*slug)

        elif entity_type == "Sequence":
            slug = [
                "shots",
                kwargs.get("episode") or "generic",
                code,
                "wip",
                STEP2FOLDER.get(step, task),
            ]
            if task == "animatic":
                slug.pop(-2)
            slug = Path(*slug)

        local_path = Path(self.local_root, slug)
        server_path = Path(self._server_root, slug)

        if slug is None:
            local_path = None
            server_path = None

        return local_path, server_path

    def return_next_version_name(self, ext: Iterable, version: int = None) -> dict:
        task = self.last_task_clicked
        if task is not None:
            task_name = self.task_long_to_short(task.name)
            link = task.link_name
            v, last_file = self.return_last_file(ext)
            v = version or v
            if task_name == "cmp":
                sq_name = link.split("_")[0]
                file_name = f"FT_{sq_name}_MasterComp"
            else:
                file_name = f"{link}_{task_name}_V{v+1:03}"
            if last_file is None:
                last_file = Path(self.TEMPLATES_FOLDER)

            return {
                "local_path": Path(task.local_path),
                "file_name": file_name,
                "previous_file": last_file,
                "full_file_name": Path(task.local_path, f"{file_name}.{ext[0]}"),
            }

    def return_all_versions_name(self, ext: str) -> list:
        task = self.last_task_clicked
        if task is not None:
            task_name = self.task_long_to_short(task.name)
            link = task.link_name
            file_name = f"{link}_{task_name}_V*{ext}"
            return list(self.last_task_clicked.local_path.glob(file_name))

    def return_last_version_file(self, path: Path, ext: Iterable[str]) -> Path | None:
        """
        Looks at all the files with a given extension in 'path' and returns as
        Path the file that has the highest version number that matches the version_regex.
        """
        v, last_file = 0, None
        logger.debug(f"Filtering possible candidates.")
        for f in self.filter_local_files(path, ext):
            try:
                logger.debug(f"Evaluating {f} as a candidate.")
                version_str = search(self.version_regex, f.name).group()
                version_str = sub("[^0-9]", "", version_str)
                if int(version_str) == 0:
                    print("OMIT:",f)
                if int(version_str) >= v and int(version_str) != 0:
                    v, last_file = int(version_str), f
            except:
                pass

        # If there are files without versioning regex, get them by date
        if last_file is None:
            try:
                last_file = max(self.filter_local_files(path, ext), key=getmtime)
            except:
                pass
        logger.debug(f"Candidate found @ {last_file}")
        return last_file
    
    def on_item_doubleclicked_callback(self):
        # last_file = self.return_last_version_file(self.last_task_clicked.local_path, [".ma"])
        task = self.last_task_clicked
        if task.name == "refine":
            all_files = [f for f in self.return_all_versions_name(".ma") if not "V000" in f.stem]
            if all_files:
                last_file = max(all_files, key=os.path.getmtime)
            else:
                last_file = self.return_last_version_file(task.prev_task_server,"ma")
                if last_file is None:
                    return
                task_name = self.task_long_to_short(task.name)
                link = task.link_name
                next_file = Path(task.local_path, f"{link}_{task_name}_V001.ma")
                copy2(last_file, next_file)
                last_file = next_file
        elif task.name == "lighting":
            all_files = list(f for f in task.local_path.glob("*.hip") if "_V" in f.stem)
            if all_files:
                last_file = max(all_files, key=os.path.getmtime)
            else:
                task_name = self.task_long_to_short(task.name)
                link = task.link_name
                next_file = Path(task.local_path, f"{link}_{task_name}_V001.hip")
                last_file = self._dict_file_templates["hip"]
                # last_file = Path(self.server_root,"library/templates/startUp.hip")
                logger.info(f"Copying {last_file} > {next_file}")
                copy2(last_file, next_file)
                last_file = next_file
        else:
            all_files = list(f for f in task.local_path.glob("*.ma") if "_V" in f.stem)
            if all_files:
                last_file = max(all_files, key=os.path.getmtime)
            else:
                last_file = None
        logger.info(f"Double click, file found '{last_file}'")
        if last_file is None and self.explorer_toolbar is not None:
            # something else than ma, make a mapping for tasks
            result = self.explorer_toolbar.create_file(
                ["ma"], self._dict_file_templates["ma"]
            )
            last_file = Path(result.get("local_path"), result.get("file_name") + ".ma")
            logger.debug(
                f"Duble click, file was created: {last_file} from source {self._dict_file_templates['ma']}"
            )

        if Path(last_file).exists():
            self.open_file_with_env(
                fspath(last_file), self.guess_executable_for_file(last_file)
            )

    def after_publish(self, file: Path, data: dict, *args, **kwargs):
        # WindowsPath('D:/PROJECTS/FURRY_TAILS/FurryTails/shots/TestScript/TestScripts_sq0010/wip/layout/TestScripts_sq0010_lay_V003.ma'),
        return
        is_published = data["is_publish"]
        is_synced = data["is_sync"]
        task: BaseTask = data["task"]
        widget_item = data["item"]

        if "rig" not in task.name:
            return
        if file.suffix != ".ma":
            return

        new_file = file.parent.parent.parent / sub(self.version_regex, "", file.name)
        new_file = Path(fspath(new_file).replace("__", ""))
        server_file = Path(
            self._server_root,
            *new_file.parts[
                len(Path(self.env_handler.get_env("GWAIO_LOCAL_ROOT")).parts) :
            ],
        )
        for f in (new_file, server_file):
            try:
                if f.exists():
                    remove(f)
                copy2(fspath(file), fspath(f))
            except Exception as e:
                logger.warning(f"Failed to create file {f} because: {e}")

    def return_maya_outliner_asset_base_nodes(self, *args, **kwargs):
        return ["|asset_grp|rig_grp", "|asset_grp|model_grp"]


if __name__ == "__main__":
    from os import environ
    from pprint import pprint
    from copy import deepcopy

    basicConfig()
    logger = getLogger()
    logger.level = DEBUG

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))
    ins = FurryTailsNewPlugin()
