from collections.abc import Callable
import os
from pathlib import Path
from typing import Iterable

if __name__ == "__main__":
    # these are only required if the module is executed stand alone
    import sys
    from os import fspath

    sys.path.append(fspath(Path(__file__).parent.parent.parent))

from task_schema.plugins.google_plugin import GooglePlugin
from task_schema.plugins.base_plugin import BaseTask, BaseThumbnail


class NivisPlugin(GooglePlugin):
    TITLE = "Nivis"
    PLUGIN_UUID = "43a63dc7-38c8-4819-93e2-3ff45cb38ae0"
    # _server_root = Path("\\\\qsrv01.mondotvcanarias.lan\\NIVIS")

    LOCATE_TASK_NAME = "B3"
    LOCATE_ENTITY_NAME = [0, 1, 2]
    LOCATE_EXTRA_DATA = [
        # [3],
        # [4],
        # [5],
        # [6],
        [7],
        [8],
        [9],
        # [10],
        # [11],
        # [12],
        # [13],
        # [14],
        # [15],
        # [16],
    ]
    LOCATE_START_TASKS = 4
    LOCATE_DIRECTION = 0

    SCOPE = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]

    GOOGLE_DATA_SHEETS = [
        "https://docs.google.com/spreadsheets/d"
        "/1vgKifUFvTFBkmhza7yaUKyTnldZMHGboFAtdWBJ4t9U/"
        "edit?usp=sharing"
    ]

    API_KEY = {
        "type": "service_account",
        "project_id": "tokyo-epoch-342009",
        "private_key_id": "ef35451d8776f20c67ef15bd326e01879bfb9f08",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCu1roXkgRDFu5G\nILK7b8elRI9bED2/+FUjvEt+CSBMfP7GpuPmhPfEUX5xHKgrzbwvNNHJSUrJvJPu\n7N1BlZ2J7T6l1Y6fupv6Do6TPFGrYdrWlcB/wNNFA8M19ddyaHjm5mDMQGAMoxsi\ncMyArPDk55x4YIiCHxjrvx3y6n/5M4BQ9U9so0A8i6REcKvnomJ0NTWpwDYI3oze\nFe8sHLUMjHll4dMC5DJAbAymnmvt1TAsWWzvGkDwldNmfjIj4eTxpYmpZ1d5fieb\nIHix0O62ZmxfRQAkzM7ouYn5AymQLxSrk8l0y3UrQLzfRzAS7y3hGatC6ru8zdir\nDFRKPN/dAgMBAAECggEABe3dQLhgcaAA85rfRND9HcMt82IhHfX/eSdFDiCkGkPw\n5e658tLWji9PUOmuYFHpTFaHuMJGCYJeJ++bb0JyJb/IbJpJ7GvJJ1lAB4k3oc6/\nO6C3dv2kjIYcpCNSq5wUYYw1gye5uiP74xadMM3sm26pVUG8z2DbmP8Rtm+yaFKC\n13Y2HrUJhOEUg3/aQ0YlldAa3VakCek75nO1lgHaYKnbIeSSxdFNds7v8RXxGiuu\n+3Tb+SbbobSFYj+pX2AjRhCp0xGG1rb4dKrWdvt6pavbtvAaF5W6bunyBL1C5O95\nwYwrpOyOlBVa7583eLklehc7Gc2c5dynVo6HrE1VAQKBgQDuVMu3ZI2dDTCvsh8t\n7InUux4ejfDJ11Siz0BVzsWeoMckvfD8kkqlK+nzSJeUkOW81QrmcgAQ5NGHpaiW\nvMNSa7tUgeDjAqni+DU8R3TbcSpujMEjklAUG06wPLypxSfIOVjPRDNNuER967wa\nj7io0MSZFwdd3KZxtVO3NelHgQKBgQC7zO4mEJcUespaJ/W3caHe/bgKrNQLUQK1\nSBGp++ZzBz6WSHxdrihoCQBBkH3ObFZZ7S50Sb+7/Txd3SoyaCenouQsUOTcN/W1\nu5enVBPlhkGIljyO6mT/1v3kiqffjBg1dsnmii+B+AhH0sFiHi59x6BSnSYJN5Ln\np9AzPkDmXQKBgG9/dB7ECAxlU1We+z883e6L67dXqEKFXq8cTnjWV1Wy2feydL90\noT9MoBKU73UtpI0HDiZpRuagZfYT5h8/CBHTHLyYVmFdqaTpgd5Ff8H522QErYa6\nuIPvkoyYnZq/BbGCQq4UtfuyLTjLxCCZBEbWBGOqhmO/Co8/yX541j4BAoGAR+z4\n2MNJ2aIdleHwDc4LfOgXcJ84pwzjyKJNgZjkbfG8WrpwR0DIYO/xlSrNxB1iBRb9\nz7PfJxSZ5ikqXBvf9ChC02Y4AM+931h1gLSG2kVNHA7OKr5C6Gli3ADuwoNZUkCo\nmw8ZmuFv6nIhdn6wt6OZF4rwYl9SeD6hUr7pBFECgYEAzaPMeaCo0fgzz+lxXUZX\nM/4cu5v2m+TW3slGUmZuKTPNYGmn0vu35joge7CcA9I3RpLEFSlkujIMwYdjmwTf\nAmo+5RF80LLq1DScLMzwkz0Jwvj/1CjuzjQ7ooeyW8Osn6dVEXMdVUBPvpby3XVb\niWgZuSvRM4YISG5bppjLhqE=\n-----END PRIVATE KEY-----\n",
        "client_email": "testapitdmdtv@tokyo-epoch-342009.iam.gserviceaccount.com",
        "client_id": "113221502978858697416",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/testapitdmdtv%40tokyo-epoch-342009.iam.gserviceaccount.com",
    }

    SYNC_FOLDERS = [
        Path(
            "D:\\PROJECTS\\NIVIS\\SERVERTEST\\PROYECTOS\\ADOM\\05_LIGHTING\\03_EPISODIOS"
        ),
        Path(
            "D:\\PROJECTS\\NIVIS\\SERVERTEST\\PROYECTOS\\ADOM\\05_LIGHTING\\03_EPISODIOS"
        ),
    ]

    title = "Nivis Plugin"
    add_tasks_from_plugin_kwargs = {"Auto": True}
    create_file_ext = ["from selected", "psd"]

    def __new__(cls: "NivisPlugin", *args, **kwargs) -> "NivisPlugin":
        cls._server_root = Path(
            cls.env_handler.get_env(
                "NIVIS_SERVER_PATH", Path("\\\\qsrv01.mondotvcanarias.lan\\NIVIS")
            )
        )
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._toolbars += []
        self._active_entities = ["Shot"]
        self.local_root = Path(self.env_handler.get_env("NIVIS_LOCAL_PATH"))
        self._headers = [
            "Shot",
            "Task",
            # "Duracion",
            # "Frms anim",
            # "Frame in",
            # "Personajes",
            "Set",
            "Props",
            "Assets",
            # "Dist cam",
            # "Lente",
            # "Altura",
            # "Diafragma",
            # "Shutter",
            # "Observaciones",
            # "Altura 3d",
        ]
        self._naming_regex = [
            r"^ADOM_EP(\d\d\d)_ESC(\d\d)_PL(\d\d\d)_LIGHT_(v\d\d\d).?",
            r"^ADOM_EP(\d\d\d)_ESC(\d\d)_PL(\d\d\d)_ANIM_(v\d\d\d).?",
            r"^ADOM_EP(\d\d\d)_ESC(\d\d)_PL(\d\d\d)_LAY_(v\d\d\d).?",
        ]

        self.version_regex = r"v\d\d\d"
        self._dict_previous_tasks = {
            "lighting": {"task": "animation"},
            "animation": {"task": "layout"},
        }

    def return_next_version_name(self, ext: Iterable) -> dict:
        # ADOM_EP303_ESC01_PL002_LIGHT_v000.ma
        task = self.last_task_clicked
        if task is not None:

            task_name = task.name
            v, last_file = self.return_last_file()

            if task_name == "lighting":
                task_name = "LIGHT"
            elif task_name == "animation":
                task_name = "ANIM"
            elif task_name == "layout":
                task_name = "LAY"

            return {
                "local_path": task.local_path,
                "file_name": (file_name:=f"ADOM_{task.link_name}_{task_name}_v{v+1:03}"),
                "previous_file": last_file,
                "full_file_name": Path(task.local_path, f"{file_name}.{ext[0]}")
            }

    def return_thumbnail_path(self, entity) -> str:
        code = entity[0]
        task = entity[1]
        split_code = code.split("_")
        ep = split_code[0]
        sq = split_code[1]
        sh = split_code[2]

        if task == "lighting":
            task = "LIGHT"
        elif task == "animation":
            task = "ANIM"
        elif task == "layout":
            task = "LAY"

        return Path(
            self.get_task_filesystem(entity[0], entity[1])[0],
            "THUMBNAILS",
            f"ADOM_{ep}_{sq}_{sh}_{task}.jpg",
        )

    def get_task_filesystem(self, code, task, *args, **kwargs):

        if task == "lighting":

            task_main_folder = "05_LIGHTING"
            task_folder = "LIGHT"
            entity_type = "03_EPISODIOS"

        elif task == "animation":

            task_main_folder = "04_ANIMATION"
            task_folder = "ANIM"
            entity_type = "03_EPISODIOS"

        elif task == "layout":

            task_main_folder = "04_ANIMATION"
            task_folder = "LAY"
            entity_type = "03_EPISODIOS"

        else:
            local_path = Path()
            server_path = Path()

        if task in ["lighting", "animation", "layout"]:
            split_code = code.split("_")
            ep = split_code[0]
            sq = split_code[1]
            sh = split_code[2]

            slug = Path(
                "PROYECTOS/ADOM", task_main_folder, entity_type, ep, sq, sh, task_folder
            )

            local_path = Path(self.local_root, slug)
            server_path = Path(self._server_root, slug)

        return local_path, server_path

    def get_all_tasks_data(
        self,
        return_object: dict,
        callback: Callable = None,
        force_no_cache: bool = False,
        *args,
        **kwargs,
    ) -> None:

        all_tasks = list()
        for sheet_link in self.GOOGLE_DATA_SHEETS:
            sheet_id, last_modified = self.sheet_metadata(sheet_link)
            gsp_data, cached_task_date = self.retrieve_cached(sheet_id)
            if cached_task_date is None or force_no_cache:
                gsp_data = self.get_tasks_data(sheet_link)
            elif last_modified > cached_task_date:
                gsp_data = self.get_tasks_data(sheet_link)

            for task_entity in gsp_data:
                local_path, server_path = self.get_task_filesystem(
                    task_entity[0], task_entity[1]
                )
                extra_data = [{"text": e} for e in task_entity[2:]]
                data_to_show = [
                    {
                        "text": task_entity[0],
                        "thumbnail": self.return_thumbnail_path(task_entity),
                        "icon": None,
                    },
                    {"text": task_entity[1]},
                    *extra_data,
                ]

                prev_task_server = Path()

                if self._dict_previous_tasks.get(task_entity[1]):
                    prev_task_server = self.get_task_filesystem(
                        task_entity[0], **self._dict_previous_tasks.get(task_entity[1])
                    )[1]

                task = NivisTask(
                    task_entity[1],
                    task_entity[0],
                    local_path,
                    prev_task_server,
                    server_path=server_path,
                    data_to_show=data_to_show,
                    thumbnail=BaseThumbnail(),
                )
                all_tasks.append(task)

            self.cache_data(sheet_id, gsp_data)

        return_object["results"] = all_tasks, self.headers

        if callback is not None:
            callback()

    def publish_version(self, version: Path) -> bool:

        return {
            "success": True,
            "message": "Upload was successfull",
            "error": None,
        }

    def get_tasks_data(self, sheet_link, worksheet_id=0) -> list:
        sheet = self.open_sheet(sheet_link)
        list_worksheet = self.open_worksheet(sheet, all_worksheet=True)
        tasks_data = []
        for worksheet in list_worksheet:
            all_data = worksheet.get_all_values()
            if self.LOCATE_DIRECTION == 1:
                all_data = self.data_horizontal_to_vertical(all_data)

            for task in all_data[self.LOCATE_START_TASKS :]:
                for task_name in ["layout", "animation", "lighting"]:
                    asset_name = self.collect_data(
                        all_data, task, self.LOCATE_ENTITY_NAME
                    )
                    ep, sq, sh = asset_name.split("_")
                    asset_name = f"{ep}_ESC{sq}_PL{sh}"
                    extra_data = self.collect_extra_data(
                        all_data, task, self.LOCATE_EXTRA_DATA
                    )
                    tasks_data.append([asset_name, task_name, *extra_data])

        return tasks_data


class NivisTask(BaseTask):
    # @property
    # def thumbnail(self):
    #     return Path(
    #         self.local_path,
    #         "THUMBNAILS",
    #         self.return_thumbnail_name(self.link_name, self.name),
    #     )

    def return_thumbnail_name(self, code, task) -> str:

        split_code = code.split("_")
        ep = split_code[0]
        sq = split_code[1]
        sh = split_code[2]

        if task == "lighting":
            task = "LIGHT"
        elif task == "animation":
            task = "ANIM"
        elif task == "layout":
            task = "LAY"

        return f"ADOM_{ep}_{sq}_{sh}_{task}.jpg"


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from os import environ

    base_path = Path(__file__).parent.parent.parent
    environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

    app = QApplication()
    plugin = NivisPlugin()
