import logging
from pathlib import Path
from os import environ
from shutil import copy2
from os import fspath
from re import match, Match

import pandas

if __name__ == "__main__":
    # these are only required if the module is executed stand alone
    import sys

    sys.path.append(fspath(Path(__file__).parent.parent.parent))

from task_schema.plugins.generic2d_plugin import Generic2DPlugin


class MeteoHeroesPlugin(Generic2DPlugin):
    TITLE = "MeteoHeroes"
    PLUGIN_UUID = "d05c63fe-ac3b-4daa-8c89-fb88dd7f3276"
    # _server_root = Path(
    #     "\\\\qsrv01.mondotvcanarias.lan\\proj_mh\\METEO HEROES 2"
    # )

    SHOTGRID_SCRIPT_NAME = "MeteoHeroesScript"
    SHOTGRID_API_KEY = "wss%xmktbuetgevjidk0qFulo"
    SG_PROJECT_ID = 287

    title = "MeteoHeroes Plugin"
    bdlregex = r"Checklist \d\d\d"

    def __new__(cls: "MeteoHeroesPlugin", *args, **kwargs) -> "MeteoHeroesPlugin":
        cls._local_root = Path(cls.env_handler.get_env("METEOHEROES_LOCAL_PATH"))
        cls._server_root = Path(
            Generic2DPlugin.env_handler.get_env(
                "METEOHEROES_SERVER_PATH",
                Path("\\\\qsrv01.mondotvcanarias.lan\\proj_mh\\METEO HEROES 2"),
            )
        )
        cls.TEMPLATES_FOLDER = Path(
            cls._server_root, "- 05 SMARTWORKING KIT/MH_TEMPLATES"
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
            r"^(MH\d\d\d|MH00)_(BG|CH|FX|PR|LAYOUT)_[A-Z_-]+_([A-Za-z0-9\._-]+)?"
        ]

        self._dict_previous_tasks = {"color": {"task": "line"}}

    def get_task_filesystem( self, code, entity_type, task, *args, **kwargs):

        if entity_type == "Asset":
            asset_type = code.split("_")[1]

            ep: Match = match(r"MH\d\d\d", code)

            if ep is None:
                episode = "MH00"
            else:
                episode = ep.group()

            slug = Path("PRODUCTION/ASSETS", episode, asset_type, code, task)
            local_path = Path(self.local_root, slug)
            server_path = Path(self._server_root, slug)

        else:
            local_path = None
            server_path = None

        return local_path, server_path

    def read_excel(self, excel: Path):
        episode = excel.name.split(" ")[1][:3]
        existing_assets = self.return_all_assets()
        data_frame = pandas.read_excel(excel, skiprows=[0], usecols=[0, 1, 5])
        data_frame = data_frame.dropna(subset=data_frame.columns[:2])
        data_frame.fillna("", inplace=True)
        results = dict()
        dupes = data_frame.duplicated(
            subset=data_frame.columns[1:2].tolist(), keep=False
        )

        row: pandas.Series
        for i, row in data_frame.iterrows():
            scene = row[0] or ""
            asset_name = row[1] if len(row) >= 2 else ""
            scenes = row[2] if len(row) == 3 else ""

            results[i] = {
                "series": row.tolist(),
                "errors": list(),
                "episode": f"MH{episode}",
                "asset_name": row[1],
                "exists": asset_name in existing_assets,
                "status": True,
            }

            if dupes[i]:
                results[i]["errors"].append("This asset is repeated.")

            if not match(r"^(MH\d\d\d|MH00)_(BG|CH|FX|PR|LAYOUT)_[A-Z_]+", asset_name):
                # logger.debug(asset_name)
                results[i]["errors"].append("Naming of the assets seems wrong.")

            if asset_name in existing_assets:
                results[i]["exists"] = True
                if not asset_name.startswith(f"MH{episode}"):
                    results[i]["errors"].append(
                        f"Asset exists and it won't be created."
                    )

            results[i]["status"] = len(results[i]["errors"]) == 0

        return data_frame.columns.tolist(), results

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
                    created_episodes[value["episode"]](ep)
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
                        "task_template": {"id": 442, "type": "TaskTemplate"},
                        "sg_created_for_episode": ep,
                    }
                    created_asset = self.sg.create("Asset", data)
                    created_asset[value["asset_name"]] = created_asset
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


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

    app = QApplication()
    plugin = MeteoHeroesPlugin()
