import asyncio
from functools import partial
import logging
from pprint import pprint
from tempfile import TemporaryDirectory
from typing import Any, Callable, Generator, Optional, Union, Iterator
from os import fspath, remove
import os.path
from pathlib import Path
import json
from time import mktime
from datetime import datetime
from shutil import copy2
import webbrowser as web

import shotgun_api3 as sg3
from shotgun_api3.shotgun import Shotgun

from utilities.pipe_utils import (
    create_package,
    execute_mayapy,
    extract_package,
    return_version_number_from_string,
)
from task_schema.plugins.base_plugin import BasePlugin, BaseTask, BaseThumbnail
from launcher.qtclasses.toolbar_shotgrid import ShotgridToolbar
from launcher import metadata
from mondo_scripts.editorial import read_xml

logger = logging.getLogger(__name__)


class ShotgridInstance:
    """
    Context manager for handling a Shotgun API session.

    This helper class is designed to manage the lifecycle of a Shotgun API
    instance within a with-statement. It ensures the connection is properly
    closed after use.
    """
    def __init__(self, plugin: "ShotgridPlugin") -> None:
        """
        Context manager for Shotgun API instance lifecycle.

        Args:
            plugin (ShotgridPlugin): Instance of the Shotgrid plugin.
        """
        self.plugin = plugin

    def __enter__(self) -> Shotgun:
        """
        Instantiate and return a Shotgun API instance.

        Returns:
            Shotgun: Shotgun API instance.
        """
        self.instance = self.plugin._instantiate_shogrid()
        return self.instance

    def __exit__(self, exc_type: Optional[type], exc_value: Optional[BaseException], exc_tb: Optional[object]) -> None:
        """
        Clean up the Shotgun API instance.
        """
        self.instance.close()


