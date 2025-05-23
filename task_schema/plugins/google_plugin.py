from collections.abc import Callable
from datetime import datetime
import logging
from pathlib import Path
import json

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from task_schema.plugins.base_plugin import BasePlugin, BaseTask
from launcher.qtclasses.toolbar_google import GoogleToolbar


class GooglePlugin(BasePlugin):
    TITLE = "Google"
    # _server_root = Path("\\\\qsrv01.mondotvcanarias.lan\\NIVIS")


    LOCATE_TASK_NAME = "B3"
    LOCATE_ASSET_NAME = ["B1", 3, 4]
    LOCATE_START_TASKS = 8
    LOCATE_DIRECTION = 0

    SCOPE = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]

    GOOGLE_DATA_SHEETS = [
        "https://docs.google.com/spreadsheets/d"
        "/1jQOi6i2WusBxX4oXHaU7bZjMxnvJ"
        "56Scoifv3P5-WMY/edit#gid=0"
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

    title = "Google Plugin"

    def __new__(cls: "GooglePlugin", *args, **kwargs) -> "GooglePlugin":
        cls._server_root = Path(
            cls.env_handler.get_env(
                "NIVIS_SERVER_PATH", Path("\\\\qsrv01.mondotvcanarias.lan\\NIVIS")
            )
        )
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._headers = ["asset", "task"]
        self._active_entities = ["Shot"]
        self._toolbars += [
            GoogleToolbar("Google Toolbar", self),
        ]

        self.gsp = self.instantiate_google()

    @property
    def active_entities(self):
        return self._active_entities

    def instantiate_google(self) -> gspread:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            self.API_KEY, self.SCOPE
        )

        return gspread.authorize(creds)

    def __del__(self):
        self.gsp.session.close()

    def open_sheet(self, link) -> gspread.spreadsheet.Spreadsheet:
        """
        link (str): sheet's name or sheet's link
        """
        if "https://" in link:
            sheet = self.gsp.open_by_url(link)
        else:
            sheet = self.gsp.open(link)

        return sheet

    def sheet_metadata(self, link) -> str:
        sheet = self.open_sheet(link)
        try:
            return sheet.id, datetime.strptime(
                sheet.lastUpdateTime, "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        except:
            logging.error("[ERROR] API No permission sheet")
        return None

    def open_worksheet(self, sheet, worksheet_id=0, all_worksheet=False) -> list:
        """
        worksheet (int or str): id(int) or name(str)
        """
        if all_worksheet:
            worksheet = sheet.worksheets()
        elif isinstance(worksheet_id, int):
            worksheet = [sheet.get_worksheet(worksheet_id)]
        else:
            worksheet = [sheet.worksheet(worksheet_id)]

        return worksheet

    def letter_to_int(self, col_letter) -> int:
        pow = 1
        col_num = 0
        for letter in col_letter[::-1]:
            col_num += (int(letter, 36) - 9) * pow
            pow *= 26
        return col_num - 1

    def collect_extra_data(self, all_tasks_data, task_data, compile_code) -> list:
        result = list()
        for code in compile_code:
            result.append(self.collect_data(all_tasks_data, task_data, code))
        return result

    def collect_data(self, all_tasks_data, task_data, compile_code) -> str:
        """
        example: compile_code = ["B1",4,5]
        """
        collect_cells = []

        if not isinstance(compile_code, list):
            compile_code = [compile_code]
        for code in compile_code:
            if isinstance(code, str):
                collect_cells.append(
                    all_tasks_data[int(code[1]) - 1][self.letter_to_int(code[0])]
                )
            elif isinstance(code, int):
                collect_cells.append(task_data[int(code)])

        if len(collect_cells) > 1:
            result = "_".join(collect_cells)
        else:
            result = collect_cells[0]

        return result

    def data_horizontal_to_vertical(self, data) -> list:
        num_col = max([len(row) for row in data])
        new_data = [[] for x in range(0, num_col)]
        for row in data:
            for idx, col in enumerate(row):
                new_data[idx].append(col)

        return new_data

    def get_tasks_data(self, sheet_link, worksheet_id=0) -> list:
        sheet = self.open_sheet(sheet_link)
        list_worksheet = self.open_worksheet(sheet, all_worksheet=True)
        tasks_data = []
        for worksheet in list_worksheet:
            all_data = worksheet.get_all_values()
            if self.LOCATE_DIRECTION == 1:
                all_data = self.data_horizontal_to_vertical(all_data)

            for task in all_data[self.LOCATE_START_TASKS]:

                asset_name = self.collect_data(all_data, task, self.LOCATE_ENTITY_NAME)
                task_name = self.collect_data(all_data, task, self.LOCATE_TASK_NAME)
                extra_data = self.collect_extra_data(
                    all_data, task, self.LOCATE_EXTRA_DATA
                )
                tasks_data.append([asset_name, task_name, *extra_data])

        return tasks_data

    def return_thumbnail_path(self, *args, **kwargs) -> str:
        return None

    def get_all_tasks_data(
        self,
        return_object: dict,
        callback: Callable = None,
        force_no_cache: bool = False,
        *args,
        **kwargs
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

                task = BaseTask(
                    task_entity[1],
                    task_entity[0],
                    local_path,
                    prev_task_server,
                    server_path=server_path,
                    data_to_show=data_to_show,
                )
                all_tasks.append(task)

            self.cache_data(sheet_id, gsp_data)

        return_object["results"] = all_tasks, self.headers

        if callback is not None:
            callback()

    def retrieve_cached(self, sheet_link: str):
        cached_data_file = Path(self.local_root, "gsp_cache_" + sheet_link + ".json")
        if cached_data_file.exists():
            try:
                cached_task_data = json.loads(cached_data_file.read_text())
                last_cached = cached_data_file.stat().st_mtime

                return cached_task_data, datetime.fromtimestamp(last_cached)
            except Exception as e:
                logging.error(e)
        return list(), None

    def cache_data(self, sheet_link: str, data: list):
        cached_data_file = Path(self.local_root, "gsp_cache_" + sheet_link + ".json")
        with cached_data_file.open("w") as ftw:
            json.dump(data, ftw, separators=(", ", ": "), indent=4)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    plugin = GooglePlugin()
