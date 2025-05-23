"""
base_plugin.py

This module provides the BasePlugin system for managing tasks,
thumbnails, and plugin environment within the launcher application.
It includes the BaseThumbnail, BaseTask, and BasePlugin classes
"""

import inspect
from os import environ, fspath, getcwd, remove, rename, pathsep
from os.path import getmtime
from re import match, search, sub, Match
import os.path
import json
from logging import getLogger
from sys import platform
import time
from typing import Callable, Iterable, Iterator, Union
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)
import imghdr
from shutil import copy2

# from PIL import Image

from utilities.pipe_utils import (
    return_version_number_from_string,
    replace_root_in_path,
    return_file_name_head,
    open_file,
    open_app,
)
from launcher.qtclasses.dialog_env_handler import EnvironmentHandler

from launcher.qtclasses.toolbar_base import BaseToolbar
from launcher.qtclasses.toolbar_explorer import ExplorerToolbar

from launcher.qtclasses.toolbar_player import PlayerToolbar
from launcher.qtclasses.toolbar_syncer import SyncerToolbar

logger = getLogger(__name__)


class BaseThumbnail:
    """
    Represents a thumbnail resource for a task.

    Attributes:
        id (int): Unique identifier for the thumbnail.
        on_refresh_url (Optional[Callable[[], str]]): Callback to refresh URL.
    """

    def __init__(
        self,
        id: int,
        url: str = None,
        path: Path = None,
        on_refresh_url=None,
        *args,
        **kwargs,
    ):
        self.id = id
        self._url: str = url
        self._path: Path = path
        self.on_refresh_url = on_refresh_url

        self.__dict__.update(kwargs)

    @property
    def url(self):
        """Get the thumbnail URL."""
        return self._url

    @property
    def path(self):
        """Get the thumbnail local path."""
        return self._path

    def refresh_url(self) -> Optional[str]:
        """
        Refresh and return the thumbnail URL via callback.

        Returns:
            Optional[str]: Updated URL.
        """
        if self.on_refresh_url is not None:
            self._url = self.on_refresh_url()
        return self._url


class BaseTask:
    """
    Represents a unit of work within a plugin, including paths and metadata.

    Attributes:
        name (str): Task name (e.g., 'refine', 'model').
        link_name (str): Linked entity name.
        local_path (Path): Local path of the task.
        prev_task_server (Path): Server path of previous task.
        thumbnail (BaseThumbnail): Thumbnail metadata.
        data_to_show (List[Any]): Data rows to display.
    """

    def __init__(
        self,
        name: str,
        link_name: str,
        local_path: Path,
        prev_task_server: Path,
        thumbnail: BaseThumbnail,
        data_to_show,
        *args,
        **kwargs,
    ) -> None:
        # TODO: check whether we want to make compulsory to receive server_path
        # or we want to keep it up to the user. This is related to
        # some toolbars requiring a server path, such as sync or explorer

        # TODO: think about implementing callback system for descriptor value changes,
        # so that this in focal be passed to the child members

        self.name: str = name  # Name of the task (refine, model, etc.)
        # Name of the shot, asset, episode, etc...
        self.link_name: str = link_name
        self.local_path: Path = local_path
        self.prev_task_server: Path = prev_task_server
        self.thumbnail: BaseThumbnail = thumbnail
        self.data_to_show: list = data_to_show
        self._headers = list()

        self.__dict__.update(kwargs)

    @property
    def thumbnail(self):
        """Get the thumbnail object."""
        return self._thumbnail

    @thumbnail.setter
    def thumbnail(self, value: str):
        self._thumbnail = value

    @property
    def name(self) -> str:
        """Get the task name."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if isinstance(value, str):
            self._name = value
        else:
            self._name = ""
            logger.error(f"Value must be an instance of {str} {value}")
            # raise ValueError(f"Value must be an instance of {str}")

    @property
    def link_name(self) -> str:
        """Get the link name."""
        return self._link_name

    @link_name.setter
    def link_name(self, value: str) -> None:
        if isinstance(value, str):
            self._link_name = value
        else:
            self._link_name = ""
            logger.error(f"Value must be an instance of {str} {value}")
            # raise ValueError(f"Value must be an instance of {str}")

    @property
    def local_path(self) -> Path:
        """Get the task's local path."""
        return self._local_path

    @local_path.setter
    def local_path(self, value: Path):
        if isinstance(value, Path):
            self._local_path = value
            # if not value.exists():
            #     value.mkdir(parents=True, exist_ok=True)
        else:
            self._local_path = Path(value)
            logger.error(f"Value must be an instance of {Path} {value}")
            # raise ValueError(f"Value must be an instance of {Path}")

    @property
    def data_to_show(self) -> List[Any]:
        """Get the data to show in UI list."""
        return self._data_to_show

    @data_to_show.setter
    def data_to_show(self, value: List[Any]) -> None:
        if isinstance(value, list):
            self._data_to_show = value
        else:
            self._data_to_show = ""
            logger.error(f"Value must be an instance of {list} {value}")
            # raise ValueError(f"Value must be an instance of {list}")

    def stringify_class(self, class_):
        if isinstance(class_, list | tuple):
            return [n := self.stringify_class(item) for item in class_]
        elif isinstance(class_, dict):
            return {key: self.stringify_class(value) for key, value in class_.items()}
        return str(class_)

    # def serialize(self):
    #     new_dict = dict()
    #     for key, value in self.__dict__.items():
    #         try:
    #             json.dumps(value)
    #             new_dict[key] = value
    #         except:
    #             new_dict[key] = self.stringify_class(value)
    #     return new_dict

    # def deserialize(self,data):
    #     if isinstance(data,str):
    #         data = json.loads(data)
    #     for key, value in data.items():
    #         setattr(self, key, value)

    def serialize(self) -> Dict[str, Any]:
        """
        Serialize the task object's public attributes to a dictionary.

        Returns:
            Dict[str, Any]: Serialized key-value mapping.
        """
        new_dict = {}
        for name, value in inspect.getmembers(self):
            if (
                not name.startswith("_")
                and not inspect.ismethod(value)
                and not inspect.isfunction(value)
            ):
                if inspect.isdatadescriptor(value):
                    value = getattr(self, name)  # Obtiene el valor de la propiedad
                try:
                    json.dumps(value)
                    new_dict[name] = value
                except (TypeError, OverflowError):
                    new_dict[name] = self.stringify_class(value)
        return new_dict

    def deserialize(self, data: Union[str, Dict[str, Any]]) -> None:
        """
        Populate this object from serialized dictionary or JSON string.

        Args:
            data (Union[str, Dict[str, Any]]): JSON string or dict.
        """
        if isinstance(data, str):
            data = json.loads(data)
        for key, value in data.items():
            setattr(self, key, value)


