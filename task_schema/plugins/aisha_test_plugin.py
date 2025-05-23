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

from task_schema.plugins.shotgrid_plugin import ShotgridPlugin


logger = getLogger(__name__)


class AishaTestPlugin(ShotgridPlugin):
    TITLE = "Aisha Test"
    PLUGIN_UUID = "790c3224-4986-11ee-af4c-0c8bfd443fd6"
    SG_PROJECT_ID = 223
    SHOTGRID_URL = "https://magoproduction.shotgrid.autodesk.com"
    SHOTGRID_SCRIPT_NAME = "loa_ext_tools_test"
    SHOTGRID_API_KEY = "qJrvhzak0)ujcgqkbqjkfmaqy"

    _active_entities = ["My Tasks", "Asset", "Sequence", "Episode", "Shot"]

    custom_artist_entities = [
        "sg_artist_work",
    ]
    title = "Aisha"
    uses_deadline = True
    add_tasks_from_plugin_kwargs = {"sg_entity_type": "My Tasks"}
    create_file_ext = ["from selected", "psd", "ma", "spp", "hip"]
    # bdlregex = r"BDL_FT_(Film|Teaser|[A-Z][A-Za-z0-9]+)_.*"
    # task_subfolders = {
    #     "all": ["files", "preview"],
    #     "shading": ["textures", "export", "files/maya", "files/painter"],
    #     "fur": ["masks", "collections"],
    # }
    # asset_task_fields_dict = {
    #     "Asset": {
    #         "sketch": "sg_asset_sketch_task",
    #         "line": "sg_asset_line_task",
    #         "color": "sg_asset_color_task",
    #         "expressions": "sg_asset_expressions_task",
    #     },
    # }

    def __new__(cls: "AishaTestPlugin", *args, **kwargs) -> "AishaTestPlugin":
        cls._local_root = Path(cls.env_handler.get_env("AISHA_LOCAL_PATH"))
        cls._server_root = Path(
            cls.env_handler.get_env("AISHA_SERVER_PATH")
        )
        cls.TEMPLATES_FOLDER = Path(cls._server_root, "03_FT_TEMPLATES/")
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.plugin_task_filters = [
            ["sg_status_list", "not_in", ["na"]],
            ["project.Project.id", "is", int(self.SG_PROJECT_ID)],
        ]

        self._preview_location = Path("preview")
        self._textures_location = Path("textures")
        self._export_location = Path("export")
        self._fps = 12
        # self._playblast_res = "2048x858"
        self._playblast_res = "1920x1038"
        self._starting_frame = 1001

        self.plugin_task_filters += [
            ["entity.Asset.sg_status_list", "not_in", ["na"]],
        ]
        self.version_regex = r"u|v\d\d\d"
        self._naming_regex = [
            # r"^FT_[A-Za-z0-9]+_[A-Za-z0-9]+-\d\d_[a-zA-Z0-9]+_V\d\d\d.*",
            r"^FT_(CH|PR|SP|EN|FX|MP|VE)+(_[A-Za-z0-9]+){3}_V\d\d\d(_[A-Za-z0-9]+){0,}.*",
            r"^FT(_\d\d\d){2}-\d\d(_[a-z]+){2}_V\d\d\d.*",
            r"^FT_[A-Za-z]+_(\d\d\d_){1,2}[a-z]{3}_V\d\d\d(_[A-Za-z0-9]+){0,}.*",
        ]
        self._upload_status = "pndsup"

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

if __name__ == "__main__":
    from os import environ

    basicConfig()
    logger = getLogger()
    logger.level = DEBUG

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

    plugin = FurryTailsPlugin()
    plugin.update_asset_task_fields_with_task_entities()
    
