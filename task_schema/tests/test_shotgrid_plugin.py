from pprint import pprint
from shutil import rmtree
import unittest
from os import environ, fspath
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

# Load main env, variables needed for the core tools to work
base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, fspath(base_path))
from utilities.pipe_utils import find_config, load_dotenv
load_dotenv()
environ["MH_USER_CONFIG_FILE"] = find_config()
environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

if __name__ == "__main__":
    app = QApplication().instance() or QApplication()

from task_schema.plugins.grisu_plugin import GrisuPlugin


class ShotgridPluginTests(unittest.TestCase):
    """
    This class will run different tests to
    check that the class ShotgridPlugin works
    as it is intended to work.
    """

    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication()
        else:
            cls.app = QApplication.instance()

        cls.TEMP_FOLDER = Path(Path(__file__).parent, "temp")
        cls.TEMP_FOLDER.mkdir(exist_ok=True)
        cls.asset_test = "mondohub_test-tv01"
        cls.asset_notes_test = "grisu_standard-tv01"
        cls.all_task_data = dict()
        cls.p = GrisuPlugin()
        cls.p.username = "script_test"

        data = {
            "project": {"type": "Project", "id": cls.p.SG_PROJECT_ID},
            "code": "mondohub_test-tv01",
            "description": "This is a temp asset test",
            "sg_status_list": "ip",
            "task_template": {
                "id": 46,
                "name": "Grisu - asset - ch",
                "sg_asset_type": "ch",
                "type": "TaskTemplate",
            },
        }
        cls.temp_asset = cls.p.sg.create("Asset", data)
        task = cls.p.sg.find_one("Task", [["entity.Asset.id", "is", cls.temp_asset["id"]]], [])
        cls.p.sg.update(
            "Task",
            task["id"],
            {
                "sg_status_list": "rdy",
            },
        )

        cls.p.get_all_tasks_data(
            cls.all_task_data, force_no_cache=True, **cls.p.add_tasks_from_plugin_kwargs
        )
        for task in cls.all_task_data["results"][0]:
            if task.link_name == cls.asset_test:
                cls.p.last_task_clicked = task
                break

    def test_task_long_to_short(self):
        self.p.task_long_to_short("modelProd")

    def test_retrieve_cached(self):
        r = self.p.retrieve_cached("Asset")
        l, d = self.p.retrieve_cached("BAD")

        if l != list() or d != None:
            raise Exception("Bad result function")

    def test_check_version_is_published(self):
        r_true = self.p.check_version_is_published(
            Path(Path(), "gri_ch_grisu_standard-tv01_look_lde_062_standardTurntable")
        )
        r_false = self.p.check_version_is_published(Path())
        if r_true != True or r_false != False:
            raise Exception("Bad result function")

    def test_return_all_assets(self):
        self.p.return_all_assets()

    def test_return_all_episodes(self):
        self.p.return_all_episodes()

    def test_return_all_playlists(self):
        self.p.return_all_playlists()

    def test_return_all_versions(self):
        self.p.return_all_versions()

    def test_return_entity_description(self):
        r = self.p.return_entity_description(self.p.last_task_clicked)
        if r != "This is a temp asset test":
            raise Exception("Bad result function")

    def test_return_playlist_media(self):
        r_true = self.p.return_playlist_media(12288)
        r_false = self.p.return_playlist_media(1)
        if r_true == list() or r_false != list():
            raise Exception("Bad result function")

    def test_return_task_notes(self):
        r_false = self.p.return_task_notes(self.p.last_task_clicked)
        last = self.p.last_task_clicked
        for task in self.all_task_data["results"][0]:
            if task.link_name == self.asset_notes_test:
                self.p.last_task_clicked = task
                break
        r_true = self.p.return_task_notes(self.p.last_task_clicked)
        self.p.last_task_clicked = last
        if r_true == list() or r_false != list():
            raise Exception("Bad result function")

    def test_download_thumbnail_from_sg(self):
        r_false = self.p.download_thumbnail_from_sg(
            "Task",
            self.p.last_task_clicked.task_entity.get("id"),
            Path(self.TEMP_FOLDER, "thumb.jpg"),
        )
        if r_false != False:
            raise Exception("Bad result function")

    def test_publish_version(self):
        r_true = self.p.publish_version(
            self.p.last_task_clicked,
            Path(Path(__file__).parent, "mondohub_version_test.png"),
            "Test",
        )
        if r_true.get("success") != True:
            raise Exception("Bad result function")
        
    def test_publish_file(self):
        r_true = self.p.publish_file(
            Path(Path(__file__).parent, "test.ma"),
            self.p.last_task_clicked,
            "Test",
        )
        if r_true.get("success") != True:
            raise Exception("Bad result function")
        
    # def test_publish_timelog(self):
    #     self.p.username = "e.aguado"
    #     r_true = self.p.publish_timelog(
    #         self.p.last_task_clicked,
    #         60*8,
    #     )
    #     if r_true.get("success") != True:
    #         raise Exception("Bad result function")

    def test_publish_version_download_thumbnail_from_sg(self):
        r_true = self.p.download_thumbnail_from_sg(
            "Task",
            self.p.last_task_clicked.task_entity.get("id"),
            Path(self.TEMP_FOLDER, "thumb.jpg"),
        )
        if r_true != True:
            raise Exception("Bad result function")

    @unittest.expectedFailure
    def test_error_task_long_to_short(self):
        self.p.task_long_to_short()

    @unittest.expectedFailure
    def test_error_retrieve_cached(self):
        self.p.retrieve_cached()

    @unittest.expectedFailure
    def test_error_check_version_is_published(self):
        self.p.check_version_is_published()

    @unittest.expectedFailure
    def test_error_return_all_assets(self):
        last = self.p.SG_PROJECT_ID
        self.p.SG_PROJECT_ID = None
        try:
            self.p.return_all_assets()
        except:
            self.p.SG_PROJECT_ID = last
            raise Exception("test ok")

    @unittest.expectedFailure
    def test_error_return_all_episodes(self):
        last = self.p.SG_PROJECT_ID
        self.p.SG_PROJECT_ID = None
        try:
            self.p.return_all_episodes()
        except:
            self.p.SG_PROJECT_ID = last
            raise Exception("test ok")

    @unittest.expectedFailure
    def test_error_return_all_playlists(self):
        last = self.p.plugin_task_filters
        self.p.plugin_task_filters = None
        try:
            self.p.return_all_playlists()
        except:
            self.p.plugin_task_filters = last
            raise Exception("test ok")

    @unittest.expectedFailure
    def test_error_return_all_versions(self):
        last = self.p.SG_PROJECT_ID
        self.p.SG_PROJECT_ID = None
        try:
            self.p.return_all_versions()
        except:
            self.p.SG_PROJECT_ID = last
            raise Exception("test ok")

    @unittest.expectedFailure
    def test_error_return_entity_description(self):
        self.p.return_entity_description()

    @unittest.expectedFailure
    def test_error_return_playlist_media(self):
        self.p.return_playlist_media()

    @unittest.expectedFailure
    def test_error_return_task_notes(self):
        self.p.return_task_notes()

    @unittest.expectedFailure
    def test_error_download_thumbnail_from_sg(self):
        try:
            self.p.download_thumbnail_from_sg(
                "Task",
                self.p.last_task_clicked.task_entity.get("id"),
            )
            return
        except:
            pass
        try:
            self.p.download_thumbnail_from_sg(
                "Task",
                path=Path(__file__).parent,
            )
            return
        except:
            pass
        try:
            self.p.download_thumbnail_from_sg(
                id=self.p.last_task_clicked.task_entity.get("id"),
                path=Path(__file__).parent,
            )
        except:
            raise Exception("test ok")

    @unittest.expectedFailure
    def test_error_publish_version(self):
        self.p.publish_version()

    @classmethod
    def tearDownClass(cls):
        input("CHECK")
        cls.p.sg.delete("Asset", cls.temp_asset.get("id"))
        rmtree(cls.TEMP_FOLDER)


if __name__ == "__main__":
    # QApplication()
    unittest.main(verbosity=2)
