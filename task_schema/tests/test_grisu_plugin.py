import unittest
from os import environ, fspath
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from utilities.pipe_utils import find_config, load_dotenv

# Load main env, variables needed for the core tools to work
base_path = Path(__file__).parent.parent.parent
# os.environ["PYTHONPATH"] = base_path,
sys.path.insert(0, fspath(base_path))
load_dotenv()
environ["MH_USER_CONFIG_FILE"] = find_config()
environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))
app = QApplication.instance() or QApplication()
# Load custom environments for certain plugins/tools to work
from task_schema.plugins.grisu_plugin import GrisuPlugin


class GrisuPluginTests(unittest.TestCase):
    """
    This class will run different tests to
    check that the class GrisuPlugin works
    as it is intended to work.
    """

    @classmethod
    def setUpClass(cls):
        """
        Looks for errors while instantiating,
        mostly NotImplementedErrors.
        """
        if not QApplication.instance():
            cls.app = QApplication()
        else:
            cls.app = QApplication.instance()
        cls.asset_test = "mondohub_test-tv01"
        cls.all_task_data = dict()
        cls.p = GrisuPlugin()
        cls.p.username = "script_test"

        data = {
            "project": {"type": "Project", "id": cls.p.SG_PROJECT_ID},
            "code": "mondohub_test-tv01",
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

    def test_return_next_version_name(self):
        self.p.return_next_version_name([".ma"])

    def test_file_added_callback(self):
        self.p.file_added_callback()

    @unittest.expectedFailure
    def test_error_return_next_version_name_missing_task(self):
        last = self.p.last_task_clicked
        self.p.last_task_clicked = None
        try:
            self.p.return_next_version_name([".ma"])
        except:
            self.p.last_task_clicked = last
            raise Exception("test ok")

    @unittest.expectedFailure
    def test_error_return_next_version_name_missing_ext(self):
        self.p.return_next_version_name()

    @unittest.expectedFailure
    def test_error_file_added_callback(self):
        last = self.p.last_task_clicked
        self.p.last_task_clicked = None
        try:
            self.p.file_added_callback()
        except:
            self.p.last_task_clicked = last
            raise Exception("test ok")

    @classmethod
    def tearDownClass(cls):
        cls.p.sg.delete("Asset", cls.temp_asset.get("id"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
