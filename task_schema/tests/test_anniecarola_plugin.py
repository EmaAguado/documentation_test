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

from task_schema.plugins.anniecarola_plugin import AnnieCarolaPlugin


class AnniecarolaPluginTests(unittest.TestCase):
    """
    This class will run different tests to
    check that the class ShotgridPlugin works
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
        cls.p = AnnieCarolaPlugin()
        cls.p.username = "script_test"
        cls.all_task_data = dict()
        cls.p.get_all_tasks_data(
            cls.all_task_data, force_no_cache=True, **cls.p.add_tasks_from_plugin_kwargs
        )
        cls.p.last_task_clicked = cls.all_task_data["results"][0][0]

    def test_publish_timelog(self):
        self.p.username = "e.aguado"
        r_true = self.p.publish_timelog(
            self.p.last_task_clicked,
            60*8,
        )
        if r_true.get("success") != True:
            raise Exception("Bad result function")
        
    # def test_return_next_version_name(self):
    #     pass

    # def test_get_task_filesystem(self):
    #     pass

    # def test_read_excel(self):
    #     self.p.read_excel(self.p.)
     
    # def test_create_assets_from_bdl(self):
    #     pass

    # @classmethod
    # def tearDownClass(cls):
    #     cls.p.sg.delete("Asset", cls.temp_asset.get("id"))


if __name__ == "__main__":
    # QApplication()
    unittest.main(verbosity=2)
