from pprint import pprint
from shutil import rmtree
import unittest
from os import environ, fspath
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication


# Load main env, variables needed for the core tools to work
app = QApplication.instance() or QApplication()
base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, fspath(base_path))

from utilities.pipe_utils import find_config, load_dotenv
load_dotenv()
environ["MH_USER_CONFIG_FILE"] = find_config()
environ["GWAIO_ICONS_PATH"] = fspath(Path(base_path, "utilities/static/icons"))

from task_schema.plugins.grisu_plugin import GrisuPlugin


class BasePluginTests(unittest.TestCase):
    """
    This class will run different tests to
    check that the class BasePlugin works
    as it is intended to work.
    """

    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication()
        else:
            cls.app = QApplication.instance()
        cls.asset_test = "fakeAsset_standard-tv01"
        cls.all_task_data = dict()
        cls.p = GrisuPlugin()
        cls.p.get_all_tasks_data(
            cls.all_task_data, **cls.p.add_tasks_from_plugin_kwargs
        )
        for task in cls.all_task_data["results"][0]:
            if task.link_name == cls.asset_test and task.name == "color":
                cls.p.last_task_clicked = task
                break

        cls.TEMP_FOLDER = Path(Path(__file__).parent, "temp")
        cls.TEMP_FOLDER.mkdir(exist_ok=True)
        cls.temp_local_file = Path(cls.TEMP_FOLDER, "gri_ch_fakeAsset_standard-tv01_mode_mpr_001.ma")
        cls.temp_local_preview_file = Path(cls.TEMP_FOLDER, "gri_ch_fakeAsset_standard-tv01_mode_mpr_001.jpg")
        f = open(fspath(cls.temp_local_file), mode="w")
        f = open(fspath(cls.temp_local_preview_file), mode="w")
        f.close()

    def test_return_base_task_with_kwargs(self):
        folder = Path(f"{self.p.local_root}/PROD/assets/work/ch/grisu/standard-tv01/modelingStep/modelProd")
        result = self.p.return_base_task_with_kwargs(local_path = folder)
        if result.local_path != folder:
            raise Exception ("Bad result function")

    def test_return_base_tasks_by_path(self):
        folder = Path(f"{self.p.local_root}/PROD/assets/work/ch/grisu/standard-tv01/modelingStep/modelProd/files")
        result = self.p.return_base_tasks_by_path(local_path = folder)
        if fspath(result.local_path) not in fspath(folder):
            raise Exception ("Bad result function")
        
    def test_validate_last_task_path(self):
        self.p.validate_last_task_path()

    def test_create_dir_if_missing(self):
        self.p.create_dir_if_missing(self.p.last_task_clicked.local_path.parent)

    def test_filter_local_files(self):
        result_all = self.p.filter_local_files(self.TEMP_FOLDER,[".ma",".jpg"])
        result_ma = self.p.filter_local_files(self.TEMP_FOLDER,[".ma"])
        result_jpg = self.p.filter_local_files(self.TEMP_FOLDER,[".jpg"])
        result_none = self.p.filter_local_files(self.TEMP_FOLDER,[".none"])
        if any([len(result_all) != 2,  len(result_ma) != 1, len(result_jpg) != 1, result_none != []]):
            raise Exception ("Bad result function")

    def test_file_has_convention(self):
        result_true = self.p.file_has_convention(self.temp_local_file)
        result_false = self.p.file_has_convention(Path(self.TEMP_FOLDER,"Bad_convention.bad"))
        if result_true != True or result_false != False:
            raise Exception ("Bad result function")

    def test_return_last_version_number(self):
        # result_0 = self.p.return_last_version_number(self.p.last_task_clicked.local_path.parent)
        result_1 = self.p.return_last_version_number(self.TEMP_FOLDER)
        if result_1 != 1:#result_0 != 0 or 
            raise Exception ("Bad result function")

    def test_return_last_version_file(self):
        ma = self.p.return_last_version_file(self.TEMP_FOLDER,[".ma"])
        jpg = self.p.return_last_version_file(self.TEMP_FOLDER,[".jpg"])
        none = self.p.return_last_version_file(self.TEMP_FOLDER,[".none"])

        if any([ma == None,jpg == None,none != None]):
            raise Exception ("Bad result function")

    def test_return_last_file(self):
        self.p.return_last_file([".ma"])

    def test_return_file_by_ext(self):
        ma = self.p.return_file_by_ext(self.TEMP_FOLDER,["ma"])
        jpg = self.p.return_file_by_ext(self.TEMP_FOLDER,["jpg"])
        none = self.p.return_file_by_ext(self.TEMP_FOLDER,["none"])

    def test_create_thumbnail(self):
        self.p.create_thumbnail(self.p.last_task_clicked)

    @unittest.expectedFailure
    def test_error_validate_last_task_path(self):
        last = self.p.last_task_clicked
        self.p.last_task_clicked = None
        try:
            self.p.validate_last_task_path()
        except:
            self.p.last_task_clicked = last
            raise Exception("test ok")

    @unittest.expectedFailure
    def test_error_create_dir_if_missing(self):
        self.p.create_dir_if_missing()

    @unittest.expectedFailure
    def test_error_filter_local_files(self):
        self.p.filter_local_files([".ma"])

    @unittest.expectedFailure
    def test_error_file_has_convention(self):
        self.p.file_has_convention()

    @unittest.expectedFailure
    def test_error_return_last_version_number(self):
        self.p.return_last_version_number()

    @unittest.expectedFailure
    def test_error_return_last_version_file_missing_path(self):
        self.p.return_last_version_file(ext=[".ma"])

    @unittest.expectedFailure
    def test_error_return_last_version_file_missing_ext(self):
        self.p.return_last_version_file(self.p.last_task_clicked.local_path.parent)

    @unittest.expectedFailure
    def test_error_return_last_file(self):
        self.p.return_last_file()

    @unittest.expectedFailure
    def test_error_return_file_by_ext_missing_path(self):
        self.p.return_file_by_ext(self.p.last_task_clicked.local_path)

    @unittest.expectedFailure
    def test_error_return_file_by_ext_missing_ext(self):
        self.p.return_file_by_ext(ext=[".ma"])

    @unittest.expectedFailure
    def test_error_create_thumbnail(self):
        self.p.create_thumbnail()

    @classmethod
    def tearDownClass(cls):
        rmtree(cls.TEMP_FOLDER)

if __name__ == "__main__":
    unittest.main(verbosity=2)
