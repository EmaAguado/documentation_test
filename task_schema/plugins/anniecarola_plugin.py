from pathlib import Path
from os import environ
from re import sub, compile as recomp
from logging import getLogger
from typing import Iterable, Generator

logger = getLogger(__name__)

import pandas

if __name__ == "__main__":
    # these are only required if the module is executed stand alone
    import sys
    from os import fspath

    sys.path.append(fspath(Path(__file__).parent.parent.parent))

from task_schema.plugins.generic2d_plugin import Generic2DPlugin


class AnnieCarolaPlugin(Generic2DPlugin):
    TITLE = "Annie&Carola"
    PLUGIN_UUID = "fc55a55d-32f7-46c2-af1b-7d524017d21c"
    # _server_root = Path(
    #     "\\\\qsrv01.mondotvcanarias.lan\\data2\\PROYECTOS\\ANNIE&CAROLA"
    # )

    SG_PROJECT_ID = 320
    title = "Annie&Carola"
    create_file_ext = ["from selected", "psd/psb", "clip", "harmony"]
    bdlregex = r"AC_BDL_\d\d\d_"
    _active_entities = ["Asset", "Sequence", "Episode", "Shot"]
    _edl_target_task = "animatic"
    _shot_task_tpl_id = 640

    def __new__(cls: "AnnieCarolaPlugin", *args, **kwargs) -> "AnnieCarolaPlugin":
        cls._local_root = Path(cls.env_handler.get_env("ANNIECAROLA_LOCAL_PATH"))
        cls._server_root = Path(
            cls.env_handler.get_env(
                "ANNIECAROLA_SERVER_PATH",
                Path("\\\\qsrv01.mondotvcanarias.lan\\proj_ac\\ANNIE & CAROLA"),
            )
        )

        cls.TEMPLATES_FOLDER = Path(cls._server_root, "TEMPLATES")
        cls.BDLS_PATH = Path(cls._server_root, "PRODUCTION/Episodes")
        cls.packtype_to_status = {
            "sb": (
                ["dap", "mpa", "apr"],
                lambda: cls.return_pack_folder("SBPACK"),
                False,
                [],
            ),
            "wip": (
                ["pmp", "adr", "rev", "rtk", "drv", "drk", "trk"],
                lambda: cls.return_pack_folder("WIPPACK"),
                True,
                [],
            ),
        }
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._naming_regex = [
            r"^AC_(BG|CH|FX|PR|SP|SFX)_[A-Za-z0-9_]+_(V\d\d\d)([A-Za-z0-9\._-]+)?",
            r"AC(_\d\d\d){1,2}_[A-Za-z0-9_]+_(V\d\d\d)([A-Za-z0-9\._-]+)?"
            # r"^[A-Za-z0-9_]+_(V\d\d\d)([A-Za-z0-9\._-]+)?"
        ]
        # self._toolbars += []
        self._fps = 25
        self.edl_sequence_regex = recomp(r"(?<=AC_)\d\d\d_\d\d\d")
        self._edl_shot_regex = recomp(r"\d\d\d$")
        self.edl_version_regex = recomp(r"(?<=_[Vv])\d\d\d")
        self.timelog_artist_entity_field = "sg_mondo_artist"
        self.custom_artist_login_field = "sg_username"
        self.custom_artist_entity_name = "CustomEntity04"

        # self._upload_status = "pmp"
        # self.plugin_task_filters += [""]
        self._dict_previous_tasks = {"clean": {"task": "rough"}}
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
        self._edl_target_task = "storyboard"
        # self._edl_sequence_prefix = ""
        # self._edl_ep_in_sq = False
        # self.edl_sequence_regex = rcomp(
        #     r"(?<=MR)(\d{2,3}_\d\d\d|[A-Z][a-zA-Z0-9]+_\d\d\d)"
        # )




    @property
    def _upload_status(self):
        if self.last_file_clicked is not None and self.last_task_clicked.name in (
            "sbrough",
            "sbclean",
            "blocking",
            "animatic",
            "layout",
            "blocking",
            "refine",
        ):
            return "drv"
        return "rev"

    @_upload_status.setter
    def _upload_status(self, value):
        ...

    def return_seq_and_shot_from_clipname(self, clip_name: str):
        # * FROM CLIP NAME: AC101_010_010_01-010
        shot = clip_name.split(" ")[-1]
        ep, sq, sh, _ = clip_name.split("_")
        return f"{ep[2:]}_{sq}", f"{ep[2:]}_{sq}_{sh}"


    def return_next_version_name(self, ext: Iterable, version: int = None) -> dict:
        result = super().return_next_version_name(ext, version)
        if self.last_task_clicked.asset_type:
            # if it is not None or not falsy
            prefix = f"AC_{self.last_task_clicked.asset_type}"
        else:
            prefix = "AC"
        result["file_name"] = prefix + f"_{result['file_name']}"
        return result

    def get_task_filesystem(
        self, code: str, entity_type: str, task: str, asset_type: str, *args, **kwargs
    ):
        try:
            if entity_type == "Asset":
                slug = Path("PRODUCTION/ASSETS", asset_type, code, task)

                local_path = Path(self.local_root, slug)
                server_path = Path(self._server_root, slug)

            elif entity_type == "Sequence":
                # logger.debug(", ".join([code, entity_type, task, asset_type]))
                slug = Path(
                    "PRODUCTION/Episodes/", code.split("_")[0], "sequences", code, task
                )
                local_path = Path(self.local_root, slug)
                server_path = Path(self._server_root, slug)

            elif entity_type == "Episode":
                # logger.debug(", ".join([code, entity_type, task, asset_type]))
                slug = Path("PRODUCTION/Episodes/", code, task)
                local_path = Path(self.local_root, slug)
                server_path = Path(self._server_root, slug)

            elif entity_type == "Shot":
                # logger.debug(", ".join([code, entity_type, task, asset_type]))
                slug = Path(
                    "PRODUCTION/Episodes/",
                    code.split("_")[0],
                    "sequences",
                    "_".join(code.split("_")[0:2]),
                    "shots",
                    code,
                    task,
                )
                local_path = Path(self.local_root, slug)
                server_path = Path(self._server_root, slug)

            else:
                local_path = None
                server_path = None
        except Exception as e:
            for item in [code, entity_type, task, asset_type, args, kwargs]:
                logger.debug(item)
            logger.debug(e)

        return local_path, server_path

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

    def create_assets_from_bdl(self, dict_with_items: dict, excel_file: Path):
        created_assets = self.return_all_assets()
        created_episodes = self.return_all_episodes()

        project = {"type": "Project", "id": int(self.SG_PROJECT_ID)}

        for key, value in dict_with_items.items():
            if value["episode"] not in created_episodes:
                ep = self.sg.create(
                    "Episode", {"code": value["episode"], "project": project}
                )
                created_episodes.update({value["episode"]: ep})
            else:
                ep = created_episodes[value["episode"]]

            if value["status"] and not value["exists"]:
                ttdict = {
                    "CH": 541,
                    "FX": 673,
                }
                tt_id = (
                    508
                    if value["series"][0] not in ttdict
                    else ttdict.get(value["series"][0])
                )
                data = {
                    "code": value["asset_name"],
                    "project": project,
                    "sg_status_list": "ip",
                    # "episodes": [ep],
                    "sg_2d_asset_type": value["series"][0],
                    "sg_production_type": value["series"][-2],
                    "task_template": {"id": tt_id, "type": "TaskTemplate"},
                    "sg_created_for_episode": ep,
                }
                if (
                    value["series"][-2] in ["CR", "VR"]
                    and value["asset_name"] not in created_assets
                ):
                    created_asset = self.sg.create("Asset", data)
                else:
                    created_asset = created_assets[value["asset_name"]]

                self.sg.update(
                    "Asset",
                    created_asset["id"],
                    {"episodes": [ep]},
                    multi_entity_update_modes={"episodes": "add"},
                )

                created_assets[value["asset_name"]] = created_asset

                yield created_asset

            elif value["exists"] and value["status"]:
                self.sg.update(
                    "Asset",
                    created_assets[value["asset_name"]]["id"],
                    {"episodes": [ep]},
                    multi_entity_update_modes={"episodes": "add"},
                )

    def file_added_callback(self) -> None:
        if (
            self.sg.find_one(
                "Task", [["id", "is", self.last_task_clicked.id]], ["sg_status_list"]
            ).get("sg_status_list")
            == "rdy"
        ):
            self.sg.update("Task", self.last_task_clicked.id, {"sg_status_list": "ip"})

    def parse_clip_name(self, clip_name: str):
        """
        AC_EP102_ATIC_V01-110-110_010
        """
        ep_regex = recomp("1\d\d")
        file, seq, shot = clip_name.split("-")
        seq, shot = shot.split("_")
        ep = ep_regex.match(file).group()
        return ep, seq, shot

    def return_filepack_exceptions(self) -> Generator[str, None, None]:
        for csv_file in Path(
            self._server_root, "PRODUCTION/To_AEON/Assets_Sent_to_AEON"
        ).rglob("*.csv"):
            with open(csv_file, "r") as ftr:
                yield from (f.strip() for f in ftr.readlines())


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from logging import DEBUG, basicConfig

    basicConfig(level=DEBUG)

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

    app = QApplication()
    plugin = AnnieCarolaPlugin()
