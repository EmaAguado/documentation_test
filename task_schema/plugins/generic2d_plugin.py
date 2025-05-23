from pathlib import Path
from typing import Iterable
from shutil import copy2
from os import fspath
from datetime import datetime
from logging import getLogger
import sys

base_path = fspath(Path(__file__).parent.parent.parent)
sys.path.append(base_path)


from task_schema.plugins.shotgrid_plugin import ShotgridPlugin
from launcher.qtclasses.toolbar_meteoheroes import MeteoHeoresToolbar

logger = getLogger(__name__)


class Generic2DPlugin(ShotgridPlugin):

    _active_entities = ["Asset", "Episode"]
    add_tasks_from_plugin_kwargs = {"sg_entity_type": "Asset"}
    create_file_ext = ["from selected", "psd/psb", "jpg"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._toolbars += [[MeteoHeoresToolbar,"MeteoHeroes Toolbar"]]
        # self._toolbars += [MeteoHeoresToolbar("MeteoHeroes Toolbar", self)]
        self.version_regex = r"V\d\d\d"
        self._upload_status = "cplt"
        self._version_publish_fields += ["sg_uploader", "sg_path_to_jpg_file"]
        self._dict_previous_tasks = {"color": {"task": "line"}}

    def return_next_version_name(self, ext: Iterable, version: int = None) -> dict:
        # LB101_BG_PRIME_FOREST_TRAP_AREA_EXT_D
        task = self.last_task_clicked
        # print(task.serialize())
        if task is not None:
            task_name = self.task_long_to_short(task.name).upper()
            # TODO: the call to upper() is because at this point the short names
            # of the tasks in shotgrid are lowercase but this should change.
            link = task.link_name
            v, last_file = self.return_last_file(ext)
            v = version or v
            file_name = f"{link}_{task_name}_V{v+1:03}"
            if last_file is None:
                last_file = Path(self.TEMPLATES_FOLDER)

            return {
                "local_path": Path(task.local_path),
                "file_name": file_name,
                "previous_file": last_file,
                "full_file_name": Path(task.local_path, f"{file_name}.{ext[0]}")
            }

    def get_task_filesystem(
        self, code: str, entity_type: str, task: str, *args, **kwargs
    ):

        if entity_type == "Asset":
            asset_type = code.split("_")[1]

            slug = Path("PRODUCTION/ASSETS", asset_type, code, task)
            local_path = Path(self.local_root, slug)
            server_path = Path(self._server_root, slug)
        
        else:
            local_path = None
            server_path = None

        return local_path, server_path



if __name__ == "__main__":
    from logging import DEBUG, basicConfig
    from PySide6.QtWidgets import QApplication
    from task_schema.plugins.anniecarola_plugin import AnnieCarolaPlugin

    basicConfig()
    logger = getLogger()
    logger.setLevel(DEBUG)

    app = QApplication.instance() or QApplication()
    plugin = AnnieCarolaPlugin()
    plugin.create_pack("sb", "AC107", by_task=True)