class BasePlugin:
    """
    Core plugin class providing shared launcher functionality.

    Class Attributes:
        TITLE (str): Display title of the plugin.
        PLUGIN_UUID (Optional[str]): Unique identifier.
        super_user (str): Username for elevated operations.
        env_handler (EnvironmentHandler): Environment manager for environment variables.
        TEMPLATES_FOLDER (Path): Path to templates folder.
        BDLS_PATH (Path): Path for BDLs files.
        SL_SERVER_PATH (Path): Path for session logs on server.
        GWAIO_DEADLINE_REPO_PATH (str): Path for Deadline repository.
        OCIO_FILE (Optional[Path]): Filepath for OCIO configuration.
        CUSTOM_MAYA_TOOLS (Optional[Path]): Path for custom Maya tools.
        CUSTOM_NUKE_TOOLS (Optional[Path]): Path for custom Nuke tools.
        CUSTOM_HOUDINI_TOOLS (Optional[Path]): Path for custom Houdini tools.
        GWAIO_MAYA_LIGHT_TEMPLATE (Path): Default Maya light rig template.
        title (str): Human-readable title of the plugin.
        uses_deadline (bool): Flag indicating Deadline integration.
        create_file_ext (List[str]): Default file extensions for creation.
        task_subfolders (Dict[str, List[str]]): Default subfolders for each task.
    """

    TITLE = "Base"
    PLUGIN_UUID = None
    _server_root: Path = Path(getcwd())
    _local_root: Path = Path(getcwd())
    RENDER_FARM_ROOT = _server_root
    RENDER_FARM_FFMPEG_PATH = _server_root
    super_user = "gwaio"
    env_handler = EnvironmentHandler()
    # This is now a Path but at the end of init it is turned to a string as
    # some Qt classes don't work well with Path class, such as QPixmap or QIcon
    TEMPLATES_FOLDER: Path = _server_root
    BDLS_PATH: Path = _server_root
    SL_SERVER_PATH = Path(_server_root)
    GWAIO_DEADLINE_REPO_PATH = ""
    OCIO_FILE: Path = None
    CUSTOM_MAYA_TOOLS: Path = None
    CUSTOM_NUKE_TOOLS: Path = None
    CUSTOM_HOUDINI_TOOLS: Path = None
    GWAIO_MAYA_LIGHT_TEMPLATE: Path = Path(
        TEMPLATES_FOLDER, "/maya/lookdev_light_rig_master.ma"
    )

    # UNC_PREFIX_0 = "\\\\qsrv01.mondotvcanarias.lan\\data0\\PROJECTS\\"
    # UNC_PREFIX_2 = "\\\\qsrv01.mondotvcanarias.lan\\data2\\PROYECTOS\\"
    # UNC_PREFIX_MH = "\\\\qsrv01.mondotvcanarias.lan\\proj_mh\\"
    # UNC_PREFIX_LB = "\\\\qsrv01.mondotvcanarias.lan\\proj_lb\\"

    title = "Base Plugin"
    uses_deadline = False
    add_tasks_from_plugin_kwargs = None
    create_file_ext = ["from selected"]
    bdlregex: str = None
    task_subfolders = dict()
    _folders_to_sync = list()

    def __init__(self, username: str = None, *args, **kwargs) -> None:
        """
        Initialize the BasePlugin instance.

        Args:
            username (Optional[str]): Username of the current user.
        """
        # TODO: should the plugin own the toolbars? if so, do they need to be
        # instantiated on plugin instantiation?
        # self.remap_smb_paths()
        # TODO: test whether we can remove this, as the get_env method from the
        # env_handler already returns a stripped path

        # TODO: the setters are not called unless we do this

        if Path(self.local_root) != Path(self.local_root).parent:
            self.local_root = Path(
                sub(r"(\/|\\)$", "", fspath(self._local_root).strip())
            )
        else:
            self.local_root = sub(r"(\/|\\)$", "/", fspath(self._local_root).strip())
        if Path(self.server_root) != Path(self.server_root).parent:
            self.server_root = Path(
                sub(r"(\/|\\)$", "", fspath(self._server_root).strip())
            )
        else:
            self.server_root = Path(
                sub(r"(\/|\\)$", "/", fspath(self._server_root).strip())
            )
        self._toolbars: list[BaseToolbar] = [
            [ExplorerToolbar, "Explorer Toolbar", "right"],
            [SyncerToolbar, "Syncer Toolbar", "right"],
        ]
        # self._toolbars: list[BaseToolbar] = [
        #     # ExplorerToolbar("Explorer Toolbar", self),
        #     # SyncerToolbar("Syncer Toolbar", self),
        #     # PlayerToolbar("Player Toolbar", self),
        # ]
        self._jobs: list = list()
        self._apps: list = [
            ("Maya", "MAYA_BIN"),
            ("Photoshop", "PHOTOSHOP_BIN"),
            ("Houdini", "HOUDINI_BIN"),
            ("Nuke", "NUKE_BIN"),
            # ("Substance painter","PAINTER_BIN"),
            ("Deadline", "DEADLINE_BIN"),
        ]
        # self._local_root: Path = None
        self._app_toolbars: list[BaseToolbar] = list()
        self._last_task_clicked: BaseTask = None
        self._tasks: list[BaseTask] = []
        self._current_selected_tasks: list[BaseTask] = []
        self._current_selected_files: list[Path] = []
        self._last_file_clicked: Path = None
        self._naming_regex: list[str] = list()
        self._version_regex = r""
        self._version_includes_entity = False
        self._dict_previous_tasks: dict[str, dict] = dict()
        self._dict_file_templates: dict[str, Path] = dict()
        self._username: str | None = username
        self._preview_location: Path = ""
        self._textures_location: Path = ""
        self._export_location: Path = ""
        self._fps: int | None = None
        self._cam_rig: Path | None = None
        self._starting_frame: int | None = None
        self._playblast_res: str | None = None
        self._qa_config: dict | None = dict()
        self._asset_folder_regex: str | None = None
        self._asset_folder: str | None = None
        self._episode_edl_workflow: bool = False
        self._edl_ep_in_sq: bool = True  # ep prefix in shot names
        self._edl_target_task = None
        self._edl_task_name = None
        self._edl_shot_prefix: str = ""
        self._edl_shot_regex: str = ""
        self._edl_sequence_prefix: str = ""
        self._edl_episode_prefix: str = ""
        self._compulsory_publish_fields = []
        self._active_entity: str = None
        self._shot_animatic_resolution: str | None = None
        logger.debug(
            f"Plugin {self.__class__} was instantiated for user {self._username}"
        )

        self.env_handler.get_env("GWAIO_LOCAL_ROOT")
        self.env_handler.get_env("GWAIO_SERVER_ROOT")

    @property
    def username(self):
        """str: Username of the plugin user."""
        return self._username

    @username.setter
    def username(self, value: str):
        self._username = value

    @property
    def dict_previous_tasks(self):
        # This dictionary must be created specific to each project, keep these guidelines:
        # - You must only add the get_task_filesystem arguments of the specific plugin to be
        #   changed when creating the previous version path.
        # - Always add the task key
        return self._dict_previous_tasks

    @property
    def naming_regex(self):
        return self._naming_regex

    @property
    def local_root(self):
        """Path: Local root directory for the project."""
        return self._local_root

    @local_root.setter
    def local_root(self, value: Union[str, Path]):
        if isinstance(value, (Path, str)):
            self._local_root = Path(value)
            environ["GWAIO_LOCAL_ROOT"] = fspath(value)
            self.env_handler.app_env["GWAIO_LOCAL_ROOT"] = fspath(value)
            self.env_handler.add_to_dotenv("GWAIO_LOCAL_ROOT")
        else:
            raise ValueError(f"Value must be a instance of {Path} or {str}")

    @property
    def server_root(self):
        """Path: Server root directory for the project."""
        return self._server_root

    @server_root.setter
    def server_root(self, value: Union[str, Path]):
        if isinstance(value, (Path, str)):
            self._server_root = Path(value)
            environ["GWAIO_SERVER_ROOT"] = fspath(value)
            self.env_handler.app_env["GWAIO_SERVER_ROOT"] = fspath(value)
            self.env_handler.add_to_dotenv("GWAIO_SERVER_ROOT")
            logger.info(f"SETTING SERVER ENVIRON {value}")
        else:
            raise ValueError(f"Value must be a instance of {Path} or {str}")

    @property
    def explorer_toolbar(self) -> ExplorerToolbar | None:
        return next(
            (t for t in self.app_toolbars if t.title == "Explorer Toolbar"), None
        )

    @property
    def toolbars(self):
        """Registered toolbars definitions."""
        return self._toolbars

    @property
    def app_toolbars(self) -> List[BaseToolbar]:
        """List[BaseToolbar]: Instantiated application toolbars."""
        return self._app_toolbars

    @property
    def apps(self):
        """Supported external applications."""
        return self._apps

    @property
    def tasks(self) -> List["BaseTask"]:
        """List[BaseTask]: Tasks managed by this plugin."""
        return self._tasks

    @tasks.setter
    def tasks(self, value: list[BaseTask]):
        if isinstance(value, list) and all(isinstance(t, BaseTask) for t in value):
            self._tasks = value
        else:
            raise ValueError(f"Value must be a {list} of {BaseTask}")

    @property
    def current_selected_tasks(self) -> List[BaseTask]:
        """
        Currently selected task objects in the UI.

        Returns:
            List[BaseTask]: The list of tasks the user has selected.
        """
        return self._current_selected_tasks

    @current_selected_tasks.setter
    def current_selected_tasks(self, value: list[BaseTask]):
        if isinstance(value, list) and all(isinstance(t, BaseTask) for t in value):
            self._current_selected_tasks = value
        else:
            raise ValueError(f"Value must be a {list} of {BaseTask}")

    @property
    def current_selected_files(self) -> List[Path]:
        """
        Currently selected file paths in the UI.

        Returns:
            List[Path]: The list of file Paths the user has selected.
        """
        return self._current_selected_files

    @current_selected_files.setter
    def current_selected_files(self, value: list[Path]):
        if isinstance(value, list) and all(isinstance(t, Path) for t in value):
            self._current_selected_files = value
        else:
            raise ValueError(f"Value must be a {list} of {Path}")

    @property
    def last_task_clicked(self) -> Optional[BaseTask]:
        """
        The most recent task the user clicked.

        Returns:
            Optional[BaseTask]: The last clicked task, or None if none selected.
        """
        return self._last_task_clicked

    @last_task_clicked.setter
    def last_task_clicked(self, value: BaseTask):
        self._current_selected_files = []
        self._last_task_clicked = value

    @property
    def last_file_clicked(self) -> Optional[Path]:
        """
        The most recent file the user clicked.

        Returns:
            Optional[Path]: Path of the last clicked file, or None.
        """
        return self._last_file_clicked

    @last_file_clicked.setter
    def last_file_clicked(self, file: str):
        if os.path.exists(file):
            self._last_file_clicked = file
        else:
            self._last_file_clicked = None

    @property
    def version_regex(self) -> str:
        """
        Regular expression used to identify version substrings in filenames.

        Returns:
            str: Current version‐matching regex pattern.
        """
        return self._version_regex

    @version_regex.setter
    def version_regex(self, value: str):
        if isinstance(value, str):
            self._version_regex = value
        else:
            raise ValueError(f"Value must be a instance of {str}")

    @property
    def version_includes_entity(self) -> bool:
        """
        Whether the version name must include the entity (e.g., shot or asset) string.

        Returns:
            bool: True if entity inclusion is enforced, False otherwise.
        """
        return self._version_includes_entity

    @version_includes_entity.setter
    def version_includes_entity(self, value: str):
        if isinstance(value, str):
            self._version_includes_entity = value
        else:
            raise ValueError(f"Value must be a instance of {str}")

    @property
    def headers(self) -> List[str]:
        """
        Column headers for displaying task data in the UI.

        Returns:
            List[str]: List of header strings in display order.
        """
        return self._headers

    def __del__(self) -> None:
        """This method should be called before unmounting this plugin.
        This method should be overriden to close up connections,
        like shotgun or maya instances."""
        pass

    def browse_task_data(self) -> None:
        """This method should be overriden according to each plugin.
        This opens the task in the plugin's database"""
        pass

    def browse_version_data(self) -> None:
        """This method should be overriden according to each plugin.
        This opens the version in the plugin's database"""
        pass

    def browse_note_data(self) -> None:
        """This method should be overriden according to each plugin.
        This opens the note in the plugin's database"""
        pass

    def get_all_tasks_data(
        self, return_object: dict, callback: Callable = None
    ) -> None:
        """This method should be overriden. It fills the return_object
        so that it can be accesed when threaded and runs a callback

        Args:
            return_object (Dict): A container that will be filled with
                the retrieved task data.
            callback (Callable, optional): A function to call once
                data retrieval is complete.
        """
        pass

    def validate_last_task_path(self, task: Optional[BaseTask] = None) -> Path:
        """
        Ensure the filesystem structure exists for the last-clicked task.

        If necessary, creates missing directories (including any
        subfolders defined in `task_subfolders`).

        Args:
            task (BaseTask, optional): Task to validate. Defaults to
                `self.last_task_clicked`.

        Returns:
            Path: The validated (and possibly newly created) task path.
        """
        task = task or self.last_task_clicked
        item_path = task.local_path
        if self.create_dir_if_missing(item_path, task):
            return item_path

    def get_task_filesystem(self) -> tuple[Path, Path]:
        """Utility function for returning the filesystem of a given task.
        Retrieve the local and server filesystem roots for the current task.

        Args:
            *args: Positional arguments for filesystem resolution.
            **kwargs: Keyword arguments for filesystem resolution.

        Returns:
            tuple[Path, Path]: (local_path, server_path) for the task.
        """
        return None, None

    def create_dir_if_missing(
        self, path: Path, task: Optional[BaseTask] = None
    ) -> bool:
        """
        Create a directory (and its defined subfolders) if it does not exist.

        Args:
            path (Path): The directory to ensure exists.
            task (BaseTask, optional): Task whose `task_subfolders` define
                extra subfolders to create. Defaults to `self.last_task_clicked`.

        Returns:
            bool: True if creation succeeded or already existed; False on error.
        """
        try:
            task = task or self.last_task_clicked
            path.mkdir(parents=True, exist_ok=True)
            for task, folders in self.task_subfolders.items():
                if task in [task.name, "all"]:
                    for folder in folders:
                        Path(path, folder).mkdir(parents=True, exist_ok=True)
            return True
        except:
            return False

    def return_next_version_name(self, ext: Iterable, task: BaseTask = None) -> dict:
        """This method must be overriden according to each plugin.
        it should return a dictionary like so:
        {
            "local_path": "path there the file goes",
            "file_name": "name without extension",
            "previous_file": "copy the previous version"
        }

        If there is no previous version, it should return a path where the
        templates are so that the user can choose a template form a QFileDialog.
        If the path is None, the QFileDialog will pop up in the root.

        Args:
            ext (Iterable[str]): Allowed file extensions.
            task (BaseTask, optional): Task context. Defaults to last clicked.

        Returns:
            Dict[str, Any]: Mapping with keys described above, or `None`
            if default logic is not applicable.
        """
        return None

    def check_version_is_published(self, version: Path) -> bool:
        """
        Determine whether a given version file has already been published.

        Args:
            version (Path): File path of the version to check.

        Returns:
            bool: True if published; False otherwise.
        """
        return False

    def publish_version(self, task: BaseTask, version: Path) -> dict:
        """Base method for creating the logic for publishing, the return
        object should be a dictionary with the following structure:

        Args:
            task (BaseTask): The task being published.
            version (Path): Path to the version file.

        Returns:
            Dict[str, Any]: A result dict with:
                {
                    "success": bool,
                    "message": str,
                    "error": Optional[str]
                }
        """
        return {
            "success": False,
            "message": "This plugin does not support publishing yet.",
            "error": None,
        }

    def filter_local_files(
        self,
        local_path: Path,
        ext: str | Iterable[str] = [""],
        task: Optional[BaseTask] = None,
    ) -> list[Path]:
        """
        Given a path, it will return the files
        that follow the stablished conventions

        Args:
            local_path (Path): The directory to search in.
            ext (Union[str, Iterable[str]]): Valid file extensions to include.
            task (BaseTask, optional): Task context to validate conventions. Defaults to last clicked task.

        Returns:
            list[Path]: List of files matching conventions and extensions.
        """

        task = task or self.last_task_clicked
        ext = [ext] if isinstance(ext, str) else ext
        try:
            logger.debug(f"Filter files -> {local_path}")
            filtered_files = list()
            for f in local_path.rglob("*.*"):
                logger.debug(f"Checking: {f}")
                if not self.file_has_convention(f, task):
                    logger.debug(f"Not has convention: {f}")
                    continue
                if not any(f.suffix.endswith(e) for e in ext):
                    logger.debug(f"Not suffix: {f}")
                    continue
                logger.debug(f"Found: {f}")
                filtered_files.append(f)
            return filtered_files
        except:
            # this is because apparently there is a chance where the rglob raises a
            # WinError3 (system cannot find the path specified)
            return []

    def file_has_convention(self, file: Path, task: Optional[BaseTask] = None) -> bool:
        """
        Check if a file meets entity and naming regex conventions.

        Args:
            file (Path): File to validate.
            task (Optional[BaseTask], optional): Task context. Defaults to last clicked.

        Returns:
            bool: True if file meets convention; otherwise False.
        """
        task = task or self.last_task_clicked
        return all(
            [
                self.file_has_entity(file, task),
                any(match(r, file.name) for r in self.naming_regex),
            ]
        )

    def file_has_entity(self, file: Path, task: Optional[BaseTask] = None) -> bool:
        """
        Check if the task entity is included in the file name (if required).

        Args:
            file (Path): File to check.
            task (Optional[BaseTask], optional): Task context. Defaults to last clicked.

        Returns:
            bool: True if the entity name is found or not required.
        """
        task = task or self.last_task_clicked
        return (
            True
            if not self.version_includes_entity
            else task.link_name in fspath(file.name)
        )

    def return_last_version_number(self, path: Path) -> int:
        """
        Looks at all the files in 'path' and returns as int the highest version
        number that matches the version_regex.

        Args:
            path (Path): Directory to search for versioned files.

        Returns:
            int: The maximum version number found. Returns 0 if none.
        """
        v = 0
        for f in self.filter_local_files(path):
            try:
                version_str = return_version_number_from_string(
                    self.version_regex, f.name
                )
                if int(version_str) > v:
                    v = int(version_str)
            except Exception as e:
                pass
        return v

    def return_last_version_file(
        self, path: Path, ext: Iterable[str]
    ) -> Optional[Path]:
        """
        Looks at all the files with a given extension in 'path' and returns as
        Path the file that has the highest version number that matches the version_regex.

        Args:
            path (Path): Directory to search.
            ext (Iterable[str]): File extensions to match.

        Returns:
            Optional[Path]: Path to highest-versioned file, or None.
        """
        v, last_file = 0, None
        logger.debug(f"Filtering possible candidates. -> {path} -> {ext}")
        for f in self.filter_local_files(path, ext):
            logger.debug(f"return_last_version_file: FILE FOUND: {f}")
            try:
                logger.debug(f"Evaluating {f} as a candidate.")
                version_str = search(self.version_regex, f.name).group()
                version_str = sub("[^0-9]", "", version_str)
                if int(version_str) >= v:
                    v, last_file = int(version_str), f
            except:
                pass

        # If there are files without versioning regex, get them by date
        if last_file is None:
            try:
                last_file = max(self.filter_local_files(path, ext), key=getmtime)
            except:
                pass
        logger.debug(f"Candidate found @ {last_file}")
        return last_file

    def return_last_file(
        self,
        ext: Iterable[str],
        subdir: Path = Path(),
        template_failed: bool = True,
        task: Optional[BaseTask] = None,
    ) -> tuple[int, Path]:
        """
        Returns a tuple with the both the version and the
        last file of a given task. Defaults to the task's localpath, but
        can receive a path (generaly a subpath of the local path).

        Args:
            ext (Iterable[str]): Valid file extensions.
            subdir (Path, optional): Subdirectory to look inside. Defaults to Path().
            template_failed (bool, optional): If True and no file is found, try template. Defaults to True.
            task (Optional[BaseTask], optional): Task context. Defaults to last clicked.

        Returns:
            tuple[int, Path]: Tuple of version number and file path.
        """
        task = task or self.last_task_clicked
        local_path = Path(task.local_path, subdir)
        prev_path = Path(task.prev_task_server, subdir)
        logger.debug(f"Looking for previous task for {local_path} and {prev_path}.")
        for i, task_path in enumerate([local_path, prev_path]):
            if i == 1 and prev_path.is_file():  # if prev_path is a file, use it
                return 0, task_path
            if task_path == Path():  # if task_path is empty path, ignore
                continue

            # last file from current path
            last_file = self.return_last_version_file(task_path, ext)

            # if task_path is local_path, find the highest version
            if i == 0:
                v = self.return_last_version_number(task_path)

            if last_file is not None:
                break

        if last_file is None and template_failed:
            last_file = self._dict_file_templates.get(ext[0])

        return v, last_file

    @classmethod
    def verify_bdl_excel(cls, excel: Path) -> tuple[bool, str]:
        """
        Validate the naming convention of a BDL Excel file.

        Args:
            excel (Path): The Excel file to verify.

        Returns:
            tuple[bool, str]: True and code string if valid; False and reason otherwise.
        """
        if cls.bdlregex is None:
            return False, "Method not implemented for this plugin."
        if not match(cls.bdlregex, excel.name):
            return False, "The BDL file doesn't have the right naming convention."
        return True, sub("[^0-9]", "", excel.name)

    def read_excel(self, excel: Path) -> tuple[list[Any], dict[Any, Any]]:
        """Base method for creating the logic for read and return contents of an Excel file.

        Args:
            excel (Path): Path to the Excel file.

        Returns:
            tuple[list[Any], dict[str, Any]]: A list of rows and a dictionary of parsed data.
        """

        return [], dict()

    def return_seq_and_shot_from_clipname(self, clip_name: str) -> Any:
        """
        This method is called when a EDL is parsed for an entire episode,
        where the info about which sequence and shot lives in the name of
        the clip name, for a edl file.
        This method is called when self._episode_edl_workflow is True.

        Args:
            clip_name (str): The clip name from which to extract episode data.

        Returns:
            None: Override expected to return values.
        """
        return

    def parse_edl_file(
        self, source_edl: Path, source_video: Path
    ) -> Iterator[dict[Any, Any]]:
        """
        Parse an EDL file to extract shot data.

        Args:
            source_edl (Path): Path to the EDL file.
            source_video (Path): Path to the reference video.

        Yields:
            dict[Any, Any]: A dictionary representing each shot.

        Raises:
            NotImplementedError: Must be implemented in subclass.
        """
        raise NotImplementedError("This method needs to be implemented.")

    def create_shot(self, shot_data: dict[str, Any]) -> None:
        """
        Create a shot using parsed shot data.

        Args:
            shot_data (dict[str, Any]): Dictionary of shot attributes.

        Raises:
            NotImplementedError: Must be implemented in subclass.
        """
        raise NotImplementedError("This method needs to be implemented.")

    def create_assets_from_bdl(
        self, dict_with_items: dict[str, Any], excel_file: Path
    ) -> None:
        """
        Receives an standarized dictionary that holds the data for creating assets.
        It yields assets that were successfully created.

        Args:
            dict_with_items (dict[str, Any]): Structured asset data.
            excel_file (Path): Path to original Excel file.
        """
        return

    def parse_clip_name(self, clip_name: str) -> Any:
        """
        From a clip name in a XML or in a EDL file, it returns
        the number of the episode, sequence and shot

        Args:
            clip_name (str): The input clip name.

        Returns:
            Any: Expected to return episode, sequence, and shot identifiers.

        Raises:
            NotImplementedError: Must be implemented in subclass.
        """
        raise NotImplementedError("This needs to be implemented.")

    def return_file_by_ext(self, file: Path, ext: str) -> Path:
        """
        Return a file that matches the given extension and version pattern.

        Args:
            file (Path): Input file path.
            ext (str): Target extension to match.

        Returns:
            Path: Matching file or fallback template path.
        """
        version_file_str = None
        version_file_search = search(self.version_regex, file.stem)
        if version_file_search != None:
            version_file_str = version_file_search.group()

        list_files = self.filter_local_files(file.parent, ext)
        for f in list_files:
            if any(v in fspath(f) for v in [fspath(file.stem), version_file_str] if v):
                return f
        return file.parent if list_files else Path(self.TEMPLATES_FOLDER)

    # def return_task_notes(self, task: BaseTask, force_stop: lambda: bool) -> list:
    def return_task_notes(
        self, task: BaseTask, force_stop: Callable[[], bool]
    ) -> list[dict[str, Any]]:
        """Base method to create the note listing logic of a task,
        the returned object must be a list with the following structure:

        [{
            "content" : str,
            "created_by" : str or None,
            "created_at" : str or None,
            "attachments" : list[dict["url_open":str,"url_image":str,"bytes":str,"path":str],]
            "url" : str
        }]

        Args:
            task (BaseTask): The task to retrieve notes for.
            force_stop (Callable[[], bool]): Callback to interrupt processing.

        Returns:
            list[dict[str, Any]]: A list of note dictionaries.
        """
        return []

    def return_task_versions(self, task: BaseTask) -> list[dict[str, Any]]:
        """Base method to create the version listing logic of a task,
        the returned object must be a list with the following structure:

        [{
            "content" : str,
            "created_by" : str  or None,
            "created_at" : str or None,
            "attachments" : dict["url","bytes" or "url"],
            "url" : str
            "reply" : list[dict]
        }]

        Args:
            task (BaseTask): The task to retrieve versions for.

        Returns:
            list[dict[str, Any]]: A list of version dictionaries.
        """
        return []

    # def return_entity_description(
    #     self, task: BaseTask, force_stop: lambda: bool
    # ) -> str:
    def return_entity_description(
        self, task: BaseTask, force_stop: Callable[[], bool]
    ) -> Optional[str]:
        """
        Return a string description of the entity (e.g., asset or shot).

        Args:
            task (BaseTask): The task associated with the entity.
            force_stop (Callable[[], bool]): Callback to interrupt processing.

        Returns:
            Optional[str]: The entity description, if any.
        """
        return None

    def return_thumbnail_url(self) -> Optional[str]:
        """
        This method should be overriden according to each plugin.
        This refresh the url thumbnail in the plugin's database

        Returns:
            Optional[str]: URL string if available.
        """
        return None

    @classmethod
    def create_thumbnail(cls, task: BaseTask) -> bool:
        """
        This method may be overriden and it is called when the thumbnail
        for a task cannot be synced because it is not in the server yet.
        Returns True on success

        Args:
            task (BaseTask): Task for which to create the thumbnail.

        Returns:
            bool: True if creation and resizing succeeded, False otherwise.
        """

        file_path = fspath(task.thumbnail)
        while True:
            # Generate thumbnail from last file
            try:
                dir = task.local_path
                file_path = max(
                    [*dir.glob(f"*.jpg"), *dir.glob(f"*/*.jpg")], key=os.path.getmtime
                )
                if task.thumbnail.exists():
                    remove(fspath(task.thumbnail))
                copy2(file_path, task.thumbnail)
                break
            except Exception as e:
                pass

            # If there are any other methods to retrieve a thumbnail
            # they can be set here, before returning False

            return False

        return cls.resize_thumbnail_image(task.thumbnail)

    def return_maya_outliner_asset_base_nodes(
        self, *args, **kwargs
    ) -> Optional[list[str]]:
        """
        The plugin must send to maya all the parameters so that maya doesn't have
        to query any database to get the required values.
        All not-default nodes must be under one of these nodes.

        Args:
            *args (Any): Positional arguments.
            **kwargs (Any): Keyword arguments, expects 'link_name' to identify asset group.

        Returns:
            Optional[list[str]]: List of node strings to be used as parents in Maya's outliner.

        """
        if (link_name := kwargs.get("link_name")) is not None:
            return [
                # f"|{link_name}_grp",
                f"|{link_name}_grp|rig_grp",
                f"|{link_name}_grp|model_grp",
            ]

    def on_item_doubleclicked_callback(self) -> None:
        """
        Placeholder for handling item double-click behavior in a GUI context.

        Intended to be overridden by subclasses or externally bound.
        """
        ...

    def return_maya_outliner_shot_base_nodes(self, *args, **kwargs) -> list[str]:
        """
        The plugin must send to maya all the parameters so that maya doesn't have
        to query any database to get the required values.

        Args:
            *args (Any): Positional arguments.
            **kwargs (Any): Keyword arguments.

        Returns:
            list[str]: Top-level node names used in Maya for organizing shots.

        """
        return [
            "|ASSETS",
            "|ASSETS|CH",
            "|ASSETS|PR",
            "|ASSETS|EN",
            "|ASSETS|FX",
            "|CAMS",
            "|LIGHTS",
            "|MISC",
        ]

    def receive_config_data_from_app(self, *args, **kwargs) -> None:
        """
        Because the user data may be passed on to the plugin on initialization,
        we have this function that will handle in a per plugin basis the logic.

        Args:
            *args (Any): Positional arguments.
            **kwargs (Any): Configuration data passed by the app.
        """
        ...

    @staticmethod
    def resize_thumbnail_image(file_path: str):
        return False

    def return_filepack_exceptions(self) -> list[str]:
        """
        This is a function used by the asset packager so that
        each plugin can define how to return an exception of files to be packed.

        Returns:
            list[str]: A list of exception file names or patterns.

        """
        return []

    def return_base_task_with_kwargs(self, **kwargs) -> Optional[BaseTask]:
        """
        Returns a task from current plugin if using kwargs as filters.

        Args:
            **kwargs (Any): Attribute-value pairs to match against BaseTask attributes.

        Returns:
            Optional[BaseTask]: Matching task or None.

        """
        for task in self.tasks:
            if all(getattr(task, k) == v for k, v in kwargs.items()):
                return task

    def return_base_task_with_path(self, local_path: Path) -> Optional[BaseTask]:
        """
        Returns a task from current plugin if using local_path as filters.

        Args:
            local_path (Path): Path to match against task local paths.

        Returns:
            Optional[BaseTask]: The matching BaseTask, if any.
        """
        for part in enumerate(local_path.parts):
            for task in self._tasks:
                task_path = task.local_path
                if task_path == local_path:
                    return task
            local_path = Path(
                *local_path.parts[:-1],
            )

    def file_added_callback(self) -> None:
        """
        This callback is added in case there is some further functionality to
        add in a per plugin level. Originally requested for a change in the DB
        in the Grisu plugin. File added -> task updated to IP.
        """
        return

    def generate_environment_for_app(
        self, task: Optional[BaseTask] = None
    ) -> dict[str, str]:
        """
        Generate environment variables needed to launch an external application.

        Args:
            task (Optional[BaseTask], optional): Task context to embed into environment. Defaults to None.

        Returns:
            dict[str, str]: Dictionary of environment variables.
        """
        task = task or self.last_task_clicked
        exe_env = {
            # TODO: test whether we can remove this, as the get_env method from the
            # env_handler already returns a stripped path
            # "GWAIO_LOCAL_ROOT": sub(r"(\/|\\)$", "", fspath(self.local_root)).strip(),
            # "GWAIO_SERVER_ROOT": sub(
            #     r"(\/|\\)$", "", fspath(self.server_root)
            # ).strip(),
            "GWAIO_APP_PATH": fspath(Path(Path(__file__).parent.parent.parent)),
            "GWAIO_PROJECT_NAME": self.TITLE,
            "GWAIO_VERSION_REGEX": self.version_regex,
            "GWAIO_USERNAME": self.username or "",
            "GWAIO_MAYA_PLAYBLAST_TEMPLATE": fspath(self.TEMPLATES_FOLDER)
            + "/maya/turntable_playblast_rig_master.ma",
            "GWAIO_MAYA_LIGHT_TEMPLATE": fspath(self.GWAIO_MAYA_LIGHT_TEMPLATE),
            "GWAIO_ASSET_FOLDER": self._asset_folder or "",
            "GWAIO_ASSET_FOLDER_REGEX": self._asset_folder_regex or "",
            # "GWAIO_SL_SERVER_PATH": fspath(self.SL_SERVER_PATH) or "",
            "GWAIO_SL_SERVER_PATH": (
                sub(r"(\/|\\)$", "", fspath(self.SL_SERVER_PATH) or "")
                if self.SL_SERVER_PATH
                else ""
            ),
            "GWAIO_SL_LOCAL_PATH": (
                fspath(
                    replace_root_in_path(
                        self.server_root,
                        self.local_root,
                        self.SL_SERVER_PATH,
                    )
                )
                if self.SL_SERVER_PATH
                else ""
            ),
            "GWAIO_FPS": str(self._fps),
            "GWAIO_PLAYBLAST_RESOLUTION": self._playblast_res or "1920x1080",
            "GWAIO_DEADLINE_REPO_PATH": self.GWAIO_DEADLINE_REPO_PATH,
        }

        if task:
            exe_env.update(
                {
                    "GWAIO_TASK": task.name,
                    "GWAIO_TASK_DATA": json.dumps(task.serialize()),
                    "GWAIO_NAMING_HEAD": return_file_name_head(
                        self.version_regex,
                        # the extensions below are spp and ma because these are the file types
                        # that are currently using this environment variable
                        Path(
                            self.return_next_version_name([".spp", ".ma"]).get(
                                "file_name"
                            )
                        ),
                    ),
                    "GWAIO_OUTLINER_ASSET_NODES": pathsep.join(
                        self.return_maya_outliner_asset_base_nodes(
                            link_name=task.link_name
                        )
                    ),
                    "GWAIO_EPISODE": task.episode or task.episodes or "",
                    "GWAIO_OUTLINER_SHOT_NODES": pathsep.join(
                        self.return_maya_outliner_shot_base_nodes(
                            link_name=task.link_name
                        )
                    ),
                    "GWAIO_TASK_PREVIEW_PATH": fspath(
                        task.local_path / self._preview_location
                    ),
                    "GWAIO_TASK_TEXTURES_PATH": fspath(
                        task.local_path / self._textures_location
                    ),
                    "GWAIO_TASK_EXPORT_PATH": fspath(
                        task.local_path / self._export_location
                    ),
                    "GWAIO_TASK_PATH": fspath(task.local_path),
                    "MAYA_PROJECT": fspath(task.local_path),  # internal maya var
                    "GWAIO_TASK_LINKED_ASSETS": task.assets,
                    "GWAIO_QA_CONFIG": os.pathsep.join(
                        self._qa_config.get(task.name, [])
                        + self._qa_config.get("all_tasks", [])
                    ),
                    "GWAIO_START_FRAME": str(self._starting_frame or ""),
                    "GWAIO_END_FRAME": (
                        str(self._starting_frame + task.cut_duration - 1)
                        if all(
                            [
                                f is not None
                                for f in [
                                    self._starting_frame,
                                    task.cut_duration,
                                ]
                            ]
                        )
                        else ""
                    ),
                    "GWAIO_START_FRAME_ANIMATIC": str(task.cut_in or ""),
                }
            )

        if self.OCIO_FILE is not None:
            exe_env["OCIO"] = fspath(
                Path(
                    self.env_handler.get_env("GWAIO_LOCAL_ROOT"),
                    *self.OCIO_FILE.parts[
                        len(Path(self.env_handler.get_env("GWAIO_SERVER_ROOT")).parts) :
                    ],
                )
            )

        if self.CUSTOM_HOUDINI_TOOLS is not None:
            custom_houdini_tools = Path(
                self.env_handler.get_env("GWAIO_LOCAL_ROOT"),
                *self.CUSTOM_HOUDINI_TOOLS.parts[
                    len(Path(self.env_handler.get_env("GWAIO_SERVER_ROOT")).parts) :
                ],
            )
            exe_env["HOUDINI_PATH"] = f"{custom_houdini_tools};&"

        if self.CUSTOM_NUKE_TOOLS is not None:
            custom_nuke_tools = Path(
                self.env_handler.get_env("GWAIO_LOCAL_ROOT"),
                *self.CUSTOM_NUKE_TOOLS.parts[
                    len(Path(self.env_handler.get_env("GWAIO_SERVER_ROOT")).parts) :
                ],
            )
            subdirectories = list()
            if custom_nuke_tools.exists():
                subdirectories = [
                    fspath(p) for p in custom_nuke_tools.iterdir() if p.is_dir()
                ]
            if environ.get("NUKE_PATH"):
                subdirectories.append(environ.get("NUKE_PATH"))
            exe_env["NUKE_PATH"] = (
                fspath(custom_nuke_tools) + ";" + ";".join(subdirectories)
            )  # f"{custom_nuke_tools}"

        if self.CUSTOM_MAYA_TOOLS is not None:
            custom_maya_tools = Path(
                self.env_handler.get_env("GWAIO_LOCAL_ROOT"),
                *self.CUSTOM_MAYA_TOOLS.parts[
                    len(Path(self.env_handler.get_env("GWAIO_SERVER_ROOT")).parts) :
                ],
            )
            exe_env["MAYA_MODULE_PATH"] = fspath(custom_maya_tools / "modules")
            exe_env["MAYA_PLUG_IN_PATH"] = fspath(custom_maya_tools / "plug-ins")
            exe_env["PYTHONPATH"] = fspath(custom_maya_tools / "scripts")
        else:
            exe_env["PYTHONPATH"] = ""
        return exe_env

    def guess_executable_for_file(self, path: str | Path) -> Optional[str]:
        """
        Guess which executable should be used to open a file based on its extension.

        Args:
            path (str | Path): Path to the file to analyze.

        Returns:
            Optional[str]: Path to the executable, or None if no match found.
        """
        if Path(path).suffix in [".ma", ".mb"]:
            logger.debug("Getting variable MAYA_BIN")
            executable = self.env_handler.get_env("MAYA_BIN")
            # sync_dock: "SyncDock" = self.parent().parent().parent().sync_dock
            # deps = get_dependencies(path)
            # print(list(deps))
            logger.debug(f"Executable found at {executable}")
            # return False
        elif Path(path).suffix in [".spp"]:
            executable = self.env_handler.get_env("PAINTER_BIN")
        elif Path(path).suffix in [".hip"]:
            executable = self.env_handler.get_env("HOUDINI_BIN")
        elif Path(path).suffix in [".nk"]:
            executable = self.env_handler.get_env("NUKE_BIN")
        # elif Path(path).suffix in [".fbx", ".obj"]:
        #     choice, exe_ok = QInputDialog.getItem(
        #         self.parent(),
        #         "Select software",
        #         "Please select which software would you like to use:",
        #         ["Substance Painter", "Autodesk Maya"],
        #         current=0,
        #         editable=False,
        #     )
        #     if exe_ok:
        #         executable = self.env_handler.get_env(
        #             executable_mappings[choice]
        #         )
        else:
            executable = None
        return executable

    def open_app_with_env(
        self, executable: Optional[str] = None, environ: Optional[str] = None
    ) -> None:
        """
        Launch an application with generated environment variables.

        Args:
            executable (Optional[str]): Executable path. Overridden by environ if provided.
            environ (Optional[str]): Environment variable key to retrieve executable from.
        """
        self.extract_plugin_values()
        last_task_clicked = self.last_task_clicked
        self.last_task_clicked = None
        exe_env = self.generate_environment_for_app()
        if environ:
            executable = self.env_handler.get_env(environ)
        logger.debug(f"Opening app {executable}")
        open_app(executable, exe_env=exe_env)
        self.last_task_clicked = last_task_clicked

    def open_file_with_env(self, path: str | Path, executable: str) -> None:
        """
        Open a file with a specified executable and plugin-defined environment.

        Args:
            path (str | Path): File path to open.
            executable (str): Path to the application executable.
        """
        logger.debug(f"Opening file {path}")
        self.extract_plugin_values()
        exe_env = self.generate_environment_for_app()
        open_file(path, self, executable, exe_env=exe_env)

    def copy_edl_files_to_server(self, shot_data: dict[str, Any]) -> None:
        """
        Copy EDL-associated video and audio files to the server location.

        Args:
            shot_data (dict[str, Any]): Dictionary containing keys 'video_file' and 'server_path'.
        """
        print(shot_data)
        video_file = Path(shot_data.get("video_file"))
        server_path = Path(shot_data.get("server_path"))
        server_file = Path(server_path, video_file.name)
        server_path.mkdir(exist_ok=True, parents=True)
        for suffix in (video_file.suffix, ".wav"):
            source = video_file.with_suffix(suffix)
            target = server_file.with_suffix(suffix)
            try:
                if target.exists():
                    os.remove(target)
                copy2(source, target)
            except Exception as e:
                logger.warning(e)
                logger.debug(f"Failed to copy file {source} to the {target}")

    def after_publish(*args, **kwargs) -> None:
        """
        Hook called after publishing process completes.

        Args:
            *args (Any): Positional arguments.
            **kwargs (Any): Keyword arguments.
        """
        ...

    def start_task(self) -> None:
        """
        Hook for starting a task. To be overridden as needed.
        """
        ...

    def extract_plugin_values(self) -> None:
        """
        Serialize plugin state and write it to a JSON file for debugging or inspection.
        """
        try:
            import time

            s = time.perf_counter()

            def convert(value):
                if isinstance(value, (str, int, float, bool, type(None))):
                    return value
                elif isinstance(value, Path):
                    return str(value)
                # elif isinstance(value, BaseTask):
                #     return {k: convert(v) for k, v in value.serialize().items()}
                elif isinstance(value, (list, tuple)):
                    return [convert(v) for v in value]
                elif isinstance(value, dict):
                    return {k: convert(v) for k, v in value.items()}
                else:
                    return

            result = {k: convert(v) for k, v in vars(self).items()}
            with open(
                Path(environ["GWAIO_DATA_PATH"], f"plugin_data.json"), "w"
            ) as json_file:
                json.dump(result, json_file, indent=4)
            print(">>>>>>", s - time.perf_counter())
        except Exception as error:
            logger.error(error)

    def get_plugin_info(self) -> dict[str, list[str]]:
        """
        Return a dictionary with lists of method names and variable names.

        Returns:
            dict[str, list[str]]: Dictionary with 'methods' and 'variables' as keys.
        """
        methods = [
            func
            for func in dir(self)
            if callable(getattr(self, func)) and not func.startswith("__")
        ]
        variables = [
            var
            for var in vars(self)
            if not callable(getattr(self, var)) and not var.startswith("__")
        ]
        return {"methods": methods, "variables": variables}


if __name__ == "__main__":
    from logging import DEBUG, basicConfig

    from PySide6.QtWidgets import QApplication

    basicConfig(level=DEBUG)
    logger = getLogger()

    app = QApplication()
    plugin = BasePlugin()
