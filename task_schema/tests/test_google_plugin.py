import unittest
from os import environ, fspath
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

from utilities.pipe_utils import find_config, load_dotenv

# Load main env, variables needed for the core tools to work
base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, fspath(base_path))
load_dotenv()
environ["MH_USER_CONFIG_FILE"] = find_config()
environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

if __name__ == "__main__":
    QApplication()

from task_schema.plugins.nivis_plugin import NivisPlugin

class GooglePluginTests(unittest.TestCase):
    """
    This class will run different tests to
    check that the class GooglePlugin works
    as it is intended to work.
    """

    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication()
        else:
            cls.app = QApplication.instance()
        cls.all_task_data = dict()
        cls.p = NivisPlugin()

    def test_instantiate_google(self):
        self.p.instantiate_google()

    def test_open_sheet(self):
        self.p.open_sheet(self.p.GOOGLE_DATA_SHEETS[0])

    def test_sheet_metadata(self):
        self.p.sheet_metadata(self.p.GOOGLE_DATA_SHEETS[0])

    def test_open_worksheet(self):
        sheet = self.p.open_sheet(self.p.GOOGLE_DATA_SHEETS[0])
        self.p.open_worksheet(sheet, all_worksheet=True)

    def test_letter_to_int(self):
        self.p.letter_to_int("B")

    def test_collect_extra_data(self):
        sheet = self.p.open_sheet(self.p.GOOGLE_DATA_SHEETS[0])
        all_data = self.p.open_worksheet(sheet, all_worksheet=True)[0].get_all_values()
        self.p.collect_extra_data(all_data, all_data[0], self.p.LOCATE_EXTRA_DATA)

    def test_collect_data(self):
        sheet = self.p.open_sheet(self.p.GOOGLE_DATA_SHEETS[0])
        all_data = self.p.open_worksheet(sheet, all_worksheet=True)[0].get_all_values()
        self.p.collect_data(all_data, all_data[0], self.p.LOCATE_ENTITY_NAME)

    def test_data_horizontal_to_vertical(self):
        sheet = self.p.open_sheet(self.p.GOOGLE_DATA_SHEETS[0])
        all_data = self.p.open_worksheet(sheet, all_worksheet=True)[0].get_all_values()
        self.p.data_horizontal_to_vertical(all_data)

    def test_get_tasks_data(self):
        self.p.get_tasks_data(self.p.GOOGLE_DATA_SHEETS[0])

    def test_return_thumbnail_path(self):
        gsp_data = self.p.get_tasks_data(self.p.GOOGLE_DATA_SHEETS[0])
        self.p.return_thumbnail_path(gsp_data[0])

    def test_retrieve_cached(self):
        sheet_id, _ = self.p.sheet_metadata(self.p.GOOGLE_DATA_SHEETS[0])
        self.p.retrieve_cached(sheet_id)

    def test_get_all_tasks_data(self):
        self.p.get_all_tasks_data(
            self.all_task_data, **self.p.add_tasks_from_plugin_kwargs
        )

    @unittest.expectedFailure
    def test_error_instantiate_google(self):
        api = self.p.API_KEY
        self.p.API_KEY = None
        try:
            self.p.instantiate_google()
        except:    
            self.p.API_KEY = api
            raise Exception("test ok")

    @unittest.expectedFailure
    def test_error_open_sheet(self):
        self.p.open_sheet()

    @unittest.expectedFailure
    def test_error_sheet_metadata(self):
        self.p.sheet_metadata()

    @unittest.expectedFailure
    def test_error_open_worksheet(self):
        sheet = self.p.open_sheet(self.p.GOOGLE_DATA_SHEETS[0])
        self.p.open_worksheet(all_worksheet=True)

    @unittest.expectedFailure
    def test_error_letter_to_int(self):
        self.p.letter_to_int()

    @unittest.expectedFailure
    def test_error_collect_extra_data(self):
        sheet = self.p.open_sheet(self.p.GOOGLE_DATA_SHEETS[0])
        all_data = self.p.open_worksheet(sheet, all_worksheet=True)[0].get_all_values()
        self.p.collect_extra_data(all_data, all_data[0])

    @unittest.expectedFailure
    def test_error_collect_data(self):
        sheet = self.p.open_sheet(self.p.GOOGLE_DATA_SHEETS[0])
        all_data = self.p.open_worksheet(sheet, all_worksheet=True)[0].get_all_values()
        self.p.collect_data(all_data, all_data[0])

    @unittest.expectedFailure
    def test_error_data_horizontal_to_vertical(self):
        sheet = self.p.open_sheet(self.p.GOOGLE_DATA_SHEETS[0])
        all_data = self.p.open_worksheet(sheet, all_worksheet=True)[0].get_all_values()
        self.p.data_horizontal_to_vertical()

    @unittest.expectedFailure
    def test_error_get_tasks_data(self):
        self.p.get_tasks_data()

    @unittest.expectedFailure
    def test_error_return_thumbnail_path(self):
        self.p.return_thumbnail_path()

    @unittest.expectedFailure
    def test_error_retrieve_cached(self):
        self.p.retrieve_cached()

    @unittest.expectedFailure
    def test_error_get_all_tasks_data(self):
        self.p.get_all_tasks_data()


if __name__ == "__main__":
    # QApplication()
    unittest.main(verbosity=2)
