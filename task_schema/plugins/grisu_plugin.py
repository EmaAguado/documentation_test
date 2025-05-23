from logging import getLogger, basicConfig, DEBUG
import os
from os import fspath
from pathlib import Path
from typing import Iterable

if __name__ == "__main__":
    # these are only required if the module is executed stand alone
    import sys
    from os import fspath

    sys.path.append(fspath(Path(__file__).parent.parent.parent))

from task_schema.plugins.shotgrid_plugin import ShotgridPlugin
from launcher.qtclasses.toolbar_maya import MayaToolbar
from launcher.qtclasses.toolbar_meteoheroes import MeteoHeoresToolbar

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


class GrisuPlugin(ShotgridPlugin):
    TITLE = "Grisu"
    PLUGIN_UUID = "949f437a-c538-4f62-bb47-0d053250846e"
    SG_PROJECT_ID = 122

    # MAYA_LAUNCHER = Path("PIPELINE/dev/mtv/bat/launchMaya.bat")
    title = "Grisu Plugin"
    add_tasks_from_plugin_kwargs = {"sg_entity_type": "Asset"}
    create_file_ext = ["from selected", "psd", "ma"]

    def __new__(cls: "GrisuPlugin", *args, **kwargs) -> "GrisuPlugin":
        cls._local_root = Path(cls.env_handler.get_env("GRISU_LOCAL_PATH"))
        cls._server_root = Path(
            cls.env_handler.get_env(
                "GRISU_SERVER_PATH",
                Path("\\\\qsrv01.mondotvcanarias.lan\\data0\\PROJECTS\\GRISU"),
            )
        )
        cls.TEMPLATES_FOLDER = Path(cls._server_root, "PIPELINE/templates")
        cls.BDLS_FOLDER = Path(cls._server_root, "PROD/episodes/work")
        cls.packtype_to_status = {
            "2D MODEL": (
                ["fin", "dap", "eap"],
                lambda: cls.return_pack_folder("2D MODEL", False),
                False,
                [["sg_task.Task.content", "in", ["views", "line", "color"]]],
            ),
        }
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
            [MeteoHeoresToolbar,"meteoheroes Toolbar"],
        ]
        self._preview_location = Path("preview")

        self.plugin_task_filters += [
            ["sg_status_list", "not_in", ["na", "wtg"]],
            ["entity.Asset.sg_status_list", "not_in", ["na"]],
            # ["entity.Shot.code", "starts_with", "gri_1"],
        ]
        self.timelog_artist_entity_field = "user"
        self.publishedfile_artist_entity_field = "created_by"
        self.custom_artist_login_field = "login"
        self.custom_artist_entity_name = "HumanUser"
        self.custom_artist_task_field = "task_assignees"
        self._version_includes_entity = True
        self.version_regex = r"\d\d\d"
        self._naming_regex = [
            r"^gri_[a-z]{2}_[A-Za-z0-9]+_[A-Za-z0-9]+-tv\d\d_[a-z]+_[a-z]+_\d\d\d.*",
            r"^gri(_\d\d\d){3}-\d\d(_[a-z]+){2}_\d\d\d.*",
        ]
        self._upload_status = "rev"
        self._fps = 25
        self._starting_frame = 101
        self._dict_previous_tasks = {
            "color": {"task": "line", "step": "conceptArtStep"},
            "modelProd": {"task": "modelHigh", "step": "modelingStep"},
            "lookDevExport": {"task": "modelProd", "step": "modelingStep"},
            "rigAnim": {"task": "modelProd", "step": "modelingStep"},
            "rigProxy": {"task": "modelProd", "step": "modelingStep"},
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

    def return_next_version_name(self, ext: Iterable) -> dict:
        # gri_102_060_040_01_light_rfn_002.mov
        # gri_pr_toast_standard-tv01_look_lde_003_standardRenderTurntable
        task = self.last_task_clicked
        if task is not None:
            task_name = self.task_long_to_short(task.name)
            step = self.task_long_to_short(task.step)
            link = task.link_name
            type_ = task.asset_type
            v, last_file = self.return_last_file(ext, Path("files"))

            match task.entity_type:
                case "Asset":
                    file_name = f"gri_{type_}_{link}_{step}_{task_name}_{v+1:03}"
                case "Shot":
                    file_name = f"gri_{link}_{step}_{task_name}_{v+1:03}"
            if last_file is None:
                last_file = Path(self.TEMPLATES_FOLDER)

            return {
                "local_path": Path(task.local_path, "files"),
                "file_name": file_name,
                "previous_file": last_file,
                "full_file_name": Path(task.local_path, f"{file_name}.{ext[0]}")
            }


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from os import environ

    basicConfig()
    logger = getLogger()
    logger.level = DEBUG

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

    app = QApplication()
    plugin = GrisuPlugin()