class ShotgridPlugin(BasePlugin):
    """
    Plugin for integration with Autodesk ShotGrid.

    This plugin extends the BasePlugin to support task and version management
    through ShotGrid. It handles querying tasks, uploading packages, retrieving
    notes and versions, managing custom artist entities, and other production
    tracking features within the launcher environment.

    Class Attributes:
        TITLE (str): Plugin title identifier.
        _server_root (Path): Root path to the project's server-side filesystem.
        SHOTGRID_URL (str): URL endpoint for the ShotGrid instance.
        SHOTGRID_SCRIPT_NAME (str): Script name used for authenticating with ShotGrid API.
        SHOTGRID_API_KEY (str): Script-based API key for ShotGrid access.
        SG_PROJECT_ID (int): ShotGrid project ID used for scoping queries.
        SL_SERVER_PATH (Optional[Path]): Optional path used for logging or data sharing.
        title (str): Human-readable title for the plugin.
        custom_artist_entities (List[str]): List of custom entity fields used to resolve assignees.
        _active_entities (List[str]): Entity types used by the plugin (e.g. Shot, Asset).
        plugin_task_fields (List[str]): Default fields requested from each task.
        _discarted_task_status (List[str]): List of task statuses to ignore.
        _discarted_version_status (List[str]): List of version statuses to ignore.
        asset_task_fields_dict (Optional[Dict]): Optional dictionary for customizing task fields.

    Instance Attributes:
        sg (Shotgun): ShotGrid API instance.
        _toolbars (List): List of toolbars registered by this plugin.
        _headers (List[str]): Column headers for task display.
        plugin_task_filters (List[List]): Filters applied to task queries.
        timelog_artist_entity_field (Optional[str]): Field used to assign timelogs to artists.
        publishedfile_artist_entity_field (Optional[str]): Field used to resolve artist from PublishedFiles.
        version_artist_entity_field (Optional[str]): Field used to assign versions to artists.
        custom_artist_login_field (Optional[str]): Field used to match the current username to artist.
        custom_artist_entity_name (Optional[str]): Name of the custom artist entity in ShotGrid.
        custom_artist_task_field (Optional[str]): Custom field linking tasks and artists.
        _starting_frame (int): Default starting frame for playblasts or versioning.
        _task_long_to_short_dict (Dict[str, str]): Mapping of long task names to short aliases.
        _upload_status (str): Default status to assign when uploading a version.
        _version_publish_fields (List[str]): Fields to include when publishing a version.
        _color_status (Dict[str, Tuple[int, int, int]]): Mapping of ShotGrid status codes to RGB colors.
    """
    TITLE = "Shotgrid"
    _server_root = Path("\\\\qsrv01.mondotvcanarias.lan\\data0\\PROJECTS\\GRISU")
    SHOTGRID_URL = "https://mondotv.shotgunstudio.com"
    SHOTGRID_SCRIPT_NAME = "ShotgunHandlerBase"
    SHOTGRID_API_KEY = "#ebhfcJlejfxjinlvorxmwja9"
    SG_PROJECT_ID = 122
    SL_SERVER_PATH = None

    title = "Shotgrid Plugin"
    # custom_artist_entity = "sg_mondo_artist.CustomEntity04.code"
    custom_artist_entities = ["sg_mondo_artist.CustomEntity04.code"]
    _active_entities = ["My Tasks", "Asset", "Episode", "Shot"]
    plugin_task_fields = [
        "sg_status_list",
        "step.Step.entity_type",
        "step.Step.code",
        "content",
        "image",
        "task_assignees",
    ]
    _discarted_task_status: list[str] = ["na"]
    _discarted_version_status: list[str] = ["na", "dct"]
    asset_task_fields_dict: dict[dict, dict[str, str]] = None

    def __new__(cls: "ShotgridPlugin", *args, **kwargs) -> "ShotgridPlugin":
        # cls.plugin_task_fields.append(cls.custom_artist_entity)
        cls.plugin_task_fields += cls.custom_artist_entities
        return super().__new__(cls)

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the ShotgridPlugin instance.

        Initializes toolbars, sets up task filters, ShotGrid connection,
        headers, version fields and task mappings.
        """
        super().__init__(*args, **kwargs)
        self._toolbars += [[ShotgridToolbar, "Shotgrid Toolbar"]]
        # self._toolbars += [ShotgridToolbar("Shotgrid Toolbar", self)]

        self._headers = [
            "link",
            "task",
            "task status",
            "artist",
            "asset type",
            "tags",
            "created_for_episode",
            "episodes",
            "cut_in",
            "cut_out",
            "cut_duration",
            "sequence",
            "episode",
        ]

        self.plugin_task_filters = [
            ["sg_status_list", "not_in", ["na", "wtg"]],
            ["project.Project.id", "is", int(self.SG_PROJECT_ID)],
        ]

        self.timelog_artist_entity_field = None
        self.publishedfile_artist_entity_field = None
        self.version_artist_entity_field = None
        self.custom_artist_login_field = None
        self.custom_artist_entity_name = None
        self.custom_artist_task_field = None
        self._starting_frame = 1

        self.sg = self._instantiate_shogrid()
        self._task_long_to_short_dict: dict[str, str] = dict()
        self._set_task_long_to_short_dict()
        self._set_color_status()
        self._upload_status = "rev"
        self._version_publish_fields = [
            "project",
            "code",
            "description",
            "sg_task",
            "entity",
        ]

    def __del__(self) -> None:
        self.sg.close()

    @property
    def task_long_to_short_dict(self) -> dict[str, str]:
        """
        Returns the mapping of long task names to their short aliases.

        Returns:
            dict[str, str]: Dictionary of task name mappings.
        """
        return self._task_long_to_short_dict

    @property
    def active_entities(self) -> list[str]:
        """
        Returns the list of active entity types the plugin supports.

        Returns:
            list[str]: List of supported entity types.
        """
        return self._active_entities

    def async_find(
        self,
        entity: str,
        filters: list[list[Any]] = [],
        fields: list[str] = [],
        page_size: int = 500,
    ) -> list[dict[str, Any]]:
        """
        Performs asynchronous paged queries on the ShotGrid API.

        Args:
            entity (str): Entity type to query (e.g., 'Task').
            filters (list[list[Any]]): ShotGrid filter list.
            fields (list[str]): Fields to retrieve.
            page_size (int): Number of results per page.

        Returns:
            list[dict[str, Any]]: Flattened list of all retrieved results.
        """
        sg = self._instantiate_shogrid()
        total_tasks = sg.summarize(
            entity, filters, summary_fields=[{"field": "id", "type": "count"}]
        )["summaries"]["id"]
        total_pages = -(-total_tasks // page_size)
        loop = asyncio.new_event_loop()

        async def run_task(page):
            return await loop.run_in_executor(
                None,
                lambda: self._instantiate_shogrid().find(
                    entity, filters, fields, page=page, limit=page_size
                ),
            )

        async def gather_task():
            return await asyncio.gather(
                *[run_task(page) for page in range(1, total_pages + 1)]
            )

        result = loop.run_until_complete(gather_task())
        loop.close()
        return [item for group in result for item in group]

    def _set_color_status(self) -> None:
        """
        Initializes the internal `_color_status` dictionary mapping status codes to RGB color tuples.
        """
        raw_data_status = self.sg.find(
            "Status",
            filters=[
                # ["sg_used_in", "is", {"type": "Project", "id": self.SG_PROJECT_ID}]
            ],
            fields=["code", "bg_color"],
        )
        self._color_status = dict()
        for item in raw_data_status:
            if item["bg_color"] is None:
                item["bg_color"] = "255,255,255"
            self._color_status[item["code"]] = [
                int(col) for col in item["bg_color"].split(",")
            ]

    def _set_task_long_to_short_dict(self) -> None:
        """
        Populates `_task_long_to_short` with mappings for task and step names from ShotGrid's TaskTemplates and Steps.
        """
        # project = self.sg.find("Project",[["id","is",int(self.SG_PROJECT_ID)]])
        raw_data_task = self.sg.find(
            "Task",
            filters=[
                ["task_template", "is_not", None],
                # ["task_template.TaskTemplate.code", "contains", self.TITLE],
                [
                    "task_template.TaskTemplate.projects",
                    "in",
                    {"type": "Project", "id": self.SG_PROJECT_ID},
                ],
            ],
            fields=["content", "sg_short_name"],
        )

        raw_data_step = self.sg.find("Step", filters=[], fields=["code", "short_name"])

        self._task_long_to_short = {
            **{t["content"]: t["sg_short_name"] for t in raw_data_task},
            **{s["code"]: s["short_name"] for s in raw_data_step},
        }

    def task_long_to_short(self, task_name: str) -> str:
        """
        Returns the short alias for a given long task name.

        Args:
            task_name (str): Full name of the task.

        Returns:
            str: Shortened task name.

        Raises:
            Exception: If task name is not found in the dictionary.
        """
        try:
            return self._task_long_to_short[task_name]
        except:
            raise Exception(f"Task '{task_name}' not found in Task templates")

    @classmethod
    def _instantiate_shogrid(cls) -> Shotgun:
        """
        Instantiates and returns a Shotgun API session using class-level credentials.

        Returns:
            Shotgun: An authenticated Shotgun instance.
        """
        return sg3.Shotgun(
            cls.SHOTGRID_URL,
            script_name=cls.SHOTGRID_SCRIPT_NAME,
            api_key=cls.SHOTGRID_API_KEY,
        )

    def browse_task_data(self, task: BaseTask) -> None:
        """
        This method should be overriden according to each plugin.
        This opens the task in the plugin's database
        
        Args:
            task (BaseTask): Task whose ShotGrid detail page should be opened.
        """

        web.open(f"{self.SHOTGRID_URL}/detail/Task/{task.id}")

    def browse_version_data(self, version_id: int) -> None:
        """
        This method should be overriden according to each plugin.
        This opens the version in the plugin's database
        
        Args:
            version_id (int): ID of the version to open.
        """
        web.open(f"{self.SHOTGRID_URL}/detail/Version/{version_id}")

    def browse_note_data(self, note_id: int) -> None:
        """
        This method should be overriden according to each plugin.
        This opens the note in the plugin's database
        Args:
            note_id (int): ID of the note to open.
        """
        web.open(f"{self.SHOTGRID_URL}/detail/Note/{note_id}")

    def receive_config_data_from_app(self, *args, **kwargs) -> None:
        """
        Receives entity-type configuration data from an external application.

        Args:
            *args: Positional arguments (unused).
            **kwargs: Keyword arguments containing 'sg_active_entity'.
        """
        if kwargs.get("sg_active_entity") is not None:
            self.add_tasks_from_plugin_kwargs = {
                "sg_entity_type": kwargs.get("sg_active_entity")
            }

    def retrieve_cached(self, link_type: str) -> tuple[list[dict[str, Any]], Optional[datetime], bool]:
        """
        Attempts to load cached task data for the given link type.

        Args:
            link_type (str): The ShotGrid entity type.

        Returns:
            tuple[list[dict[str, Any]], Optional[datetime], bool]: Cached data, last modified date, and success flag.
        """
        cached_data_file = Path(
            os.environ["GWAIO_DATA_PATH"], f"sg_cache_{link_type}_{self.title}.json"
        )
        logger.debug(f"Retrieving cached data from {cached_data_file}")
        if cached_data_file.exists():
            try:
                cached_task_data = json.loads(cached_data_file.read_text())
                last_cached = cached_data_file.stat().st_mtime  # - 2592000
                plugin_task_fields_by_entity = self.return_fields_from_entity_type(
                    link_type
                )
                for cd in cached_task_data:  # Check missing keys in cache
                    [
                        cd[f]
                        for f in plugin_task_fields_by_entity
                        if f.startswith(f"entity.{link_type}")
                        or not f.startswith("entity.")
                    ]
                return cached_task_data, datetime.fromtimestamp(last_cached), True
            except Exception as e:
                remove(fspath(cached_data_file))
                logger.error(f"Failed to read cache: {str(e)}")
        return list(), None, False

    def cache_data(self, file_name: str, data: list[dict[str, Any]]) -> None:
        """
        Stores task data in a cache file.

        Args:
            file_name (str): Cache filename identifier.
            data (list[dict[str, Any]]): Data to cache.
        """
        if file_name is None:
            return
        cached_data_file = Path(
            os.environ["GWAIO_DATA_PATH"], f"sg_cache_{file_name}_{self.title}.json"
        )
        tmp_cached_data_file = Path(
            fspath(cached_data_file)
            + f".{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}.tmp"
        )
        logger.debug(f"Caching data into {cached_data_file}.")
        with tmp_cached_data_file.open("w") as ftw:
            json.dump(data, ftw, separators=(", ", ": "), indent=4)
        if cached_data_file.exists():
            remove(fspath(cached_data_file))
        tmp_cached_data_file.rename(cached_data_file)

    def return_last_version(self, task_id: int) -> Optional[dict[str, Any]]:
        """
        Returns the latest version associated with a given task.

        Args:
            task_id (int): ID of the task.

        Returns:
            Optional[dict[str, Any]]: Latest version dictionary or None.
        """
        return self.sg.find_one(
            "Version",
            [["sg_task.Task.id", "is", task_id]],
            ["code"],
            order=[{"column": "created_at", "direction": "desc"}],
        )

    def return_last_version_by_entity(self, entity: dict[str, Any], fields: list[str] = []) -> Optional[dict[str, Any]]:
        """
        Returns the most recent version associated with a specific entity.

        Args:
            entity (dict[str, Any]): ShotGrid entity dictionary.
            fields (list[str]): Additional fields to include in the query.

        Returns:
            Optional[dict[str, Any]]: Latest version dictionary or None.
        """
        return self.sg.find_one(
            "Version",
            [["entity", "is", entity]],
            ["code"] + fields,
            order=[{"column": "created_at", "direction": "desc"}],
        )

    def return_fields_from_entity_type(self, entity_type: str) -> list[str]:
        """
        Generate the list of ShotGrid fields to request based on entity type.

        Args:
            entity_type (str): The ShotGrid entity type (e.g., "Shot" or "Asset").

        Returns:
            list[str]: Unique list of field names to retrieve for the given entity.
        """
        value = list(
            set(
                [
                    f"entity.{entity_type}.code",
                    *self.plugin_task_fields,
                    "entity",
                    f"entity.Asset.task_template.TaskTemplate.sg_asset_type",
                    f"entity.Asset.sg_asset_type",
                    f"entity.Asset.sg_2d_asset_type",
                    f"entity.{entity_type}.tags",
                    f"entity.{entity_type}.sg_created_for_episode",
                    f"entity.{entity_type}.episodes",
                    f"image",
                ]
            )
        )
        if entity_type == "Shot":
            value += [
                f"entity.{entity_type}.sg_cut_in",
                f"entity.{entity_type}.sg_cut_out",
                f"entity.{entity_type}.sg_cut_duration",
                f"entity.{entity_type}.sg_sequence",
                f"entity.{entity_type}.assets",
                f"entity.{entity_type}.sg_sequence.Sequence.code",
                f"entity.{entity_type}.sg_sequence.Sequence.episode.Episode.code",
            ]
        if entity_type == "Sequence":
            value += [
                f"entity.{entity_type}.code",
                f"entity.{entity_type}.assets",
                f"entity.{entity_type}.shots",
                f"entity.{entity_type}.episode.Episode.code",
            ]

        return value

    def retrieve_latests_tasks(
        self,
        link_type: str,
        sg_filters: list[list[Any]],
        force_no_cache: bool
    ) -> list[dict[str, Any]]:
        """
        Uses the cache to get its date so that only the tasks that were updated
        after the last cache are retrieved. These tasks are merged with the cache.

        Args:
            link_type (str): The entity type to query (e.g., "Shot").
            sg_filters (list[list[Any]]): ShotGrid filter definitions.
            force_no_cache (bool): If True, bypass local cache entirely.

        Returns:
            list[dict[str, Any]]: Combined list of new and (if not forced) cached task dicts.
        """
        plugin_task_fields_by_entity = self.return_fields_from_entity_type(link_type)
        last_cache = list()
        if not force_no_cache:
            last_cache, cached_task_date, ok = self.retrieve_cached(link_type)
            if not ok:
                return
            if cached_task_date is not None and not force_no_cache:
                sg_filters.append(["updated_at", "greater_than", cached_task_date])
        latest_sg_tasks = self.async_find(
            "Task", sg_filters, plugin_task_fields_by_entity
        )
        # if force_no_cache:
        # latest_sg_tasks = self.async_find(
        # "Task", sg_filters, plugin_task_fields_by_entity
        # )
        # else:
        # with ShotgridInstance(plugin=self) as sg:
        # latest_sg_tasks = sg.find("Task", sg_filters, plugin_task_fields_by_entity)
        # with ShotgridInstance(plugin=self) as sg:
        #     latest_sg_tasks = sg.find("Task", sg_filters, plugin_task_fields_by_entity)
        if not force_no_cache:
            new_ids = [t["id"] for t in latest_sg_tasks]
            sg_tasks = latest_sg_tasks + [
                t for t in last_cache if t["id"] not in new_ids
            ]
        else:
            sg_tasks = latest_sg_tasks

        # all tasks are also looped in the get_all_tasks_data, this portion
        # could be embeded there, but having them here makes both methods cleaner.
        for sg_task in sg_tasks:
            for field in plugin_task_fields_by_entity:
                if field not in sg_task:
                    sg_task[field] = None
        return sg_tasks

    def return_data_to_show(
        self,
        sg_task: dict[str, Any],
        link_type: str,
        thumbnail: BaseThumbnail,
        assignees: list[str],
        tags: str,
        asset_type: str,
        episodes: str,
        created_for_episode: Optional[str],
        cut_in: Any,
        cut_out: Any,
        cut_duration: Any,
        sequence: Any,
        episode: Any,
    ) -> list[dict[str, Any]]:
        """
        Format a ShotGrid task into a list of UI‐ready rows matching headers.

        Args:
            sg_task (dict[str, Any]): Raw ShotGrid Task entity.
            link_type (str): Entity type of the task (e.g., "Shot").
            thumbnail (BaseThumbnail): Thumbnail object for display.
            assignees (list[str]): Names of assigned artists.
            tags (str): Space‐separated tag names.
            asset_type (str): Asset type code.
            episodes (str): Episode codes.
            created_for_episode (Optional[str]): Original episode code.
            cut_in (Any): Cut in frame or None.
            cut_out (Any): Cut out frame or None.
            cut_duration (Any): Duration in frames or None.
            sequence (Any): Sequence code or None.
            episode (Any): Episode code or None.

        Returns:
            list[dict[str, Any]]: List of dicts with keys "text", "icon", "thumbnail", "background_color".
        """
        base_data_to_show = {
            "thumbnail": None,
            "icon": None,
            "background_color": None,
        }
        return [
            # This is redundant data that is used to be shown in the
            # tree widget and they map 1 to 1 to the headers
            {
                **base_data_to_show,
                "text": sg_task[f"entity.{link_type}.code"],
                "thumbnail": thumbnail,
            },
            {
                **base_data_to_show,
                "text": sg_task["content"],
            },
            {
                **base_data_to_show,
                "text": sg_task["sg_status_list"],
                "icon": self.env_handler.get_env("GWAIO_ICONS_PATH")
                + f"/status_sg_{sg_task['sg_status_list']}.png",
                "background_color": self._color_status.get(
                    sg_task.get("sg_status_list")
                ),
            },
            {
                **base_data_to_show,
                "text": ", ".join(assignees),
            },
            {
                **base_data_to_show,
                "text": asset_type,
            },
            {
                **base_data_to_show,
                "text": tags,
            },
            {
                **base_data_to_show,
                "text": created_for_episode,
            },
            {
                **base_data_to_show,
                "text": episodes,
            },
            {
                **base_data_to_show,
                "text": cut_in,
            },
            {
                **base_data_to_show,
                "text": cut_out,
            },
            {
                **base_data_to_show,
                "text": cut_duration,
            },
            {
                **base_data_to_show,
                "text": sequence,
            },
            {
                **base_data_to_show,
                "text": episode,
            },
        ]

    def get_all_tasks_data(
        self,
        return_object: dict[str, Any],
        callback: Optional[Callable[[], None]] = None,
        force_no_cache: bool = False,
        cache_data: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Retrieve all tasks for the specified entity type, handle caching, and invoke callback.

        Args:
            return_object (dict[str, Any]): Dict to populate with `return_object["results"] = (tasks, headers)`.
            callback (Optional[Callable[[], None]]): Function to call once tasks are loaded.
            force_no_cache (bool): If True, ignore existing cache.
            cache_data (bool): If True, update the local cache with new results.
            *args: Additional positional arguments.
            **kwargs: Keyword args, expects 'sg_entity_type' key.
        """
        if (entity_type := kwargs.get("sg_entity_type")) is None:
            return

        self._active_entity = entity_type
        all_tasks = list()
        if entity_type == "My Tasks":
            try:
                filters = self.return_my_tasks_filter() + self.plugin_task_filters
            except NotImplementedError as e:
                logger.warning(
                    "Failed to retrieve the My Tasks filter, all tasks will be retrieved."
                )
                filters = []
            for entity_type in self.active_entities:
                all_tasks += self.return_tasks_by_entity(
                    entity_type, True, filters, cache_data=False
                )
        else:
            all_tasks = self.return_tasks_by_entity(
                entity_type, force_no_cache, cache_data=cache_data
            )
            if all_tasks is None:
                return

        self.tasks = all_tasks

        return_object["results"] = (all_tasks, self.headers)
        if callback is not None:
            callback()

    def return_tasks_by_entity(
        self,
        link_type: str,
        force_no_cache: bool = False,
        filters: list[list[Any]] = [],
        cache_data: bool = True
    ) -> Optional[list[BaseTask]]:
        """
        Query ShotGrid for all tasks of a given entity type and wrap them as BaseTask objects.

        Args:
            link_type (str): The entity type code (e.g., "Asset", "Shot").
            force_no_cache (bool): If True, bypass the cache layer.
            filters (list[list[Any]]): Additional ShotGrid filters.
            cache_data (bool): If True, save the raw SG results to cache.

        Returns:
            Optional[list[BaseTask]]: A list of BaseTask instances, or None on failure.
        """
        all_tasks = list()
        sg_filters = [
            ["step.Step.entity_type", "is", link_type],
            *self.plugin_task_filters + filters,
        ]

        sg_tasks = self.retrieve_latests_tasks(link_type, sg_filters, force_no_cache)
        if sg_tasks is None:
            return None

        for sg_task in sg_tasks:
            prev_task_server = Path()
            asset_type = (
                sg_task.get(f"entity.{link_type}.sg_2d_asset_type")
                or sg_task.get(
                    f"entity.{link_type}.task_template.TaskTemplate.sg_asset_type"
                )
                or sg_task.get(f"entity.{link_type}.sg_asset_type", "")
            )

            local_path, server_path = self.get_task_filesystem(
                sg_task[f"entity.{link_type}.code"],
                sg_task[f"step.Step.entity_type"],
                sg_task["content"],
                step=sg_task["step.Step.code"],
                asset_type=asset_type,
                episode=sg_task.get(
                    f"entity.{link_type}.episode.Episode.code",
                    sg_task.get(
                        f"entity.{link_type}.sg_sequence.Sequence.episode.Episode.code"
                    ),
                ),
                sequence=sg_task.get(f"entity.{link_type}.sg_sequence.Sequence.code"),
            )

            if (prev_dict := self._dict_previous_tasks.get(sg_task["content"])) is None:
                ...
            else:
                prev_task_server = self.get_task_filesystem(
                    sg_task[f"entity.{link_type}.code"],  # Teaser_010_030
                    sg_task[f"step.Step.entity_type"],  # Shot
                    **prev_dict,  # {'task': 'layout', 'step': 'LayoutStep'}
                    asset_type=asset_type,
                    episode=sg_task.get(
                        f"entity.{link_type}.episode.Episode.code",
                        sg_task.get(
                            f"entity.{link_type}.sg_sequence.Sequence.episode.Episode.code"
                        ),
                    ),
                    sequence=sg_task.get(
                        f"entity.{link_type}.sg_sequence.Sequence.code"
                    ),
                    state="publish",
                )[1]

            # assignees = [a["name"] for a in sg_task["task_assignees"]] + [
            #     sg_task[self.custom_artist_entity] or ""
            # ]

            assignees = [a["name"] for a in sg_task["task_assignees"]] + [
                sg_task[f] or ""
                for f in self.custom_artist_entities
                if not isinstance(sg_task[f], list)
            ]

            # This code may seem dodgy but we have to go with it
            # as we don't know the name of the field that the custom
            # entity will use

            for f in self.custom_artist_entities:
                if isinstance(sg_task[f], list):
                    element: dict
                    for element in sg_task[f]:
                        if element.get("code") is not None:
                            assignees.append(element.get("code"))
                        elif element.get("name") is not None:
                            assignees.append(element.get("name"))

            tags = " ".join([t["name"] for t in sg_task[f"entity.{link_type}.tags"]])
            episode = sg_task.get(
                f"entity.{link_type}.sg_sequence.Sequence.episode.Episode.code",
                sg_task.get(f"entity.{link_type}.episode.Episode.code"),
            )
            episodes = episode
            if sg_task[f"entity.{link_type}.episodes"]:
                episodes = ", ".join(
                    [e["name"] for e in sg_task[f"entity.{link_type}.episodes"]]
                )
            created_for_episode = None
            created_for_episode = sg_task.get(
                f"entity.{link_type}.sg_created_for_episode.Episode.code"
            )
            cut_in = sg_task.get(f"entity.{link_type}.sg_cut_in")
            cut_out = sg_task.get(f"entity.{link_type}.sg_cut_out")
            cut_duration = sg_task.get(f"entity.{link_type}.sg_cut_duration")
            sequence = sg_task.get(f"entity.{link_type}.sg_sequence.Sequence.code")

            assets = ",".join(
                [
                    asset.get("name", "")
                    for asset in sg_task.get(f"entity.{link_type}.assets", [])
                ]
            )

            thumbnail = BaseThumbnail(
                sg_task["id"],
                sg_task["image"],
                Path(local_path, "thumbnail"),
                on_refresh_url=partial(
                    self.return_thumbnail_url, "Task", sg_task["id"]
                ),
            )

            task = BaseTask(
                sg_task["content"],
                sg_task[f"entity.{link_type}.code"],
                local_path,
                prev_task_server,
                server_path=server_path,
                id=sg_task["id"],
                entity_type=sg_task["step.Step.entity_type"],
                entity=sg_task["entity"],
                task_entity=sg_task,
                step=sg_task["step.Step.code"],
                asset_type=asset_type,
                cut_in=cut_in,
                cut_out=cut_out,
                cut_duration=cut_duration,
                sequence=sequence,
                assets=assets,
                episode=episode,
                episodes=episodes,
                thumbnail=thumbnail,
                data_to_show=self.return_data_to_show(
                    sg_task,
                    link_type,
                    thumbnail,
                    assignees,
                    tags,
                    asset_type,
                    episodes,
                    created_for_episode,
                    cut_in,
                    cut_out,
                    cut_duration,
                    sequence,
                    episode,
                ),
            )
            all_tasks.append(task)
        if cache_data:
            self.cache_data(link_type, sg_tasks)

        return all_tasks

    def check_file_is_uploaded(self, file: Path) -> bool:
        """
        Check if a given file name has an associated PublishedFile in ShotGrid.

        Args:
            file (Path): The local file to check.

        Returns:
            bool: True if a PublishedFile with the same code exists.
        """
        return self.sg.find_one("PublishedFile", [["code", "is", file.name]]) != None

    def check_version_is_published(self, version: Path) -> bool:
        """
        Check if a given version file name has already been published to ShotGrid.

        Args:
            version (Path): Path to the version file.

        Returns:
            bool: True if a Version entity with the same code exists.
        """
        return self.sg.find_one("Version", [["code", "is", version.name]]) != None

    def return_all_assets(self) -> dict[str, dict[str, Any]]:
        """
        Retrieve all Asset entities for the configured project.

        Returns:
            dict[str, dict[str, Any]]: Mapping asset code to its SG entity dict.
        """
        asset_entities = self.sg.find(
            "Asset",
            [["project.Project.id", "is", int(self.SG_PROJECT_ID)]],
            ["code", "sg_created_for_episode.Episode.code", "parents"],
        )
        return {a["code"]: a for a in asset_entities}

    def return_all_episodes(self) -> dict[str, dict[str, Any]]:
        """
        Retrieve all Episode entities for the configured project.

        Returns:
            dict[str, dict[str, Any]]: Mapping episode code to its SG entity dict.
        """
        ep_entities = self.sg.find(
            "Episode",
            [["project.Project.id", "is", int(self.SG_PROJECT_ID)]],
            ["code"],
        )
        return {ep["code"]: ep for ep in ep_entities}

    def return_all_playlists(self) -> list[dict[str, Any]]:
        """
        Retrieve all Playlist entities for the configured project.

        Returns:
            list[dict[str, Any]]: List of Playlist entity dicts.
        """
        return self.sg.find(
            "Playlist",
            [["project.Project.id", "is", int(self.SG_PROJECT_ID)]],
            ["code"],
        )

    def return_all_sequences(self) -> dict[str, dict[str, Any]]:
        """
        Retrieve all Sequence entities for the configured project.

        Returns:
            dict[str, dict[str, Any]]: Mapping sequence code to its SG entity dict.
        """
        seq_entities = self.sg.find(
            "Sequence",
            [["project.Project.id", "is", int(self.SG_PROJECT_ID)]],
            ["code"],
        )
        return {seq["code"]: seq for seq in seq_entities}

    def return_all_shots(self, filters: list[list[Any]] = []) -> dict[str, dict[str, Any]]:
        """
        Retrieve all Shot entities, optionally filtered, for the project.

        Args:
            filters (list[list[Any]], optional): Additional filter rules.

        Returns:
            dict[str, dict[str, Any]]: Mapping shot code to its SG entity dict.
        """
        shot_entities = self.sg.find(
            "Shot",
            [["project.Project.id", "is", int(self.SG_PROJECT_ID)], *filters],
            [
                "code",
                "sg_sequence",
                "sg_status_list",
                "sg_cut_in",
                "sg_cut_out",
                "sg_cut_duration",
            ],
            order=[{"column": "code", "direction": "asc"}],
        )
        return {sh["code"]: sh for sh in shot_entities}

    def return_all_versions(
        self,
        filters: Optional[list[list[Any]]] = None,
        fields: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve all Version entities matching optional filters.

        Args:
            filters (Optional[list[list[Any]]]): ShotGrid filters to apply.
            fields (Optional[list[str]]): Fields to include in results.

        Returns:
            list[dict[str, Any]]: List of Version entity dicts.
        """
        sg = self._instantiate_shogrid()

        filters = [["project.Project.id", "is", int(self.SG_PROJECT_ID)]] + (
            [filters] if filters else []
        )

        version_entities = sg.find(
            "Version",
            filters,
            [
                "code",
                "sg_status_list",
                "sg_task",
                "sg_task.Task.sg_status_list",
                "entity",
            ]
            + fields,
            order=[{"column": "created_at", "direction": "desc"}],
        )
        sg.close()
        return version_entities

    def return_all_packages(
        self,
        filters: Optional[list[list[Any]]] = None,
        fields: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve all PublishedFile (package) entities matching optional filters.

        Args:
            filters (Optional[list[list[Any]]]): ShotGrid filters to apply.
            fields (Optional[list[str]]): Fields to include in results.

        Returns:
            list[dict[str, Any]]: List of PublishedFile entity dicts.
        """
        sg = self._instantiate_shogrid()

        filters = [["project.Project.id", "is", int(self.SG_PROJECT_ID)]] + (
            [filters] if filters else []
        )

        package_entities = sg.find(
            "PublishedFile",
            filters,
            ["code"] + fields,
            order=[{"column": "created_at", "direction": "desc"}],
        )
        sg.close()
        return package_entities

    def return_entity_description(
        self,
        task: BaseTask,
        force_stop: Callable[[], bool] = lambda: False
    ) -> str:
        """
        Fetch the description of the entity linked to a given task.

        Args:
            task (BaseTask): Task whose parent entity description to retrieve.
            force_stop (Callable[[], bool], optional): If True at any point, aborts and returns empty string.

        Returns:
            str: The entity's description, or empty string if not found/aborted.
        """
        sg = self._instantiate_shogrid()
        entity_type = task.entity.get("type")
        result = sg.find_one(
            "Task", [["id", "is", task.id]], [f"entity.{entity_type}.description"]
        )
        sg.close()
        if not result or force_stop():
            return str()
        return result.get(f"entity.{entity_type}.description")

    def return_playlist_media(
        self,
        playlist_id: int,
        fields: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve Version entities associated with a Playlist, including notes.

        Args:
            playlist_id (int): ID of the Playlist entity.
            fields (Optional[list[str]]): Additional fields to include.

        Returns:
            list[dict[str, Any]]: List of Version entity dicts in the playlist.
        """
        filters = [
            ["playlists", "is", [{"type": "Playlist", "id": playlist_id}]],
            ["open_notes", "is_not", None],
        ]
        if fields is None:
            fields = [
                "open_notes",
                "sg_status_list",
                "code",
                "sg_task",
                "sg_task.Task.sg_status_list",
                "open_notes",
            ]
        order = [{"column": "sg_sort_order", "direction": "asc"}]
        return self.sg.find("Version", filters, fields, order)

    def return_task_versions(self, task: BaseTask) -> list[list[Any]]:
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
            task (BaseTask): The task entity to query versions for.

        Returns:
            list[list[Any]]: A list of version details, each item containing:
                [version_id, thumbnail_url, version_code, user_name, status_code]
        """
        version_list = self.return_all_versions(
            filters=["sg_task.Task.id", "is", task.id], fields=["user", "image"]
        )
        data_to_show = list()
        for version_data in version_list:
            data_to_show.append(
                [
                    version_data.get("id"),
                    version_data.get("image"),
                    version_data.get("code"),
                    version_data.get("user", dict()).get("name"),
                    version_data.get("sg_status_list"),
                ]
            )
        return data_to_show

    def return_task_notes(
        self, task: BaseTask, force_stop: Callable[[], bool] = lambda: False
    ) -> list[dict[str, Any]]:
        """Base method to create the note listing logic of a task,
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
            task (BaseTask): The task for which to retrieve notes.
            force_stop (Callable[[], bool], optional): If True, aborts and returns empty list.

        Returns:
            list[dict[str, Any]]: List of notes including content, author, timestamp,
            attachments, replies, and direct ShotGrid URLs.
        """
        sg = self._instantiate_shogrid()
        report_data = list()
        list_notes_id = [
            note.get("id")
            for note in sg.find_one(
                "Task", [["id", "is", task.id]], ["open_notes"]
            ).get("open_notes", [])
        ]
        data_notes = []
        if list_notes_id != []:
            data_notes = sg.find(
                "Note",
                [["id", "in", list_notes_id]],
                ["user", "attachments", "replies", "content", "created_at"],
                [{"field_name": "created_at", "direction": "desc"}],
            )

        list_replies_id = [
            attach["id"] for note in data_notes for attach in note.get("replies", [])
        ]
        data_replies = []
        if list_replies_id != []:
            data_replies = sg.find(
                "Reply",
                [["id", "in", list_replies_id]],
                [
                    "user",
                    "attachments",
                    "sg_sk_note_id",
                    "replies",
                    "content",
                    "created_at",
                ],
            )

        list_notes_attachments_id = [
            attach["id"]
            for note in data_notes
            for attach in note.get("attachments", [])
        ]
        list_replies_attachments_id = [
            attach["id"]
            for note in data_replies
            for attach in note.get("attachments", [])
        ]

        data_attachments = dict()
        if any([list_notes_attachments_id, list_replies_attachments_id]):
            data_attachments = {
                a["id"]: a["image"]
                for a in sg.find(
                    "Attachment",
                    [
                        [
                            "id",
                            "in",
                            list_notes_attachments_id + list_replies_attachments_id,
                        ]
                    ],
                    ["image"],
                )
            }
        data_reply_dict = dict()
        for reply in data_replies:
            list_attach_data = [
                {
                    "url_open": sg.get_attachment_download_url(a["id"]),
                    "url_image": data_attachments[a["id"]],
                }
                for a in reply.get("attachments", [])
            ]

            data_reply_dict[reply["id"]] = {
                "content": reply["content"],
                "created_at": reply["created_at"].strftime("%b %d, %Y, %H:%M"),
                "created_by": reply["user"]["name"],
                "attachments": list_attach_data,
                "url": f"{self.SHOTGRID_URL}/detail/Reply/{reply['id']}",
            }

        for note in data_notes:
            list_attach_data = [
                {
                    "url_open": sg.get_attachment_download_url(a["id"]),
                    "url_image": data_attachments[a["id"]],
                }
                for a in note.get("attachments", [])
            ]

            note_data = {
                "content": note["content"],
                "created_at": note["created_at"].strftime("%b %d, %Y, %H:%M"),
                "created_by": note["user"]["name"],
                "attachments": list_attach_data,
                "url": f"{self.SHOTGRID_URL}/detail/Note/{note['id']}",
                "reply": [data_reply_dict[reply["id"]] for reply in note["replies"]],
            }
            report_data.append(note_data)

        if force_stop():
            return list()
        return report_data

    def return_versions_notes(
        self, list_version: list[dict[str, Any]], download_attachments: Union[Path, bool] = False
    ) -> list[dict[str, Any]]:
        """Base method to create the note listing logic of a playlist,
        the returned object must be a list with the following structure:
        
        [{
            "content" : str,
            "created_by" : str  or None,
            "created_at" : str or None,
            "attachments" : dict["url","bytes"],
            "url" : str
        }]
        
        Args:
            list_version (list[dict[str, Any]]): Versions to extract notes from.
            download_attachments (Union[Path, bool], optional): Destination path to download attachments or False.

        Returns:
            list[dict[str, Any]]: Updated version dictionaries with note attachments.
        """
        sg = self._instantiate_shogrid()
        list_notes = list()
        for version in list_version:
            list_notes += [n for n in version.get("open_notes")]
        list_notes_id = [note.get("id") for note in list_notes]
        list_notes_data = sg.find(
            "Note", [["id", "in", list_notes_id]], ["attachments"]
        )

        for version in list_version:
            for note in version.get("open_notes"):
                for n in list_notes_data:
                    if n.get("id") == note.get("id"):
                        note["attachments"] = n.get("attachments")
                        break

        sg.close()
        return list_version

    def return_version_notes(
        self, version: dict[str, Any], download_attachments: Union[Path, bool] = False
    ) -> list[dict[str, Any]]:
        """Base method to create the note listing logic of a playlist,
        the returned object must be a list with the following structure:
        
        [{
            "content" : str,
            "created_by" : str  or None,
            "created_at" : str or None,
            "attachments" : dict["url","bytes"],
            "url" : str
        }]

        Args:
            version (dict[str, Any]): A ShotGrid version dictionary.
            download_attachments (Union[Path, bool], optional): Path to download files to.

        Returns:
            list[dict[str, Any]]: The same version dict with 'attachments' populated.
        """
        sg = self._instantiate_shogrid()
        if version.get("open_notes") is None:
            version = sg.find_one(
                "Version", [["id", "is", version.get("id")]], ["open_notes"]
            )
        for note in version.get("open_notes"):
            attachments = sg.find_one(
                "Note", [["id", "is", note["id"]]], ["attachments"]
            ).get("attachments")
            if download_attachments is not False:
                note["attachments"] = list()
                for attach in attachments:
                    file_path = Path(download_attachments / attach["name"])
                    if not file_path.exists():
                        sg.download_attachment(attach, file_path=(fspath(file_path)))
                    note["attachments"].append(file_path)
            else:
                note["attachments"] = attachments
        sg.close()
        return version

    def return_thumbnail_url(self, entity_type: str, id: int) -> Optional[str]:
        """
        Retrieve the thumbnail image URL for a specific entity.

        Args:
            entity_type (str): The type of entity (e.g., 'Task', 'Asset').
            id (int): ID of the entity.

        Returns:
            Optional[str]: URL of the thumbnail image or None if not found.
        """
        sg = self._instantiate_shogrid()
        result = sg.find_one(entity_type, [["id", "is", id]], ["image"])["image"]
        sg.close()
        return result

    def return_custom_artist_entity(self) -> Union[dict[str, Any], bool]:
        """
        Return the custom artist entity linked to the current user.

        Returns:
            Union[dict[str, Any], bool]: ShotGrid entity dict or False if not found/configured.
        """
        if not all(
            [
                self.custom_artist_entity_name,
                self.custom_artist_login_field,
            ]
        ):
            return False
        return self.sg.find_one(
            self.custom_artist_entity_name,
            [[self.custom_artist_login_field, "is", self.username]],
        )

    def download_package(self, package: Union[str, BaseTask]) -> Optional[list[Path]]:
        """
        Download a package from ShotGrid by task or package name and extract it.

        Args:
            package (Union[str, BaseTask]): Task or package name to download.

        Returns:
            Optional[list[Path]]: List of extracted files or None.
        """
        temp = TemporaryDirectory()
        TEMP_FOLDER = temp.name
        package_folder = Path(TEMP_FOLDER)
        logger.info(f"Downloading package...")
        if isinstance(package, BaseTask):
            package_path = self.dowload_last_file_from_task(package, package_folder)
        elif isinstance(package, str):
            package_path = self.dowload_last_file_from_name(package, package_folder)
        if package_path:
            logger.info(f"Package Downloaded successfully...")
            logger.info(f"Extracting package file: {fspath(package_path)}")
            list_files = extract_package(package_path, self.local_root)
            return list_files

    def upload_package(
        self, list_files: list[Path], package_name: str, task: Optional[BaseTask] = None
    ) -> Iterator[tuple[int, str]]:
        """
        Create and upload a zip package containing the specified files and their Maya dependencies.

        This function yields progress updates at different stages of packaging and uploading:
        - 0–10%: Preparing files
        - 10–50%: Resolving Maya dependencies
        - 70–99%: Uploading the package to ShotGrid

        Args:
            list_files (list[Path]): List of files to include in the package.
            package_name (str): The name for the zip archive to be created.
            task (Optional[BaseTask]): Optional task context to associate the upload with.

        Yields:
            Iterator[tuple[int, str]]: Tuples of (progress percentage, status message).
        """
        temp = TemporaryDirectory()
        TEMP_FOLDER = temp.name
        package_path = Path(TEMP_FOLDER, package_name)
        logger.info(f"Creating package file: {fspath(package_path)}")
        yield (0, f"Creating package file: {fspath(package_path)}")
        total = len(list_files)
        for idx, file in enumerate(list(list_files)):
            percent = int((idx / total) * 10)
            if Path(file).is_dir():
                list_files += list(Path(file).rglob("*"))
            yield (percent, f"Capturing maya dependencies {Path(file).name}...")

        total = len(list(set(list_files)))
        for idx, file in enumerate(list(set(list_files))):
            if Path(file).suffix == ".ma":
                percent = int((idx / total) * 40) + 10
                logger.info(
                    f"{percent}% Capturing maya dependencies {Path(file).name}..."
                )
                yield (percent, f"Capturing maya dependencies {Path(file).name}...")
                env = self.generate_environment_for_app()
                result = execute_mayapy(
                    fspath(file),
                    env,
                    f"list(return_all_dependencies(resolve_environs = True))",
                )
                list_files += result

        _, zip_files, zip_files_not_found = create_package(
            list(set(list_files)), self.local_root, package_path
        )
        description = (
            "\n".join(
                [f"found: {f}" for f in zip_files]
                + [f"not found: {f}" for f in zip_files_not_found]
            )
            + f"\nGWAIO VERSION: {metadata.PROGRAM_VERSION}"
        )
        logger.debug(f"Desccription:\n {description}")
        logger.info(f"Upload package {package_path.stem}...")
        yield (70, f"Uploading package {package_path.stem}...")
        logger.info(f"Uploading package {package_path.stem}...")
        result = self.upload_file(package_path, task, description)
        if result.get("success"):
            logger.info(f"Uploaded package successfully. {package_path.stem}")
            yield (99, f"Uploaded package successfully. {package_path.stem}")
        else:
            logger.error(result.get("error"))
            raise Exception(result.get("error"))

    def generate_package_name(self, task: BaseTask) -> str:
        """
        Generate a unique package name based on task and current user.

        Args:
            task (BaseTask): The task to generate the package name for.

        Returns:
            str: A filename-safe package name.
        """
        return f"gwaio_{task.link_name}_{task.name}_{task.id}_package_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.username}.zip"

    def dowload_last_file_from_task(self, task: BaseTask, path: Optional[Union[str, Path]] = None) -> Optional[Path]:
        """
        Download the last file published for a given task.

        Args:
            task (BaseTask): Task to query.
            path (Optional[Union[str, Path]]): Destination path.

        Returns:
            Optional[Path]: File path if downloaded, else None.
        """
        find_result = self.sg.find(
            "PublishedFile",
            [["task.Task.id", "is", task.id]],
            [],
            order=[{"column": "created_at", "direction": "desc"}],
        )
        if find_result:
            return self.download_file(find_result[0].get("id"), path or task.local_path)

    def dowload_last_file_from_name(self, name: str, path: str) -> Optional[Path]:
        """
        Download the most recent published file whose code contains the given name.

        Args:
            name (str): Name substring to match against the PublishedFile code.
            path (str): Destination folder path where the file will be downloaded.

        Returns:
            Optional[Path]: Local path of the downloaded file if successful, otherwise None.
        """
        find_result = self.sg.find(
            "PublishedFile",
            [["code", "contains", name]],
            [],
            order=[{"column": "created_at", "direction": "desc"}],
        )
        if find_result:
            return self.download_file(find_result[0].get("id"), path)

    def download_last_version_from_entity(self, task: str, id: int, path: Path) -> bool:
        """
        Download the last uploaded MP4 movie associated with a specific entity.

        Args:
            task (str): Unused placeholder argument.
            id (int): Entity ID.
            path (Path): Destination file path.

        Returns:
            bool: True if download was successful, otherwise False.
        """
        url = self.sg.find_one(
            "Version", [["entity.id", "is", id]], ["sg_uploaded_movie_mp4"]
        ).get("sg_uploaded_movie_mp4")
        file_path = fspath(path)

        if url is not None:
            result = self.sg.download_attachment({"url": url}, file_path=file_path)
            return True
        return False

    def download_version(self, id: int, path: Path) -> Union[Path, bool]:
        """
        Download the movie file from a version.

        Args:
            id (int): ShotGrid Version ID.
            path (Path): Directory to store the downloaded file.

        Returns:
            Union[Path, bool]: Path to downloaded file or False if unsuccessful.
        """
        url_data = self.sg.find_one(
            "Version", [["id", "is", id]], ["sg_uploaded_movie_mp4"]
        ).get("sg_uploaded_movie_mp4")
        if url_data is not None:
            file_path = fspath(Path(path, url_data["name"]))
            if not Path(file_path).exists():
                Path(path).mkdir(parents=True, exist_ok=True)
                result = self.sg.download_attachment(
                    {"url": url_data["url"]}, file_path=file_path
                )
            return file_path
        return False

    def download_file(self, id: int, path: Path) -> Union[Path, bool]:
        """
        Download a PublishedFile from ShotGrid by ID.

        Args:
            id (int): ShotGrid PublishedFile ID.
            path (Path): Directory to save the file to.

        Returns:
            Union[Path, bool]: Local path to the file, or False if failed.
        """
        url_data = self.sg.find_one("PublishedFile", [["id", "is", id]], ["path"]).get(
            "path"
        )
        # pprint(url_data)
        if url_data is not None:
            file_path = fspath(Path(path, url_data["name"]))
            result = self.sg.download_attachment(
                {"url": url_data["url"]}, file_path=file_path
            )
            return file_path
        return False

    def download_thumbnail_from_sg(self, entity_type: str, id: int, path: Path) -> bool:
        """
        Download a thumbnail image from a ShotGrid entity.

        Args:
            entity_type (str): Type of entity (e.g., 'Task').
            id (int): ID of the entity.
            path (Path): Path where the image should be saved.

        Returns:
            bool: True if successful, False otherwise.
        """
        url = self.sg.find_one(entity_type, [["id", "is", id]], ["image"]).get("image")
        file_path = fspath(path)

        if url is not None:
            result = self.sg.download_attachment({"url": url}, file_path=file_path)
            return True
        return False

    def download_versions_from_sg(self) -> None:
        """
        Download all version movie files (sg_uploaded_movie) for selected tasks.

        For each version in each selected task, this function saves the movie to the preview location
        if it doesn't already exist.
        """
        for task in self.current_selected_tasks:
            list_versions = self.sg.find(
                "Version",
                [["sg_task", "is", {"id": task.id, "type": "Task"}]],
                ["sg_uploaded_movie"],
            )

            for version_data in list_versions:
                data = version_data.get("sg_uploaded_movie")
                if data is None:
                    continue
                url = data.get("url")
                name = data.get("name")
                out_path = Path(task.local_path, self._preview_location or "", name)
                if out_path.exists():
                    continue
                if not out_path.parent.exists():
                    out_path.parent.mkdir(parents=True)
                logger.debug(f"Saving version: {out_path}")
                self.sg.download_attachment({"url": url}, file_path=fspath(out_path))

    def create_thumbnail(self, task: BaseTask) -> Optional[Path]:
        """
        Generate and set a thumbnail for the given task.

        Attempts to generate a thumbnail from the latest .jpg file in the task directory.
        If not found, it falls back to downloading from ShotGrid.

        Args:
            task (BaseTask): The task for which to create the thumbnail.

        Returns:
            Optional[Path]: Path to the generated thumbnail or None if failed.
        """
        file_path = fspath(task.thumbnail.path)
        while True:
            # Generate thumbnail from last file
            try:
                dir = task.local_path
                file_path = max(
                    [*dir.glob(f"*.jpg"), *dir.glob(f"*/*.jpg")], key=os.path.getmtime
                )
                if task.thumbnail.path.exists():
                    remove(fspath(task.thumbnail.path))
                copy2(file_path, task.thumbnail.path)
                break
            except Exception as e:
                pass

            # Download from SG
            if self.download_thumbnail_from_sg(
                "Task", task.task_entity.get("id"), file_path
            ):
                break

            return False

        return self.resize_thumbnail_image(task.thumbnail.path)

    def publish_last_version(self, task: Optional[BaseTask] = None) -> bool:
        """
        Publish the last version file for the specified or last-clicked task.

        Args:
            task (Optional[BaseTask]): Task to publish. Defaults to last clicked.

        Returns:
            bool: True if publishing succeeds, otherwise False.
        """
        _, last_version = self.return_last_file(task)
        return self.publish_version(task or self.last_task_clicked, last_version)

    def upload_file(
        self, file: Path, task: Optional[BaseTask] = None, description: str = ""
    ) -> dict[str, Any]:
        """
        Upload a local file to ShotGrid as a PublishedFile.

        Args:
            file (Path): The file to upload.
            task (Optional[BaseTask]): The task associated with the file.
            description (str): Optional description for the upload.

        Returns:
            dict[str, Any]: A result dictionary indicating success, message, and error if any.
        """
        if self.username is None:
            logger.debug("Failed to get logged user.")
            return {
                "success": False,
                "message": "Upload failed",
                "error": "Failed to get logged user.",
            }

        relative_file = Path(
            "./",
            # self._server_root,
            *file.parts[
                len(Path(self.env_handler.get_env("GWAIO_LOCAL_ROOT")).parts) :
            ],
        ).as_posix()

        custom_artist_entity = self.return_custom_artist_entity()
        if not custom_artist_entity or not self.publishedfile_artist_entity_field:
            msg = "Failed to find a publish config in plugin."
            if not custom_artist_entity:
                msg = "Artist not found in Shotgrid."
            logger.debug(msg)
            return {
                "success": False,
                "message": "Upload failed",
                "error": msg,
            }

        version = None
        if task:
            logger.debug("Getting Task")
            version = self.sg.find_one(
                "Version",
                [
                    ["code", "contains", file.stem],
                    ["sg_task", "is", {"id": task.task_entity["id"], "type": "Task"}],
                ],
            )

        data = {
            "project": {"id": int(self.SG_PROJECT_ID), "type": "Project"},
            "code": file.name,
            "name": fspath(relative_file),
            # "published_file_type":file.suffix,
            "description": description,
            self.publishedfile_artist_entity_field: custom_artist_entity,
            # "sg_status_list": 'cmpt',
            # "sg_uploader": self.username,
        }
        if task:
            data.update(
                {
                    "task": {"id": task.task_entity["id"], "type": "Task"},
                    "entity": task.entity,
                }
            )
        if version:
            data.update(
                {
                    "version": version,
                }
            )
        try:
            logger.debug("Creating PublishedFile")
            file_entity: dict = self.sg.create("PublishedFile", data)
            logger.debug("PublishedFile created successfully")
            logger.debug("Uploading PublishedFile")
            self.sg.upload(
                "PublishedFile",
                file_entity["id"],
                file,
                field_name="path",
                display_name=file.name,
            )
            logger.debug("Upload PublishedFile success")
        except Exception as e:
            logger.error("Failed upload PublishedFile")
            try:
                logger.error("trying clear PublishedFile")
                self.sg.delete("PublishedFile", file_entity.get("id"))
            except Exception as e2:
                logger.debug("Failed to remove PublishedFile, please check statuses.")
                logger.error(str(e2))
            raise Exception(e)

        return {
            "success": True,
            "message": "Upload was successfull",
            "error": None,
        }

    def publish_file(
        self, file: Path, version: Optional[dict[str, Any]] = None, task: Optional[BaseTask] = None, description: str = ""
    ) -> dict[str, Union[bool, str, None]]:
        """
        Upload a file as a PublishedFile entity to ShotGrid.

        Args:
            file (Path): The local file path to upload.
            version (Optional[dict[str, Any]]): Version entity to link with this PublishedFile.
            task (Optional[BaseTask]): Task associated with the file.
            description (str): Description of the upload.

        Returns:
            dict[str, Union[bool, str, None]]: Dictionary containing upload status, message and any error.
        """
        if self.username is None:
            logger.debug("Failed to get logged user.")
            return {
                "success": False,
                "message": "Upload failed",
                "error": "Failed to get logged user.",
            }

        relative_file = Path(
            "./",
            *file.parts[
                len(Path(self.env_handler.get_env("GWAIO_LOCAL_ROOT")).parts) :
            ],
        ).as_posix()

        custom_artist_entity = self.return_custom_artist_entity()
        if not custom_artist_entity or not self.publishedfile_artist_entity_field:
            msg = "Failed to find a publish config in plugin."
            if not custom_artist_entity:
                msg = "Artist not found in Shotgrid."
            logger.debug(msg)
            return {
                "success": False,
                "message": "Upload failed",
                "error": msg,
            }

        data = {
            "project": {"id": int(self.SG_PROJECT_ID), "type": "Project"},
            "code": file.name,
            "name": file.name,#fspath(relative_file),
            "description": description,
            self.publishedfile_artist_entity_field: custom_artist_entity,
        }
        if task:
            data.update(
                {
                    "task": {"id": task.task_entity["id"], "type": "Task"},
                    "entity": task.entity,
                }
            )
        if version:
            data.update(
                {
                    "version": version,
                }
            )
        try:
            logger.debug("Creating PublishedFile")
            file_entity: dict = self.sg.create("PublishedFile", data)
            logger.debug("PublishedFile created successfully")
            logger.debug("Uploading PublishedFile")
            self.sg.upload(
                "PublishedFile",
                file_entity["id"],
                file,
                field_name="path",
                display_name=fspath(relative_file),
            )
            logger.debug("Upload PublishedFile success")
        except Exception as e:
            logger.error("Failed upload PublishedFile")
            try:
                logger.error("trying clear PublishedFile")
                self.sg.delete("PublishedFile", file_entity.get("id"))
            except Exception as e2:
                logger.debug("Failed to remove PublishedFile, please check statuses.")
                logger.error(str(e2))
            raise Exception(e)

        return {
            "success": True,
            "message": "Upload was successfull",
            "error": None,
        }


    def publish_version(
        self, task: BaseTask, version: Path, description: str = ""
    ) -> dict[str, Union[bool, str, None, dict[str, Any]]]:
        """
        Method for creating the logic for publishing, the return
        object should be a dictionary with the following structure:
        
        {
            "success" : bool,
            "message" : str,
            "error" : str |None # Exception like error
            "entity" : dict |None
        }

        Args:
            task (BaseTask): Task associated with the version.
            version (Path): Local path to the video file to upload.
            description (str): Optional description of the version.

        Returns:
            dict[str, Union[bool, str, None, dict[str, Any]]]:
                A result dict with status, message, error (if any), and version entity.
        """
        if isinstance(task,dict):
            task = BaseTask(**task)

        if self.username is None:
            return {
                "success": False,
                "message": "Upload failed. Failed to get logged user.",
                "error": "Failed to get logged user.",
                "entity": None,
            }

        custom_artist_entity = self.return_custom_artist_entity()
        if not custom_artist_entity or not self.version_artist_entity_field:
            msg = "Failed to find a publish config in plugin."
            if not custom_artist_entity:
                msg = "Artist not found in Shotgrid."
            logger.debug(msg)
            return {
                "success": False,
                "message": "Upload failed",
                "error": msg,
                "entity": None,
            }
        
        if self.check_version_is_published(version) or version is None:
            return {
                "success": False,
                "error": None,
                "message": "The version has already been uploaded"
                " or nothing was selected",
                "entity": None,
            }

        server_version = Path(
            self._server_root,
            *version.parts[
                len(Path(self.env_handler.get_env("GWAIO_LOCAL_ROOT")).parts) :
            ],
        )

        data = {
            "project": {"id": int(self.SG_PROJECT_ID), "type": "Project"},
            "code": version.name,
            "description": description,
            "sg_status_list": self._upload_status,
            self.version_artist_entity_field: custom_artist_entity,
            "sg_path_to_jpg_file": os.fspath(server_version.parent),
            "sg_task": {"id": task.task_entity["id"], "type": "Task"},
            "entity": task.entity,
        }
        filtered_data = {
            k: v for k, v in data.items() if k in self._version_publish_fields
        }

        try:
            version_entity: dict = self.sg.create("Version", filtered_data)

            self.sg.upload(
                "Version",
                version_entity["id"],
                version,
                field_name="sg_uploaded_movie",
                display_name=version.name,
            )
            self.sg.update(
                "Version",
                version_entity["id"],
                {
                    "sg_status_list": self._upload_status,
                    self.version_artist_entity_field: custom_artist_entity,
                },
            )

        except Exception as e:
            try:
                self.sg.delete("Version", version_entity.get("id"))
            except Exception as e2:
                logger.debug("Failed to remove version, please check statuses.")

            raise Exception(e)

        return {
            "success": True,
            "message": "Upload was successfull",
            "error": None,
            "entity": version_entity,
        }

    def publish_timelog(self, task: BaseTask, duration: int) -> dict[str, Union[bool, str, None]]:
        """
        Publish a timelog entry in ShotGrid for the given task and duration.

        Args:
            task (BaseTask): The task for which the timelog will be created.
            duration (int): Duration in minutes to be logged.

        Returns:
            dict[str, Union[bool, str, None]]: A result dict with status, message, and error.
        """
        if self.username is None:
            return {
                "success": False,
                "message": "Publish timelog failed",
                "error": "Failed to get logged user.",
            }

        custom_artist_entity = self.return_custom_artist_entity()
        if not custom_artist_entity or not self.timelog_artist_entity_field:
            return {
                "success": False,
                "message": "Publish timelog failed",
                "error": "Failed to config plugin.",
            }
        try:
            data = {
                "entity": {"id": task.task_entity["id"], "type": "Task"},
                "duration": duration,
                "project": {"id": int(self.SG_PROJECT_ID), "type": "Project"},
                self.timelog_artist_entity_field: custom_artist_entity,
            }
            timelog_entity = self.sg.create("TimeLog", data)
        except Exception as e:
            try:
                self.sg.delete("TimeLog", timelog_entity.get("id"))
            except Exception as e2:
                logger.debug("Failed to remove version, please check statuses.")

            raise Exception(e)

        return {
            "success": True,
            "message": "Publish TimeLog was successfull",
            "error": None,
        }

    @staticmethod
    def return_pack_folder(folder_name: str, add_date: bool = False) -> str:
        """
        Generate a pack folder name, optionally appending the current date.

        Args:
            folder_name (str): Base name of the folder.
            add_date (bool): If True, appends current date in YYYYMMDD format.

        Returns:
            str: Final folder name.
        """
        if add_date:
            return f"{folder_name}/{datetime.now().strftime('%Y%m%d')}"
        return folder_name

    def parse_edl_file(
        self,
        source_edl: Path,
        source_video: Path,
        episode_name: Optional[str] = None,
        edl_target_task: Optional[str] = None,
        task: Optional[BaseTask] = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Parse an EDL file and yield shot metadata for creation or update.

        Args:
            source_edl (Path): Path to the source EDL file.
            source_video (Path): Path to the source video file.
            episode_name (Optional[str]): Name of the episode to associate with the EDL.
            edl_target_task (Optional[str]): Name of the EDL-related task.
            task (Optional[BaseTask]): Optional BaseTask context fallback.

        Yields:
            Generator[dict[str, Any], None, None]: Metadata for each parsed shot.
        """
        task = task or self.last_file_clicked
        # versions = self.return_all_versions()
        sequences = self.return_all_sequences()
        self._edl_target_task = edl_target_task or self._edl_target_task
        

        step_entity = self.sg.find_one(
            "Task",
            [
                ["content", "is", self._edl_target_task],
                ["step", "is_not", None],
                ["project.Project.id", "is", self.SG_PROJECT_ID],
            ],
            ["step.Step.code"],
        )
        step_name = step_entity["step.Step.code"]

        episode_name = (
            episode_name or self._edl_episode_regex.findall(source_edl.stem)[0]
        )
        episode_entity = self.return_all_episodes()[episode_name]
        sequence_name = (
            f"{self._edl_sequence_prefix}{self.edl_sequence_regex.findall(source_edl.stem)[0]}"
            if not self._episode_edl_workflow
            else None
        )
        if not self._episode_edl_workflow and self._edl_ep_in_sq:
            sequence_name = f"{episode_name}_{sequence_name}"

        version_number = self.edl_version_regex.findall(source_edl.stem)[0]
        sequence_entity = sequences[sequence_name] if sequence_name else None
        shots = (
            self.return_all_shots([["sg_sequence", "is", sequence_entity]])
            if not self._episode_edl_workflow
            else self.return_all_shots(
                [["sg_sequence.Sequence.episode", "is", episode_entity]]
            )  # TODO: ?????
        )

        source_task = self.return_base_task_with_kwargs(
            link_name=sequence_name or episode_name, name=self._edl_target_task
        )

        last_task_clicked = self.last_task_clicked
        self.last_task_clicked = source_task
        try:
            source_file_name: Path = self.return_next_version_name(
                ["mp4", "mov"], int(version_number) - 1
            ).get("full_file_name")
        except AttributeError as e:
            raise AttributeError(
                "It looks like there was an error while parsing tasks."
                "Please make sure that GwaIO has loaded the correct task types for "
                f"this {'episode' if self._episode_edl_workflow else 'sequence'}."
            )
        self.last_task_clicked = last_task_clicked

        good_shots = list()
        for clip_tuple in read_xml(source_edl, rate=self._fps):
            logger.debug(clip_tuple)
            shot_data = dict()
            shot_name = (
                (
                    f"{sequence_name}_{self._edl_shot_prefix}{self._edl_shot_regex.findall(clip_tuple[0])[0]}"
                )
                if not self._episode_edl_workflow
                else (
                    f"{episode_name}_{self._edl_shot_regex.findall(clip_tuple[0])[0]}"
                )
            )

            name, v_file, duration, start, end, seq_start = clip_tuple

            if self._episode_edl_workflow is True:
                sequence_name, shot_name = self.return_seq_and_shot_from_clipname(
                    v_file
                )
                if sequence_name in sequences.keys():
                    sequence_entity = sequences[sequence_name]
                else:
                    sequence_data = {
                        "code": sequence_name,
                        "episode": episode_entity,
                        "project": {"id": int(self.SG_PROJECT_ID), "type": "Project"},
                        # "task_template": {"id": self._sequence_task_template_id, "type": "TaskTemplate"},
                    }
                    sequence_entity = self.sg.create(
                        "Sequence", sequence_data, ["code"]
                    )
                    sequences[sequence_name] = sequence_entity

            logger.debug(f"{sequence_name}, {shot_name}")
            task_short_name = self._task_long_to_short.get(self._edl_target_task)
            video_file = source_video.parent / (
                f"{self._edl_episode_prefix}{shot_name}_{task_short_name}_v{version_number}.mov"
            )
            local_path, server_path = self.get_task_filesystem(
                shot_name,  # Teaser_010_030
                "Shot",  # Shot
                self._edl_target_task,
                asset_type=None,
                episode=episode_name,
                sequence=sequence_name,
                step=step_name,
            )
            shot_data.update(
                {
                    "shot_name": shot_name,
                    "sequence_entity": sequence_entity,
                    "video_file": video_file,
                    "new_status": "ip",
                    "new_duration": int(duration),
                    "new_start": int(start),
                    "new_end": int(end),
                    "local_path": local_path,
                    "server_path": server_path,
                    "source_server_path": Path(
                        source_task.server_path, source_file_name.name
                    ),
                    "source_local_path": source_file_name,
                    "seq_start": seq_start,
                }
            )

            if shot_name not in shots:
                shot_data.update({"shot_missing": True})

            else:
                shot_entity = shots[shot_name]
                shot_data.update(
                    {
                        "old_status": shot_entity.get("sg_status_list"),
                        "old_duration": shot_entity.get("sg_cut_duration"),
                        "old_start": shot_entity.get("sg_cut_in"),
                        "old_end": shot_entity.get("sg_cut_out"),
                        "shot_entity": shot_entity,
                        # "local_path": local_path,
                        # "source_local_path": source_file_name,
                        # "source_server_path": Path(
                        #     source_task.server_path, source_file_name.name
                        # ),
                    }
                )
            # ep, seq, shot = self.parse_clip_name(name)
            good_shots.append(shot_name)
            yield shot_data

        for shot_name, shot_entity in shots.items():
            if shot_name not in good_shots:
                yield {
                    "shot_name": shot_name,
                    "sequence_entity": sequence_entity,
                    "shot_entity": shot_entity,
                    "old_status": shot_entity.get("sg_status_list"),
                    "old_duration": shot_entity.get("sg_cut_duration"),
                    "old_start": shot_entity.get("sg_cut_in"),
                    "old_end": shot_entity.get("sg_cut_out"),
                    "video_file": None,
                    "new_status": "omt",
                    "new_duration": shot_entity.get("sg_cut_duration"),
                    "source_local_path": source_file_name,
                    "new_start": shot_entity.get("sg_cut_in"),
                    "new_end": shot_entity.get("sg_cut_out"),
                    "source_server_path": Path(
                        source_task.server_path, source_file_name.name
                    ),
                }

    def create_shot(self, shot_data: dict[str, Any], task_name: Optional[str] = None) -> dict[str, Any]:
        """
        Create or update a Shot entity and upload an associated version if applicable.

        Args:
            shot_data (dict[str, Any]): Dictionary with shot data.
            task_name (Optional[str]): Optional name of the task for thumbnail association.

        Returns:
            dict[str, Any]: The created or updated Shot entity.
        """
        sg_shot_data = {
            "sg_status_list": shot_data.get("new_status"),
            "sg_cut_duration": shot_data.get("new_duration"),
            "sg_cut_in": shot_data.get("new_start"),
            "sg_cut_out": shot_data.get("new_end"),
        }

        if shot_data.get("shot_missing", False):
            logger.info("Missing shot in sg. Creating shot")
            shot = self.sg.create(
                "Shot",
                {
                    "code": shot_data.get("shot_name"),
                    "task_template": {
                        "type": "TaskTemplate",
                        "id": self._shot_task_tpl_id,
                    },
                    "project": {"id": int(self.SG_PROJECT_ID), "type": "Project"},
                    "sg_sequence": shot_data.get("sequence_entity"),
                    **sg_shot_data,
                },
                return_fields=["code", "sg_sequence"],
            )
        else:
            logger.info("Publishing version..")
            shot = self.sg.update("Shot", shot_data["shot_entity"]["id"], sg_shot_data)

        if shot_data.get("video_file") is None:
            return shot

        task_entity = self.sg.find_one(
            "Task",
            [
                ["entity", "is", shot],
                ["content", "is", self._edl_target_task],
            ],
            ["entity", "content"],
        )
        clip_file = Path(shot_data.get("video_file"))

        self.last_file_clicked = clip_file
        self.last_task_clicked = BaseTask(
            name=task_name,
            link_name=clip_file.name,
            local_path=Path(),
            prev_task_server=Path(),
            thumbnail=None,
            data_to_show=list(),
        )  # TODO:TEMPORAL PARA PODER ASIGNAR EL _UPLOAD_STATUS CORRECTO EN EL PROYECTO ANNIECAROLA
        task_entity
        version_data = {
            "project": {"id": int(self.SG_PROJECT_ID), "type": "Project"},
            "code": clip_file.name,
            "description": "Automatic upload of edl",
            "sg_status_list": self._upload_status,
            "sg_uploader": self.username,
            "sg_task": {"id": task_entity["id"], "type": "Task"},
            "entity": task_entity["entity"],
        }

        if not (
            version := self.sg.find_one(
                "Version",
                [["sg_task", "is", task_entity], ["code", "is", clip_file.name]],
            )
        ):
            logger.info("Creating version..")
            version = self.sg.create("Version", version_data)

        logger.info("Uploading version...")
        logger.info(
            f"ID: {version['id']}\n{fspath(clip_file)}\n{clip_file.name}\n#################"
        )
        self.sg.upload(
            "Version",
            version["id"],
            path=fspath(clip_file),
            field_name="sg_uploaded_movie",
            display_name=clip_file.name,
        )
        logger.info("version uploaded successfully...")

        return shot

    def create_pack(self, pack_type: str, ep: str) -> Generator[str, None, None]:
        """
        Looks for versions that matches the data passed as args,
        and adds them to a given folder.

        Args:
            pack_type (str): Type of pack to create.
            ep (str): Episode identifier.

        Yields:
            str: Names of copied files.
        """
        status, get_folder_lambda, by_task, tasks_filter = self.packtype_to_status[
            pack_type
        ]
        folder = get_folder_lambda()
        yield folder
        p = Path(self._server_root, folder, ep)
        p.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Destination file: '{fspath(p)}'")
        # print(ep, status, int(self.SG_PROJECT_ID))
        ep_entity = self.return_all_episodes().get(ep)

        fields = [
            "code",
            "entity.Asset.sg_2d_asset_type",
            "sg_path_to_jpg_file",
            "sg_uploaded_movie",
            "entity.Asset.code",
            "sg_task.Task.content",
            "sg_task.Task.step.Step.code",
            "sg_task.Task.entity.Asset.task_template.TaskTemplate.sg_asset_type",
        ]

        if by_task:
            versions: list[dict] = list()
            logger.debug("Working on a per task basis.")
            tasks: list[dict] = self.sg.find(
                "Task",
                [
                    (
                        ["entity.Asset.sg_created_for_episode.Episode.code", "is", ep]
                        if self.TITLE != "Annie&Carola"
                        else ["entity.Asset.episodes", "is", ep_entity]
                    ),
                    ["sg_status_list", "in", status],
                    ["project.Project.id", "is", int(self.SG_PROJECT_ID)],
                ],
                ["content", "entity.Asset.code"],
            )
            for task in tasks:
                logger.debug(
                    f"Fetching versions for task \"{task.get('content')}\" @ asset \"{task.get('entity.Asset.code')}\""
                )
                last_version = self.return_last_version(task.get("id"))

                if last_version is None:
                    continue

                last_version_number = return_version_number_from_string(
                    self.version_regex, last_version.get("code")
                )
                versions += self.sg.find(
                    "Version",
                    [
                        (
                            [
                                "entity.Asset.sg_created_for_episode.Episode.code",
                                "is",
                                ep,
                            ]
                            if self.TITLE != "Annie&Carola"
                            else ["entity.Asset.episodes", "is", ep_entity]
                        ),
                        ["sg_task.Task.id", "is", task.get("id")],
                        ["code", "contains", last_version_number],
                        ["sg_status_list", "in", status],
                        ["project.Project.id", "is", int(self.SG_PROJECT_ID)],
                    ],
                    fields,
                )
        else:
            versions: list[dict] = self.sg.find(
                "Version",
                [
                    (
                        ["entity.Asset.sg_created_for_episode.Episode.code", "is", ep]
                        if self.TITLE != "Annie&Carola"
                        else ["entity.Asset.episodes", "is", ep_entity]
                    ),
                    ["sg_status_list", "in", status],
                    ["project.Project.id", "is", int(self.SG_PROJECT_ID)],
                ]
                + tasks_filter,
                fields,
            )

        summary_file = Path(p, "summary.csv")
        with open(summary_file, "w") as ftw:
            ...
        for version in versions:
            # f = Path(version["sg_path_to_jpg_file"])
            logger.debug(f"Working on \"{version.get('code')}\"")

            local_path, server_path = self.get_task_filesystem(
                version.get("entity.Asset.code"),
                "Asset",
                version.get("sg_task.Task.content"),
                asset_type=version.get("entity.Asset.sg_2d_asset_type")
                or version.get(
                    "sg_task.Task.entity.Asset.task_template.TaskTemplate.sg_asset_type"
                ),
                step=version.get("sg_task.Task.step.Step.code"),
            )

            # f = list(Path(server_path).glob("/**/" + version.get('code')))[0]
            # print(fspath(Path(server_path)) + "/**/" + version.get("code"))
            # f = Path([f for f in glob(fspath(Path(server_path)) + "/**/" + version.get('code'), recursive=True)][0])

            version_name = Path(version.get("code")).name
            # version_name_psd = Path(version.get('code')).stem + "*.psd"
            # version_name_psb = Path(version.get('code')).stem + "*.psb"

            # print(version_name, version_name_psd, version_name_psb)

            f = next(
                Path(server_path).rglob(f"*{version_name}"),
                Path(server_path, self._preview_location or "", version_name),
            )

            logger.debug(f'Server path is "{server_path}"')

            # fpsd = next(Path(server_path).rglob(f"*{version_name_psd}"), None)
            # fpsb = next(Path(server_path).rglob(f"*{version_name_psb}"), None)
            fpsd, fpsb = None, None
            for psd in Path(server_path).rglob("*.psd"):
                if psd.stem in version_name:
                    fpsd = psd

            for psb in Path(server_path).rglob("*.psb"):
                if psb.stem in version_name:
                    fpsb = psb

            logger.debug(f'Server path for PSB is is "{fpsb}"')
            logger.debug(f'Server path for PSD is is "{fpsd}"')
            # fpsd = Path(fspath(f).replace(f.suffix, ".psd"))
            # fpsb = Path(fspath(f).replace(f.suffix, ".psb"))

            if not f.exists():
                self.sg.download_attachment(version["sg_uploaded_movie"], file_path=f)
                logger.debug(
                    "File didn't exist in the server, it was downloaded form SG."
                )

            if not Path(p, f.name).exists():
                copy2(f, Path(p, f.name))
                yield f.name

            if fpsd is not None and fpsd.exists() and not Path(p, fpsd.name).exists():
                copy2(fpsd, Path(p, fpsd.name))
                yield fpsd.name

            if fpsb is not None and fpsb.exists() and not Path(p, fpsb.name).exists():
                copy2(fpsb, Path(p, fpsb.name))
                yield fpsb.name

        for file_to_log in p.glob("*.*"):
            with open(summary_file, "a") as ftw:
                if file_to_log.exists():
                    ftw.write(f"{file_to_log.name}\n")

    def create_pack_from_dialog(self, p: Path, versions: list[dict[str, Any]], extensions: list[str]) -> Generator[str, None, None]:
        """
        Pack selected version files based on user-selected filters.

        Args:
            p (Path): Target folder path for the pack.
            versions (list[dict[str, Any]]): List of version dictionaries to pack.
            extensions (list[str]): File extensions to include.

        Yields:
            str: File names of the packed assets.
        """
        summary_file = Path(p, "summary.csv")
        with open(summary_file, "w") as ftw:
            ...
        for version in versions:
            # f = Path(version["sg_path_to_jpg_file"])
            logger.debug(f"Working on \"{version.get('code')}\"")

            local_path, server_path = self.get_task_filesystem(
                version.get("entity.Asset.code"),
                "Asset",
                version.get("sg_task.Task.content"),
                asset_type=version.get("entity.Asset.sg_2d_asset_type")
                or version.get(
                    "sg_task.Task.entity.Asset.task_template.TaskTemplate.sg_asset_type"
                ),
                step=version.get("sg_task.Task.step.Step.code"),
            )

            version_name = Path(version.get("code")).name

            f = next(
                Path(server_path).rglob(f"*{version_name}"),
                Path(server_path, self._preview_location or "", version_name),
            )

            logger.debug(f'Server path is "{server_path}"')
            logger.debug(f"File is '{f}'")
            # files_to_add: dict[str, Path] = dict()

            for ext in set(extensions + [Path(version.get("code")).suffix[1:]]):
                file = next(
                    (
                        f_
                        for f_ in Path(server_path).rglob(f"*.{ext}")
                        if Path(version_name).stem in f_.stem
                    ),
                    None,
                )
                print(file)
                if (
                    file is not None
                    and file.exists()
                    and not Path(p, file.name).exists()
                    and file.name not in self.return_filepack_exceptions()
                ):
                    copy2(file, Path(p, file.name))
                    logger.debug(file)
                    yield file.name

        for file_to_log in p.glob("*.*"):
            with open(summary_file, "a") as ftw:
                if file_to_log.exists():
                    ftw.write(f"{file_to_log.name}\n")

    def update_asset_task_fields_with_task_entities(self, additional_filters: Optional[list[Any]] = None) -> None:
        """
        Update asset task fields based on associated ShotGrid task entities.

        Args:
            additional_filters (Optional[list[Any]]): Additional filters for the ShotGrid query.
        """
        if self.asset_task_fields_dict is None:
            return

        # for each entity type: Asset, Shot, Episode, Sequence etc.
        for entity_type, values in self.asset_task_fields_dict.items():
            # for each type of task in each entity
            for task_name, field_name in values.items():
                f = [
                    ["entity", "is_not", None],
                    [
                        f"entity.{entity_type}.task_template.TaskTemplate.entity_type",
                        "is",
                        entity_type,
                    ],
                    [f"entity.{entity_type}.{field_name}", "is", None],
                ]
                filters = f if additional_filters is None else additional_filters + f

                # get all tasks for each entity type and task name
                # TODO: this loop may be optimizable... as we can get all tasks
                # by Entity instead of by Entity and task name
                # but we are getting only the ones with the missing field anyway
                for task_entity in self.sg.find(
                    "Task",
                    filters + [["content", "is", task_name]],
                    [f"entity.{entity_type}.{field_name}", "entity"],
                ):
                    try:
                        self.sg.update(
                            entity_type,
                            task_entity["entity"]["id"],
                            {field_name: task_entity},
                        )
                        logger.info(
                            f"Updated {entity_type} number {task_entity['entity']['id']}'s field {field_name}"
                        )
                    except Exception as e:
                        logger.exception(e)

    def create_note(
        self,
        links: list[Any] = [],
        status: str = "opn",
        body: str = "",
        subject: str = "",
        tasks: list[BaseTask] = [],
        to: list[Any] = [],
        author: dict[str, Any] = {},
        **kwargs,
    ) -> None:
        """
        Create a new Note entity in ShotGrid.

        Args:
            links (list[Any]): List of linked entities.
            status (str): Note status.
            body (str): Body content.
            subject (str): Subject line.
            tasks (list[Any]): Associated task entities.
            to (list[Any]): Users addressed in the note.
            author (dict[str, Any]): User entity of the note author.
            **kwargs: Additional ShotGrid fields.
        """
        data = {
            "note_links": [link for link in links if link != None],
            "sg_status_list": status,
            "content": body,
            "project": {"id": self.SG_PROJECT_ID, "type": "Project"},
            "subject": subject,
            "tasks": tasks,
            "addressings_to": to,
            "user": author,
        }

        data.update(kwargs)

        self.sg.create("Note", data)

    def return_my_tasks_filter(self) -> list[list[Any]]:
        """
        Return filters for querying tasks assigned to the currently logged-in user.

        Returns:
            list[list[Any]]: ShotGrid filter for user's tasks.
        """
        with ShotgridInstance(self) as sg:
            artist_entity = sg.find_one(
                self.custom_artist_entity_name,
                [
                    [self.custom_artist_login_field, "is", self.username],
                    ["project.Project.id", "is", int(self.SG_PROJECT_ID)],
                ],
            )

        if artist_entity is None:
            logger.warning(
                f"Failed to find a custom artist entity for the username '{self.username}'."
            )

        my_tasks_filter = [[self.custom_artist_task_field, "is", artist_entity]]
        return my_tasks_filter


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    plugin = ShotgridPlugin()
