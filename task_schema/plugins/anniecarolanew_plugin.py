from pathlib import Path
from re import compile as recomp
from os import environ, fspath

from task_schema.plugins.anniecarola_plugin import AnnieCarolaPlugin


class AnnieCarolaNewPlugin(AnnieCarolaPlugin):
    SG_PROJECT_ID = 386
    PLUGIN_UUID = "2d816fb8-cc04-11ee-8624-9c7bef2d10d5"

    title = "Annie&CarolaNew"
    _active_entities = ["Asset", "Episode", "Shot"]
    _edl_target_task = "StbClean"
    _shot_task_tpl_id = 904
    TITLE = "A&C_"

    def __new__(cls: "AnnieCarolaNewPlugin", *args, **kwargs) -> "AnnieCarolaNewPlugin":
        cls._local_root = Path(cls.env_handler.get_env("AC_LOCAL_PATH"))
        p = Path("\\\\qsrv01.mondotvcanarias.lan\\proj_ac\\ANNIE & CAROLA")
        cls._server_root = Path(cls.env_handler.get_env("AC_SERVER_PATH", p))

        # cls.TEMPLATES_FOLDER = Path(cls._server_root, "TEMPLATES")
        # cls.BDLS_PATH = Path(cls._server_root, "PRODUCTION/Episodes")
        # cls.packtype_to_status = {
        #     "sb": (
        #         ["dap", "mpa", "apr"],
        #         lambda: cls.return_pack_folder("SBPACK"),
        #         False,
        #         [],
        #     ),
        #     "wip": (
        #         ["pmp", "adr", "rev", "rtk", "drv", "drk", "trk"],
        #         lambda: cls.return_pack_folder("WIPPACK"),
        #         True,
        #         [],
        #     ),
        # }
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._naming_regex = [
            r"^AC_(BG|CH|FX|PR|SP|SFX)_[A-Za-z0-9_]+_(V\d\d\d)([A-Za-z0-9\._-]+)?",
            r"AC(_\d\d\d){1,2}_[A-Za-z0-9_]+_(V\d\d\d)([A-Za-z0-9\._-]+)?",
            # r"^[A-Za-z0-9_]+_(V\d\d\d)([A-Za-z0-9\._-]+)?"
        ]
        # self._fps = 25
        # self.edl_sequence_regex = recomp(r"(?<=AC_)\d\d\d_\d\d\d")
        self._edl_shot_regex = recomp(r"\d{4}[A-Z]{0,1}(?=_TK\d)")
        self.edl_version_regex = recomp(r"(?<=_[Vv])\d\d\d")
        # self.timelog_artist_entity_field = "sg_mondo_artist"
        # self.custom_artist_login_field = "sg_username"
        # self.custom_artist_entity_name = "CustomEntity04"

        # self._upload_status = "pmp"
        # self.plugin_task_filters += [""]
        # self._dict_previous_tasks = {"clean": {"task": "rough"}}
        self._episode_edl_workflow = True
        self._edl_episode_regex = recomp(r"AC\d{3}")
        # self.edl_version_regex = recomp(r"(?<=_[Vv])\d\d\d")

        # self._naming_regex = [
        #     r"^(?!.*(_)\1)LB(\d\d\d)_(BG|CH|FX|PR)_[0-9A-Z_]+_(V\d\d\d)([A-Za-z0-9\._-]+)?"
        # ]
        # self._dict_previous_tasks = {
        #     "color": {"task": "sketch", "step": "conceptArtStep"},
        #     "raster": {"task": "color", "step": "conceptArtStep"},
        # }
        # self._edl_target_task = "animatic"
        self._edl_target_task = "StbClean"
        # self._edl_sequence_prefix = ""
        # self._edl_ep_in_sq = False
        # self.edl_sequence_regex = rcomp(
        #     r"(?<=MR)(\d{2,3}_\d\d\d|[A-Z][a-zA-Z0-9]+_\d\d\d)"
        # )

    def return_seq_and_shot_from_clipname(self, clip_name: str):
        # * FROM CLIP NAME: AC101_SC003_TK0
        shot = clip_name.split(" ")[-1]
        ep, sh, _ = clip_name.split("_")
        return f"{ep}_010", f"{ep}_{sh}"


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from logging import DEBUG, basicConfig

    basicConfig(level=DEBUG)

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

    app = QApplication()
    plugin = AnnieCarolaPlugin()
