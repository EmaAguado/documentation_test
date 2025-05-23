import logging
import os
from pathlib import Path
from re import match, Match, search, compile as rcomp

import pandas

if __name__ == "__main__":
    # these are only required if the module is executed stand alone
    import sys
    from os import fspath

    sys.path.append(fspath(Path(__file__).parent.parent.parent))

from task_schema.plugins.generic2d_plugin import Generic2DPlugin

logger = logging.getLogger(__name__)


class LetrabotsPlugin(Generic2DPlugin):
    TITLE = "LetraBots"
    PLUGIN_UUID = "8b82740c-a1ce-44e0-b3d6-03e177b4fad5"
    # _server_root = Path("\\\\qsrv01.mondotvcanarias.lan\\proj_lb\\LETRABOTS")

    SG_PROJECT_ID = 254
    bdlregex = r"Checklist LB\d\d\d"

    _active_entities = ["Asset", "Sequence", "Episode", "Shot"]
    title = "Letrabots Plugin"

    def __new__(cls: "LetrabotsPlugin", *args, **kwargs) -> "LetrabotsPlugin":
        cls._local_root = Path(cls.env_handler.get_env("LETRABOTS_LOCAL_PATH"))
        cls._server_root = Path(
            cls.env_handler.get_env(
                "LETRABOTS_SERVER_PATH",
                Path("\\\\qsrv01.mondotvcanarias.lan\\proj_lb\\LETRABOTS"),
            )
        )

        cls.TEMPLATES_FOLDER = Path(
            cls._server_root,
            "00_MONDO TV_LETRABOTS/- 05 SMARTWORKING KIT/TEMPLATES",
        )
        cls.BDLS_PATH = Path(cls._server_root, "PRODUCTION", "BDL_FILES")
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
            r"^(?!.*(_)\1)LB(\d\d\d)_(BG|CH|FX|PR)_[0-9A-Z_]+_(V\d\d\d)([A-Za-z0-9\._-]+)?"
        ]
        self._dict_previous_tasks = {
            "color": {"task": "sketch", "step": "conceptArtStep"},
            "raster": {"task": "color", "step": "conceptArtStep"},
        }
        self._edl_target_task = "animatic"
        self._edl_shot_prefix = ""
        self._edl_sequence_prefix = ""
        # self.edl_sequence_regex = rcomp(r"(?<=FT_)[A-Za-z]*_\d\d\d")
        self._edl_ep_in_sq = False
        self._episode_edl_workflow = True
        self._edl_episode_regex = rcomp(r"LB\d{3}")
        self.edl_sequence_regex = rcomp(
            r"(?<=MR)(\d{2,3}_\d\d\d|[A-Z][a-zA-Z0-9]+_\d\d\d)"
        )
        self._edl_shot_regex = rcomp(r"\d\d\d[A-Z]{0,1}(?=_TK\d)")
        # self._sequence_task_template_id =
        self.edl_version_regex = rcomp(r"(?<=_V)\d\d\d")
        self._shot_task_tpl_id = 774
        self._fps = 25

    def get_task_filesystem(self, code, entity_type, task, *args, **kwargs):

        if entity_type == "Asset":
            asset_type = code.split("_")[1]

            ep: Match = match(r"LB\d\d\d", code)
            # ep: Match = search(r"LB\d\d\d", code)

            if ep is None:
                episode = "LB100"
            else:
                episode = ep.group()
            # logger.debug(f"{episode=} {asset_type=} {code=} {task=}")
            slug = Path("PRODUCTION/ASSETS", episode, asset_type, code, task)
            local_path = Path(self.local_root, slug)
            server_path = Path(self._server_root, slug)

        elif entity_type == "Episode":
            # logger.debug(", ".join([code, entity_type, task, asset_type]))
            slug = Path("PRODUCTION/Episodes/", code, task)
            local_path = Path(self.local_root, slug)
            server_path = Path(self._server_root, slug)

        elif entity_type == "Shot":
            # logger.debug(", ".join([code, entity_type, task, asset_type]))
            # LB110_SC223
            slug = Path(
                "PRODUCTION/Episodes/",
                code.split("_")[0],
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
        episode = excel.name.split(" ")[1][:3]
        existing_assets = self.return_all_assets()
        data_frame = pandas.read_excel(excel, skiprows=[0], usecols=[0, 1, 5])
        data_frame = data_frame.dropna(subset=data_frame.columns[1:2])
        data_frame.fillna("", inplace=True)
        results = dict()
        dupes = data_frame.duplicated(
            subset=data_frame.columns[1:2].tolist(), keep=False
        )

        row: pandas.Series
        for i, row in data_frame.iterrows():
            # logger.debug(f"{i} - {row}")
            scene = row[0] or ""
            asset_name = row[1] if row[1].startswith("LB1") and "_" in row[1] else ""
            episode = asset_name[2:5] if asset_name != "" else None
            # asset_name = row[1] if len(row) >= 2 else ""
            scenes = row[2] if len(row) == 3 else ""

            results[i] = {
                "series": row.tolist(),
                "errors": list(),
                "episode": f"LB{episode}",
                "asset_name": row[1],
                "exists": asset_name in existing_assets,
                "status": True,
            }

            if dupes[i]:
                results[i]["errors"].append("This asset is repeated.")

            if " " in asset_name:
                # logger.debug(row[0])
                results[i]["errors"].append(
                    "Naming has white spaces (espacios en blanco)."
                )

            if not match(r"^LB\d\d\d_(BG|CH|FX|PR|LAYOUT)_[0-9A-Z@#_]+", asset_name):
                # logger.debug(asset_name)
                results[i]["errors"].append("Naming of the assets seems wrong.")

            if asset_name in existing_assets:
                results[i]["exists"] = True
                if not asset_name.startswith(f"LB{episode}"):
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
                        "episodes": [ep, created_episodes[value["asset_name"][:5]]],
                        "sg_2d_asset_type": value["asset_name"].split("_")[1],
                        # "sg_production_type" : value["series"][-1],
                        "task_template": {"id": 475, "type": "TaskTemplate"},
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

    def return_seq_and_shot_from_clipname(self, clip_name: str):
        # * FROM CLIP NAME: LB110_SC001_TK0
        shot = clip_name.split(" ")[-1]
        ep, sh, _ = clip_name.split("_")
        return f"{ep}_010", f"{ep}_{sh}"

    # def read_excel(self, excel: Path):
    #     # episode = excel.name.split(" ")[1][2:5]
    #     existing_assets = self.return_all_assets()
    #     data_frame = pandas.read_excel(excel, skiprows=[0], usecols=[0])
    #     data_frame = data_frame.dropna(subset=data_frame.columns[:1])
    #     data_frame.fillna("", inplace=True)
    #     results = dict()
    #     dupes = data_frame.duplicated(
    #         subset=data_frame.columns[:1].tolist(), keep=False
    #     )

    #     row: pandas.Series
    #     for i, row in data_frame.iterrows():
    #         # scene = row[0] or ""
    #         try:
    #             asset_name = row[0] if row[0].startswith("LB1") and "_" in row[0] else ""
    #         except Exception as e:
    #             logger.critical(e)
    #             logger.critical(f"Failed to extract asset name in row {i} with value {row[0]}")
    #             raise(e)
    #         episode = asset_name[2:5] if asset_name != "" else None
    #         # scenes = row[2] if len(row) == 3 else ""

    #         results[i] = {
    #             "series": row.tolist(),
    #             "errors": list(),
    #             "episode": f"LB{episode}",
    #             "asset_name": row[0],
    #             "exists": asset_name in existing_assets,
    #             "status": True,
    #         }

    #         if dupes[i]:
    #             results[i]["errors"].append("This asset is repeated.")

    #         if not match(r"^(LB\d\d\d)_(BG|CH|FX|PR)_[0-9A-Z@#_]+", asset_name):
    #             logger.debug(row[0])
    #             results[i]["errors"].append("Naming of the assets seems wrong.")

    #         if " " in asset_name:
    #             logger.debug(row[0])
    #             results[i]["errors"].append(
    #                 "Naming has white spaces (espacios en blanco)."
    #             )

    #         if asset_name in existing_assets:
    #             results[i]["exists"] = True
    #             if not asset_name.startswith(f"LB{episode}"):
    #                 results[i]["errors"].append(
    #                     f"Asset exists and it won't be created."
    #                 )

    #         results[i]["status"] = len(results[i]["errors"]) == 0

    #     return data_frame.columns.tolist(), results

    # def create_assets_from_bdl(self, dict_with_items: dict, excel_file: Path):
    #     created_assets = self.return_all_assets()
    #     created_episodes = self.return_all_episodes()

    #     project = {"type": "Project", "id": int(self.SG_PROJECT_ID)}

    #     for key, value in dict_with_items.items():
    #         if value["status"]:
    #             if value["episode"] not in created_episodes:
    #                 ep = self.sg.create(
    #                     "Episode", {"code": value["episode"], "project": project}
    #                 )
    #                 created_episodes[value["episode"]](ep)
    #             else:
    #                 ep = created_episodes[value["episode"]]

    #             if value["asset_name"] not in created_assets:
    #                 data = {
    #                     "code": value["asset_name"],
    #                     "project": project,
    #                     "sg_status_list": "ip",
    #                     "episodes": [ep, created_episodes[value["asset_name"][:5]]],
    #                     "sg_2d_asset_type": value["asset_name"].split("_")[1],
    #                     # "sg_production_type" : value["series"][-1],
    #                     "task_template": {"id": 475, "type": "TaskTemplate"},
    #                     "sg_created_for_episode": ep,
    #                 }
    #                 created_asset = self.sg.create("Asset", data)
    #                 created_asset[value["asset_name"]] = created_asset
    #             else:
    #                 created_asset = created_assets[value["asset_name"]]

    #             self.sg.update(
    #                 "Asset",
    #                 created_asset["id"],
    #                 {"episodes": [ep]},
    #                 multi_entity_update_modes={"episodes": "add"},
    #             )

    #             created_assets[value["asset_name"]] = created_asset

    #             yield created_asset


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from os import environ

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

    app = QApplication()
    plugin = LetrabotsPlugin()
