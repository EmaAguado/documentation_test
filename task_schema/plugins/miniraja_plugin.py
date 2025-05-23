from logging import getLogger
from pathlib import Path
from os import environ
from shutil import copy2
from typing import Iterable
from os import fspath
from re import match, Match, compile

import pandas

if __name__ == "__main__":
    # these are only required if the module is executed stand alone
    import sys
    sys.path.append(fspath(Path(__file__).parent.parent.parent))

from task_schema.plugins.generic2d_plugin import Generic2DPlugin

logger = getLogger(__file__)


class MiniRajaPlugin(Generic2DPlugin):
    TITLE = "MiniRaja"
    PLUGIN_UUID = "a6b31f9a-bbfc-11ed-a253-9c7bef2d10d5"
    # _server_root = Path(
    #     "\\\\qsrv01.mondotvcanarias.lan\\proj_mh\\METEO HEROES 2"
    # )

    SHOTGRID_SCRIPT_NAME = "MiniRajaScript"
    SHOTGRID_API_KEY = "dyffuvgb&sjWpgwa0zjwwwwfo"
    SG_PROJECT_ID = 353

    title = "MiniRaja Plugin"
    bdlregex = r"Checklist MR(\d{2,3}|[A-Z][A-Za-z0-9]+)"
    _active_entities = ["Asset", "Sequence", "Episode", "Shot"]
    _edl_target_task = "animatic"
    _shot_task_tpl_id = 739

    def __new__(cls: "MiniRajaPlugin", *args, **kwargs) -> "MiniRajaPlugin":
        cls._local_root = Path(cls.env_handler.get_env("MINIRAJA_LOCAL_PATH"))
        cls._server_root = Path(
            Generic2DPlugin.env_handler.get_env(
                "MINIRAJA_SERVER_PATH",
                Path("\\\\qsrv01.mondotvcanarias.lan\\proj_mr\\MINIRAJA"),
            )
        )
        cls.TEMPLATES_FOLDER = Path(
            cls._server_root, "Concept MondoTvStudios/SMARTWORKING KIT"
        )
        cls.BDLS_PATH = Path(cls._server_root, "PRODUCTION/BDL_FILES")
        cls.packtype_to_status = {
            "sb": (
                ["mhok1", "mhok2"],
                lambda: cls.return_pack_folder("SBPACK"),
                False,
                [],
            ),
            "ep": (
                ["mhok1", "mhok2"],
                lambda: cls.return_pack_folder("EPPACK"),
                False,
                [],
            ),
            "re": (
                ["mhrdy"],
                lambda: cls.return_pack_folder("REVIEW_PACK", True),
                False,
                [],
            ),
        }
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._naming_regex = [
            # r"^(MH\d\d\d|MH00)_(BG|CH|FX|PR)_[A-Z_]+_(V\d\d\d)([A-Za-z0-9\._-]+)?"
            r"^(MR\d\d\d|MR00)_(BG|CH|FX|PR|LAYOUT)_[A-Z_-]+_([A-Za-z0-9\._-]+)?"
        ]
        self.plugin_task_filters = [
            ["sg_status_list", "not_in", ["na"]],
            ["project.Project.id", "is", int(self.SG_PROJECT_ID)],
        ]
        self._dict_previous_tasks = {"color": {"task": "line"}}
        self._fps = 25
        # self.edl_sequence_regex = compile(r"(?:(?<=MR\d\d\d_)|(?<=MRTrailer_))\d\d\d")
        self._episode_edl_workflow = True
        self._edl_episode_regex = compile(r"(?<=MR)(\d{2,3}|[A-Z][a-zA-Z0-9]+)")
        self.edl_sequence_regex = compile(r"(?<=MR)(\d{2,3}_\d\d\d|[A-Z][a-zA-Z0-9]+_\d\d\d)")
        self._edl_shot_regex = compile(r"\d\d\d$")
        # self._sequence_task_template_id = 
        self.edl_version_regex = compile(r"(?<=_V)\d\d\d")
        self._edl_shot_prefix = "MR"
        self._upload_status = "drv"

    def get_task_filesystem( self, code, entity_type, task, *args, **kwargs):

        if entity_type == "Asset":
            asset_type = code.split("_")[1]

            ep: Match = match(r"MR(\d{2,3}|[A-Z][a-zA-Z0-9]+)", code)

            if ep is None:
                episode = "MR00"
            else:
                episode = ep.group()

            slug = Path("PRODUCTION/ASSETS", episode, asset_type, code, task)
            local_path = Path(self.local_root, slug)
            server_path = Path(self._server_root, slug)

        elif entity_type == "Shot":
            episode, sequence, shot = code.split("_")
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

        return local_path, server_path

    def read_excel(self, excel: Path):
        episode = excel.name.split(" ")[1][:5]
        existing_assets = self.return_all_assets()
        data_frame = (
            pandas.read_excel(excel, skiprows=[0], usecols=[0, 1, 5])
            .replace(regex=[" "], value="_")
            .replace(regex=[r"_$"], value="")
        )
        data_frame = data_frame.dropna(subset=data_frame.columns[:2])
        data_frame.fillna("", inplace=True)
        results = dict()
        dupes = data_frame.duplicated(
            subset=data_frame.columns[1:2].tolist(), keep=False
        )

        row: pandas.Series
        for i, row in data_frame.iterrows():
            scene = row[0] or ""
            asset_name = str(row[1]) if len(row) >= 2 else ""
            scenes = row[2] if len(row) == 3 else ""

            results[i] = {
                "series": row.tolist(),
                "errors": list(),
                "episode": f"{episode}",
                "asset_name": row[1],
                "exists": asset_name in existing_assets,
                "status": True,
            }

            if dupes[i]:
                results[i]["errors"].append("This asset is repeated.")

            if not match(r"^(MR\d\d\d|MR00)_(BG|CH|FX|PR|LAYOUT)_[A-Z_]+", asset_name):
                # logger.debug(asset_name)
                results[i]["errors"].append("Naming of the assets seems wrong.")

            # logger.debug(asset_name)
            # logger.debug(existing_assets)
            if asset_name in existing_assets.keys():
                results[i]["exists"] = True
                if not asset_name.startswith(f"MR{episode}") and not asset_name.startswith(f"MR00"):
                    results[i]["errors"].append(
                        f"Asset exists and it won't be created."
                    )

            results[i]["status"] = len(results[i]["errors"]) == 0

        return data_frame.columns.tolist(), results
    
    def return_next_version_name(self, ext: Iterable) -> dict:
        result = super().return_next_version_name(ext)
        if self.last_task_clicked.asset_type:
            # if it is not None or not falsy
            prefix = ""
        else:
            prefix = "MR"
        result["file_name"] = f"{prefix}{result['file_name']}"
        return result
    
    def create_assets_from_bdl(self, dict_with_items: dict, excel_file: Path):
        created_assets = self.return_all_assets()
        created_episodes = self.return_all_episodes()

        project = {"type": "Project", "id": int(self.SG_PROJECT_ID)}
        for key, value in dict_with_items.items():
            if value["status"]:
                if value["episode"] not in created_episodes:
                    ep = self.sg.create(
                        "Episode", {"code": value["episode"], "project": project}
                    )
                    created_episodes[value["episode"]] = ep
                else:
                    ep = created_episodes[value["episode"]]

                if value["asset_name"] not in created_assets:
                    data = {
                        "code": value["asset_name"],
                        "project": project,
                        "sg_status_list": "ip",
                        "episodes": [ep],
                        "sg_2d_asset_type": value["asset_name"].split("_")[1],
                        # "sg_production_type" : value["series"][-1],
                        "task_template": {"id": 706, "type": "TaskTemplate"},
                        "sg_created_for_episode": ep,
                    }
                    created_asset = self.sg.create("Asset", data)
                    created_assets[value["asset_name"]] = created_asset
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

    def return_seq_and_shot_from_clipname(self, clip_name: str):
        # mr_101_030_100.01_anmt_001.mov
        ep, seq, shot = clip_name.split("_")[1:4]
        return f"{ep}_{seq}", f"{ep}_{seq}_{shot.replace('.', '-')}"


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

    app = QApplication()
    plugin = MiniRajaPlugin()
