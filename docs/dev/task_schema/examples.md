# **Developing a Custom Production Plugin**

This guide walks you through the process of creating a custom production plugin for the GwaIO ecosystem. Plugins are essential for tailoring GwaIO to your specific pipeline needs, integrating with production tracking systems, and defining project-specific workflows.

In this example, we will focus on building a plugin based on the `ShotgridPlugin` class. This provides a robust foundation by leveraging the pre-existing logic for communication between GwaIO and Autodesk ShotGrid.

## **Prerequisites**

Before you begin, ensure you have the following set up in your development environment:

* **GwaIO Repositories**: You must have the core GwaIO repositories installed or accessible in your `PYTHONPATH`:
    * `launcher`
    * `task_schema`
    * `utilities`
    * `publisher`
* **Python Version**: GwaIO requires `Python 3.10.14`. Please ensure you have this specific version installed and active.

!!! info
    This guide assumes a basic understanding of Python programming and familiarity with both the GwaIO ecosystem and Autodesk ShotGrid concepts.

## 1. **Create Your Plugin File** 📝

The first step is to create a Python file that will contain your plugin's code. For this guide, we will name our file `production_plugin.py`.

According to the GwaIO structure, this file should be placed within the `plugins` directory of the `task_schema` repository.

**Path:** `task_schema/plugins/production_plugin.py`

**Filename:** `production_plugin.py`

!!! note
    While the example suggests this specific path, you might have a different or centralized location for custom plugins in your studio's GwaIO deployment. Ensure the GwaIO `launcher` can discover and load your plugin from its location.

## 2. **Define Necessary Imports**

At the very beginning of your `production_plugin.py` file, add all the necessary import statements. These will bring in the core GwaIO classes your plugin will extend or interact with, along with any standard Python libraries, UI elements, publisher components, or custom utilities your specific workflow requires.

```python
# production_plugin.py
from pathlib import Path
from typing import Iterable
import traceback
from shutil import copy2
from os import remove, fspath
import pandas
from difflib import SequenceMatcher as smatch
from re import sub

# --- GwaIO Core Imports ---
# Import the base classes. We inherit from ShotgridPlugin, 
# BaseTask represents a task in GwaIO.
from task_schema.plugins.shotgrid_plugin import ShotgridPlugin, BaseTask 

# --- Optional UI Imports ---
# Import UI elements like custom toolbars if your plugin adds them.
from launcher.qtclasses.toolbar_maya import MayaToolbar 

# --- Optional Publisher Imports ---
# Import base classes if you're integrating with the GwaIO Publisher framework.
# Replace with your actual Collect/Push classes.
from publisher.core import Collect, Push 

# --- Optional Utility Imports ---
# Import any helper scripts or batch processes your plugin might use.
from utilities.maya.scripts import (
    batch_playblast,
    batch_turntable,
)
```

!!! tip "Adapt Your Imports"
The imports shown above are based on the example plugin. You should tailor this section to include only what your specific plugin needs. If you aren't using Maya toolbars or specific publisher classes, you won't need those imports. Conversely, if you're working with Nuke or Houdini, you might import their respective toolbars or utilities.

## 3. **Plugin Class Definition**

Next, define your plugin class. In our example, we're creating `ProductionPlugin` which inherits from `ShotgridPlugin`. If you're not integrating with ShotGrid, you might inherit from `BasePlugin` directly.

Key class-level attributes to set initially include:

* `title`: A human-readable name for your plugin, often used in UIs.
* `SG_PROJECT_ID` (if using `ShotgridPlugin`): The numerical ID of your ShotGrid project.
* `SHOTGRID_URL` (if using `ShotgridPlugin`): The base URL of your ShotGrid instance.

The `__init__` method is where you'll initialize instance variables and configure the plugin's behavior. This is the primary area for setting up all necessary variables for the plugin and its associated tools to function correctly.

!!! tip "Review Base Class Documentation"
    You can review the default configuration variables used in `BasePlugin` and `ShotgridPlugin` by referring to their respective documentation (we can add links here later if available, e.g., `[BasePlugin](path/to/base_plugin_doc.md)` and `[ShotgridPlugin](path/to/shotgrid_plugin_doc.md)`).



```python
class ProductionPlugin(ShotgridPlugin):
    title = "Production Project"  # A descriptive title for UI purposes
    SG_PROJECT_ID = 999  # Example ShotGrid Project ID
    SHOTGRID_URL = "https://yourstudio.shotgunstudio.com"  # Your ShotGrid instance URL

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ----------------------------------------------------------------------
        # GwaIO Launcher Configuration
        # ----------------------------------------------------------------------
        # Defines GwaIO Launcher behavior, UI elements, and available actions.

        # Default entity types and filters to apply when the plugin loads in the launcher.
        self._active_entities = ["My Tasks", "Asset", "Sequence", "Episode", "Shot"]
        
        # List of custom job functions/classes available through the launcher UI.
        # These are typically batch processes or automated tasks.
        self._jobs += [
            batch_playblast,
            batch_turntable,
        ]
        
        # Define custom toolbars to be added to the launcher UI for this plugin.
        # Each item is a list: [ToolbarClass, "Display Name", "Placement (e.g., 'right')"]
        self._toolbars += [
            [MayaToolbar, "Maya Toolbar", "right"],
        ]
        
        # Default entity type and filters to apply when adding tasks to the view (e.g. "My Tasks" view).
        self.add_tasks_from_plugin_kwargs = {"sg_entity_type": "My Tasks"}
        
        # File extensions offered in the "Create File" dialog.
        # "from selected" implies using the current task context for creation.
        self.create_file_ext = ["from selected", "psd", "ma", "spp", "xlsx"]
        
        # Flag indicating if the project uses a render farm like Deadline.
        self.uses_deadline = True

        # ----------------------------------------------------------------------
        # ShotGrid Integration Configuration
        # ----------------------------------------------------------------------
        # Settings specific to how GwaIO interacts with ShotGrid.

        # --- ShotGrid Custom Artist Entity Configuration ---
        # Maps launcher users to a specific Artist entity in ShotGrid.
        # Field on your Artist Custom Entity in SG that matches the launcher username.
        self.custom_artist_entity_name = "CustomEntity04" 
        self.custom_artist_login_field = "code" # Login field on the custom artist entity.
        
        # Fields on various ShotGrid entities that link back to your Artist Custom Entity.
        self.publishedfile_artist_entity_field = "sg_mondo_artist"  # On PublishedFile
        self.timelog_artist_entity_field = "sg_mondo_artist"       # On TimeLog
        self.version_artist_entity_field = "sg_mondo_artist"       # On Version
        self.custom_artist_task_field = "sg_mondo_artist"          # On Task (for assignments)
        
        # Extend or refine the default ShotGrid task filters.
        # These filters apply when fetching tasks from ShotGrid.
        self.plugin_task_filters += [
            ["sg_status_list", "not_in", ["na", "wtg"]],
            ["entity.Asset.sg_status_list", "not_in", ["na"]],
        ]
        
        # Default ShotGrid status to assign to newly uploaded Versions (e.g., "rev" for "Pending Review").
        self._upload_status = "rev"

        # ----------------------------------------------------------------------
        # File System Configuration
        # ----------------------------------------------------------------------
        # Defines project paths, naming conventions, and template locations.

        # Local root path for the project. Reads "PRODUCTION_LOCAL_PATH" environment variable.
        self._local_root = Path(self.env_handler.get_env("PRODUCTION_LOCAL_PATH"))
        
        # Server root path for the project. Reads "PRODUCTION_SERVER_PATH" env var, or uses a hardcoded path.
        self._server_root = Path(
            self.env_handler.get_env(
                "PRODUCTION_SERVER_PATH",
                # Default hardcoded path if environment variable is not set
                Path("\\\\qsrv01.mondotvcanarias.lan\\proj_production\\Production") 
            )
        )
        
        # Path to project file templates.
        self.TEMPLATES_FOLDER = Path(self._server_root, "production/publish/templates")
        
        # Path to a studio library (e.g., animation library).
        self.SL_SERVER_PATH = Path(self._server_root, "production/publish/library/anim_lib")

        # Relative path within a task's local directory where previews (thumbnails, playblasts) are stored.
        # If Path(), previews are at the root of the task's local_path.
        self._preview_location = Path() 
        
        # If True, the entity's code (e.g., asset/shot name) must be part of the versioned filename.
        self._version_includes_entity = True
        
        # Regex to extract version numbers from filenames (e.g., gets '001' from 'file_w001.ma').
        self.version_regex = r"(?<=_[wv])\d{3}" 
        
        # List of regex patterns to validate filenames against project conventions.
        # "prd" is an example prefix; adapt these to your project's specific naming scheme.
        self._naming_regex = [
            r"^prd_[a-z]{2}_[A-Za-z0-9]+_[A-Za-z0-9]+_[a-z]+_[wv]\d{3}.*",
            r"^prd(_\d{3})_([a-z]+)_[wv]\d{3}.*",
            r"^prd(_\d{3}){2}_([a-z]+)_[wv]\d{3}.*",
            r"^prd(_\d{3}){3}_([a-z]+)_[wv]\d{3}.*",
            r"^prd(_\d{3}){3}(_[a-z]+){1,3}_[wv]\d{3}.*",
        ]
        # Regular expression to validate BDL (Bill of Data List) filenames.
        self.bdlregex = r"prd_(\d{3}_|[a-zA-Z]{2}_([a-zA-Z09]*._){2})bd[lw]_[vw]\d{3}\.xlsx"
        
        # Base path for asset work directories.
        # Note: fspath is from 'os' module, ensure it's imported if you use it.
        self._asset_folder = fspath(self.local_root) + "/PROD/assets/work"
        
        # Regex to help an asset browser find asset work folders.
        self._asset_folder_regex = fspath(self.local_root) + "/PROD/assets/work/*/*/*"
        
        # Provides default template files. Used by methods like return_next_version_name.
        self._dict_file_templates = {
            "bdl": Path(self.TEMPLATES_FOLDER, "prd_template_bdl.xlsx"),
            "bdw": Path(self.TEMPLATES_FOLDER, "prd_template_bdl.xlsx"),
            "skt": Path(self.TEMPLATES_FOLDER, "prd_template_psd.psd"),
        }

        # ----------------------------------------------------------------------
        # DCC Application Configuration
        # ----------------------------------------------------------------------
        # Settings related to Digital Content Creation (DCC) applications.

        # Paths to shared custom scripts, plugins, or shelves for DCCs.
        # These are often added to environment variables in `generate_environment_for_app()`.
        self.CUSTOM_MAYA_TOOLS = Path(self.server_root, "pipeline/publish/dev/maya")
        self.CUSTOM_NUKE_TOOLS = Path(self.server_root, "pipeline/publish/dev/nuke")

        # ----------------------------------------------------------------------
        # Project-Specific Configuration
        # ----------------------------------------------------------------------
        # General project settings like frame rates and task dependencies.

        self._fps = 25  # Frames per second for the project.
        self._starting_frame = 101  # Default start frame for animation, playblasts, etc.
        
        # --- Previous Task Mapping ---
        # Defines dependencies: maps a current task name to its typical upstream task.
        # Used to find outputs from previous steps (e.g., model from blocking for rigging).
        # Key: current task's long SG name. Value: dict {task_name: prev_task_long_SG_name, step: prev_task_SG_Step_code}.
        self._dict_previous_tasks = {
            "line": {"task": "sketch", "step": "ConceptArtStep"},
            "color": {"task": "line", "step": "ConceptArtStep"},
            "model": {"task": "blocking", "step": "ModelingStep"},
            "uvs": {"task": "model", "step": "ModelingStep"},
        }

        # ----------------------------------------------------------------------
        # EDL (Edit Decision List) Configuration
        # ----------------------------------------------------------------------
        # Settings for EDL processing workflows.

        self._edl_target_task = "animatic"  # Default SG Task name for EDL processing.
        self._edl_task_name = "EDL" # Name of the EDL task itself.
        self._edl_shot_prefix = "" # Prefix for shot names extracted from EDL.
        self._edl_sequence_prefix = "" # Prefix for sequence names.
        self._edl_episode_prefix = "plt_" # Prefix for episode names.
        self.edl_sequence_regex = compile(r"(?<=plt_)\d{3}_\d{3}") # Regex to parse sequence codes.
        self._edl_shot_regex = compile(r"(?<=plt_)\d{3}_\d{3}_\d{3}") # Regex to parse shot codes.
        self.edl_version_regex = compile(r"(?<=_[VvWw])\d{3}") # Regex for version numbers in EDL context.
        self._shot_task_tpl_id = 1069 # ShotGrid Task Template ID for EDL-created tasks.
        self._episode_edl_workflow = True # Flag to enable episode-based EDL workflow.
        self._edl_episode_regex = compile(r"plt_\d{3}") # Regex to parse episode codes.
        
        # ----------------------------------------------------------------------
        # Publisher Framework Configuration
        # ----------------------------------------------------------------------
        # Defines how the GwaIO Publisher Framework interacts with this plugin.

        # Configures the publisher UI by mapping task types (ShotGrid task names) 
        # to sets of Collector and Pusher classes from the Publisher framework.
        self.publisher_builder_data = {
            "line": {  # Example for a 'line' task
                CollectTask,
                CollectFileConcept,
                CollectPreview,
                CollectBID,
                CollectDescription,
                PushSG,
            },
            "color": { # Example for a 'color' task
                CollectTask,
                CollectFileConcept,
                CollectPreview,
                CollectBID,
                CollectDescription,
                PushSG,
            },
            "sbRough": { # Example for a 'storyboard rough' task
                CollectTask,
                CollectFileVideo,
                CollectPreviewVideo,
                CollectBID,
                PushSG,
            },
            "model": { # Example for a 'model' task
                CollectTask,
                CollectFileVideo, # Assuming 3D model tasks might also have video reviews (e.g. turntables)
                CollectPreviewVideo,
                CollectBID, # Business ID or other metadata collection
                PushSG, # Pushes data to ShotGrid
            },
        }
```
!!! info "Explore Base Classes"
    Many default configurations and methods are inherited. Refer to the documentation for [BasePlugin](url) and [ShotgridPlugin](url) to understand all available options and their default behaviors.

### 3.1 **GwaIO Configuration**

This section details the configuration variables that impact the GwaIO interface, allowing for the integration of custom toolbars and jobs within your personalized plugin.

* **Custom Toolbars**: You can integrate DCC (Digital Content Creation) application-specific toolbars, such as `MayaToolbar` (potentially provided by `launcher.qtclasses.toolbar_maya`) or your own custom toolbar classes, by adding them to the `self._toolbars` list within your plugin's `__init__` method. These toolbars will appear in the GwaIO launcher UI, providing buttons and actions that are contextual to the selected task and the integrated DCC application.

To learn more about creating custom toolbars, refer to the `BaseToolbars` documentation.

* **Custom Jobs**: For pipeline batch processes, such as playblasting, rendering via Deadline, or executing QA scripts using `mayapy`, you can define these as Python functions or classes. These callable jobs should then be listed in the `self._jobs` list during your plugin's `__init__` method. The GwaIO launcher application will then provide a user interface to select and trigger these jobs, often passing the current task context to them.

The following imports are necessary for integrating custom toolbars and jobs:

```python
from launcher.qtclasses.toolbar_maya import MayaToolbar # Optional: UI elements like toolbars
from utilities.maya.scripts import (
    batch_playblast,
    batch_turntable,
) # Optional: Utilities

Estas serían las variables del ejemplo
```py
        ...
        super().__init__(*args, **kwargs)
        
        ################
        # GwaIO Config #
        ################
        
        self._active_entities = ["My Tasks", "Asset", "Sequence", "Episode", "Shot"] # Default entity type and filters to apply when the plugin loads in the launcher. 
        self._jobs += [
            batch_playblast,
            batch_turntable,
        ]
        # Define custom toolbars to be added to the launcher UI for this plugin.  
        # Each item is a list: [ToolbarClass, "Display Name", "Placement (e.g., 'right')"]
        self._toolbars += [
            [MayaToolbar, "Maya Toolbar", "right"],
        ]
        self.add_tasks_from_plugin_kwargs = {"sg_entity_type": "My Tasks"} # Default entity type and filters to apply when the plugin loads in the launcher. 
        self.create_file_ext = ["from selected", "psd", "ma", "spp", "xlsx"] # File extensions offered in the "Create File" dialog. "from selected" implies using the current task context. 
        self.uses_deadline = True # Flag indicating if the project uses a render farm like Deadline. 

```

### 3.2 **Shotgrid Config**

This section fine-tunes the interaction with ShotGrid.

* **Custom Artist Entity**: If you use a custom entity in ShotGrid to represent artists/users (instead of the standard HumanUser), these variables (`custom_artist_entity_name`, `custom_artist_login_field`, etc.) map GwaIO users to that entity for tasks, versions, and timelogs.
* `plugin_task_filters`: Allows you to add more filters to the ones already defined in `ShotgridPlugin`. These are used when fetching tasks from ShotGrid, helping to narrow down the list shown to users (e.g., hiding tasks with 'N/A' or 'Waiting to Start' statuses).
* `_upload_status`: Sets the default ShotGrid status (e.g., 'rev' for 'Pending Review') that will be assigned to new Version entities created by GwaIO.

```py
        ...

        #############
        # SG Config #
        #############

        # --- ShotGrid Custom Artist Entity Configuration ---  
        # Defines how launcher users are mapped to your specific Artist entity in ShotGrid.  
        self.custom_artist_entity_name = "CustomEntity04"  # Field on your Artist Custom Entity in SG that matches the launcher username.
        self.custom_artist_login_field = "code"
        # Fields on various ShotGrid entities that link back to your Artist Custom Entity.
        self.publishedfile_artist_entity_field = "sg_mondo_artist" # On PublishedFile  
        self.timelog_artist_entity_field = "sg_mondo_artist"       # On TimeLog  
        self.version_artist_entity_field = "sg_mondo_artist"       # On Version  
        self.custom_artist_task_field = "sg_mondo_artist"          # On Task (for assignments)
        # Extend or refine the default ShotGrid task filters inherited from ShotgridPlugin.  
        # These filters apply when fetching tasks from ShotGrid.  
        self.plugin_task_filters += [
            ["sg_status_list", "not_in", ["na", "wtg"]],
            ["entity.Asset.sg_status_list", "not_in", ["na"]],
        ]
        # Default ShotGrid status to assign to newly uploaded Versions (e.g., "rev" for "Pending Review").  
        self._upload_status = "rev"

        ...

```


!!! tip "Custom ShotGrid Scripts"
    If you need to use different or custom scripts for managing ShotGrid interactions (beyond what [`ShotgridPlugin`]() provides), explore its methods and override them. You can also define specific `sg_` attributes to point to your custom ShotGrid API handlers if needed.


### 3.3 **File System Configuration**

This section defines how GwaIO understands and interacts with your project's directory structure and naming conventions.

* `_local_root` / `_server_root`: Defines the base paths for local work and server-side storage. Using `self.env_handler.get_env()` is recommended, allowing flexibility through environment variables with sensible fallbacks.
* `TEMPLATES_FOLDER` / `SL_SERVER_PATH`: Paths to specific shared resources like file templates or studio libraries.
* `_preview_location`: Specifies a sub-folder within a task's directory for storing previews. An empty `Path()` means previews go to the task's root.
* `version_regex` / `_naming_regex` / `bdlregex`: Regular expressions are crucial for GwaIO to parse version numbers from filenames and to validate that filenames adhere to your studio's naming conventions.
* `_asset_folder` / `_asset_folder_regex`: Helps tools like the asset browser locate asset work directories efficiently.
* `_dict_file_templates`: Maps short task names (or other keys) to specific template files. This is used by `return_next_version_name` when creating the very first version of a file for a task.


```py
        ...
        ######################
        # File System Config #
        ######################

        # Set the local root path for the project.  
        # Reads "PRODUCTION_LOCAL_PATH" env var
        self._local_root = Path(self.env_handler.get_env("PRODUCTION_LOCAL_PATH"))
         # Set the server root path for the project.  
        # Reads "PRODUCTION_SERVER_PATH" env var, or uses hardcode path
        self._server_root = Path(
            self.env_handler.get_env(
                "PRODUCTION_SERVER_PATH",
                Path(
                    "\\\\qsrv01.mondotvcanarias.lan\\proj_production\\Production"
                ),
            )
        )
        self.TEMPLATES_FOLDER = Path(self._server_root, "production/publish/templates") # Path to project file templates. 
        self.SL_SERVER_PATH = Path(self._server_root, "production/publish/library/anim_lib") # Path to a studio library. 

        # Relative path within a task's local directory where previews (e.g., thumbnails, playblasts) are stored.  
        # If Path(), previews are at the root of the task's local_path.  
        self._preview_location = Path()
        # If True, the entity's code (e.g., asset/shot name) must be part of the versioned filename. 
        self._version_includes_entity = True
        # Regex to extract version numbers from filenames (e.g., gets '001' from 'file_w001.ma'). 
        self.version_regex = r"(?<=_[wv])\d\d\d"
        # List of regex patterns to validate filenames against project conventions.  
        # "prd" is an example prefix; adapt these to your project's specific naming scheme. 
        self._naming_regex = [
            r"^prd_[a-z]{2}_[A-Za-z0-9]+_[A-Za-z0-9]+_[a-z]+_[wv]\d\d\d.*",
            r"^prd(_\d\d\d)_([a-z]+)_[wv]\d\d\d.*",
            r"^prd(_\d\d\d){2}_([a-z]+)_[wv]\d\d\d.*",
            r"^prd(_\d\d\d){3}_([a-z]+)_[wv]\d\d\d.*",
            r"^prd(_\d\d\d){3}(_[a-z]+){1,3}_[wv]\d\d\d.*",
        ]
        # Regular expression to validate BDL (Bill of Data List) filenames.
        self.bdlregex = r"prd_(\d\d\d_|[a-zA-Z]{2}_([a-zA-Z09]*._){2})bd[lw]_[vw]\d\d\d\.xlsx"
        # Base path for asset work directories.
        self._asset_folder = fspath(self.local_root) + "/PROD/assets/work"
        # Regex to help an asset browser find asset work folders. 
        self._asset_folder_regex = fspath(self.local_root) + "/PROD/assets/work/*/*/*"
        
        # Provides default template files. Used by return_next_version_name.
        self._dict_file_templates = {
            "bdl": Path(self.TEMPLATES_FOLDER, "prd_template_bdl.xlsx"),
            "bdw": Path(self.TEMPLATES_FOLDER, "prd_template_bdl.xlsx"),
            "skt": Path(self.TEMPLATES_FOLDER, "prd_template_psd.psd"),
        }
```

!!! tip "Hard-Coded vs. Environment Variables"
While you can hard-code paths, using environment variables via self.env_handler is generally more flexible and maintainable, especially in larger studios or when managing multiple projects.

### 3.4 **DCC Config**

This section allows you to specify paths to custom tools, scripts, or shelves for Digital Content Creation (DCC) applications like Maya or Nuke. These paths are often used later (e.g., in `generate_environment_for_app()`) to set up the environment before launching a DCC.

```py
        ...
        ##############
        # DCC Config #
        ##############

        # Paths to shared custom scripts, plugins, or shelves for DCC applications.  
        # These are often added to environment variables in generate_environment_for_app().  
        self.CUSTOM_MAYA_TOOLS = Path(self.server_root, "pipeline/publish/dev/maya")
        self.CUSTOM_NUKE_TOOLS = Path(self.server_root, "pipeline/publish/dev/nuke")

        ...

```

### 3.5 **Project Configuration**

This section holds project-wide settings.

* `_fps` / `_starting_frame`: Defines basic project standards like frames per second and the default starting frame number for new scenes.
* `_dict_previous_tasks`: A vital mapping that defines task dependencies. It tells GwaIO, for a given task (e.g., 'uvs'), which task and step (e.g., 'model' from 'ModelingStep') typically come before it. This is used to easily find upstream published files.

```py
        ...
        
        ##################
        # Project Config #
        ##################
        
        self._fps = 25 # Frames per second for the project.  
        self._starting_frame = 101 # Default start frame for animation, playblasts, etc.
        # --- Previous Task Mapping ---  
        # Defines dependencies: maps a current task name to its typical upstream task.  
        # Used to find outputs from previous steps (e.g., model from blocking for rigging).  
        # Key: current task's long SG name. Value: dict {task_name: prev_task_long_SG_name, step: prev_task_SG_Step_code}.  
        self._dict_previous_tasks = {
            "line": {"task": "sketch", "step": "ConceptArtStep"},
            "color": {"task": "line", "step": "ConceptArtStep"},
            "model": {"task": "blocking", "step": "ModelingStep"},
            "uvs": {"task": "model", "step": "ModelingStep"},
        }
        ...

```


### 3.6 **EDL Configuration**

If your workflow involves processing Edit Decision Lists (EDLs), these variables configure how GwaIO should parse them, identify shots/sequences/episodes, and interact with ShotGrid during EDL-based operations.

```py
        ...
        
        ##############
        # EDL Config #
        ##############

        self._edl_target_task = "animatic" # Default SG Task name for EDL processing
        self._edl_task_name = "EDL"
        self._edl_shot_prefix = ""
        self._edl_sequence_prefix = ""
        self._edl_episode_prefix = "plt_"
        self.edl_sequence_regex = compile(r"(?<=plt_)\d{3}_\d{3}")
        self._edl_shot_regex = compile(r"(?<=plt_)\d{3}_\d{3}_\d{3}")
        self.edl_version_regex = compile(r"(?<=_[VvWw])\d\d\d")
        self._shot_task_tpl_id = 1069
        self._episode_edl_workflow = True
        self._edl_episode_regex = compile(r"plt_\d{3}")
        
        ...

```

### 3.7 **Publisher Configuration**

This section configures the GwaIO Publisher tool.

* `publisher_builder_data`: This dictionary is key. It maps task names (e.g., 'line', 'model') to a set of `Collect` and `Push` classes. When a user opens the Publisher on a specific task, GwaIO uses this map to build the UI, showing the relevant collection (gathering data) and push (publishing data) steps for that task. 

!!! tip
To learn how to create custom `Collect` and `Push` classes, refer to the [GwaIO Publisher framework documentation](link needed).

```py
        ...
        
        ####################
        # Publisher Config #
        ####################

        # Configures the publisher UI by mapping task types to Collect and Push classes.
        self.publisher_builder_data = {
            "line": {
                CollectTask,
                CollectFileConcept,
                CollectPreview,
                CollectBID,
                CollectDescription,
                PushSG,
            },
            "color": {
                CollectTask,
                CollectFileConcept,
                CollectPreview,
                CollectBID,
                CollectDescription,
                PushSG,
            },
            "sbRough": {
                CollectTask,
                CollectFileVideo,
                CollectPreviewVideo,
                CollectBID,
                PushSG,
            },
            "model": {
                CollectTask,
                CollectFileVideo,
                CollectPreviewVideo,
                CollectBID,
                PushSG,
            },
        }
        
        ...

```


## 4. **Override File-System Layout**

Implement `get_task_filesystem` to map entities to your folder structure. In this case, we will add a pipeline that differentiates between `work` and `publish` files.


```python
    def get_task_filesystem(
        self, code, entity_type, task, step, asset_type, state="work", *args, **kwargs
    ):
        slug: str = None
        if entity_type == "Asset":
            slug = Path(
                "production", state, "assets", asset_type, *code.split("_"), task
            )
        elif entity_type == "Episode":
            slug = Path(f"production/{state}/episodes", code, task)
        elif entity_type == "Shot":
            slug = Path("production", state, "shots", *code.split("_")[0:3], task)
        if slug is None:
            return None, None

        return self._local_root / slug, self._server_root / slug
```
!!! warning
    Ensure `code` formatting matches ShotGrid conventions.

## 5. **Versioning and Naming:** return_next_version_name()

This method dictates how new work files are named, particularly the version number. It's called when the user initiates a "Create File" or "Save Next Version" action from the launcher UI.

**Attributes used:**

* self.last_task_clicked: The currently selected BaseTask object in the UI, providing context.  
* self.task_long_to_short_dict (from ShotgridPlugin): To get short task names if used in filenames.  
* self.return_last_file() (from BasePlugin): To find the previous version number and file.  
* self.version_regex: To parse version numbers from existing files.  
* self._dict_file_templates: To find a suitable template if no previous version exists.  
* self.TEMPLATES_FOLDER: Fallback directory for templates.  
* task.entity_type, task.link_name, task.asset_type, task.local_path: Attributes from the BaseTask object.

```py
    def return_next_version_name(self, ext: Iterable, version: int = None) -> dict:
        # ext: A list of possible file extensions (e.g., [".ma"], [".spp"]).  
        #      The first extension in the list is typically used for the new file.  
        # version: Optional integer to force a specific version number (rarely used by typical UI calls).  
        task = self.last_task_clicked
        if task is not None:
            task_name = self.task_long_to_short(task.name)
            link = task.link_name
            type_ = task.asset_type
            v, last_file = self.return_last_file(ext, task=task)
            v = version or v
            match task.entity_type:
                case "Asset":
                    file_name = f"plt_{type_}_{link}_{task_name}_w{v+1:03}"
                case "Shot":
                    file_name = f"plt_{link}_{task_name}_w{v+1:03}"
                case "Episode":
                    file_name = f"plt_{link}_{task_name}_w{v+1:03}"
            if last_file is None:
                last_file = self._dict_file_templates.get(task_name)
                if not last_file:
                    last_file = Path(self.TEMPLATES_FOLDER)

            return {
                "local_path": Path(task.local_path),
                "file_name": file_name,
                "previous_file": last_file,
                "full_file_name": Path(task.local_path, f"{file_name}.{ext[0]}"),
            }

```

As demonstrated in this method, it performs a check to determine the file's type and subsequently generates the next version number. If no previous version of the file exists, the method defaults to providing a suitable template file from `_dict_file_templates` or, if no specific template is found, the path to the `TEMPLATES_FOLDER`. This mechanism ensures a consistent and controlled naming convention for all new files.

## 6. **Publishing Workflow**

### 6.1. **Helper Methods for Publish Paths**

**Attributes used by** work_to_publish**:**

This method generates the local and server-side publish paths for a given work task.


* self.last_task_clicked: The currently selected BaseTask object in the UI, providing context. 
* task.server_path task.local_path: Attributes from the BaseTask object.

```python
    def work_to_publish(self, task: BaseTask = None) -> Path:
        task = task or self.last_task_clicked
        if task is None:
            return None, None
        publish_local_path = Path(
            *[p if p != "work" else "publish" for p in task.local_path.parts]
        )
        publish_server_path = Path(
            *[p if p != "work" else "publish" for p in task.server_path.parts]
        )
        return publish_local_path, publish_server_path
```

This method computes the next publish filename (with version increment) and returns both the local and server paths for that file.

**Attributes used by** return_next_publish_file**:**

* self.work_to_publish_paths(): To get the base publish directories.  
* self.version_regex (implicitly, for parsing existing publish versions, though the example uses a specific regex r"(?\<=_v)\d{3}" for publish files).  
* task.entity_type, task.link_name, task.asset_type, task.name: For constructing the publish filename.  
* self.task_long_to_short_dict: For short task names in filenames.

```py
    def return_next_publish_file(self, work_file: Path, task: BaseTask = None):
        task = task or self.last_task_clicked
        if task is None:
            return None, None
        publish_local_path, publish_server_path = self.work_to_publish(task)
        v = self.return_last_version_number(publish_server_path)
        task_name = self.task_long_to_short(task.name)
        link = task.link_name
        type_ = task.asset_type
        ext = work_file.suffix
        match task.entity_type:
            case "Asset":
                file_name = f"plt_{type_}_{link}_{task_name}_v{v+1:03}"
            case "Shot":
                file_name = f"plt_{link}_{task_name}_v{v+1:03}"
            case "Episode":
                file_name = f"plt_{link}_{task_name}_v{v+1:03}"

        return Path(publish_local_path, f"{file_name}{ext}"), Path(
            publish_server_path, f"{file_name}{ext}"
        )

```

- **is_published_file:** Prevent duplicates.  
- **return_seq_and_shot_from_clipname:** Parse shot/sequence.  
- **ShotGrid Utilities:** `return_task_notes`, `create_note`, `browse_*`, `task_long_to_short`, `retrieve_cached`, etc.


### 6.2 **Publish version** publish_version()

This is the main method called by the publisher UI (e.g., via a PushSG class) or other publish triggers. It orchestrates file copying and ShotGrid entity creation. To learn how to implement custom publisher classes, please refer to the framework documentation at [Publisher]().  

**Attributes used:**

* self.server_root: To check server connectivity.  
* self.local_root
* self.return_next_publish_file(): To determine target publish paths.  
* super().publish_version(): Calls the ShotgridPlugin's method to create the SG Version and upload the preview.  
* self.publish_file() (from ShotgridPlugin): To create SG PublishedFile entities.  
* task: Instance from the BaseTask object.  

``` py
    def publish_version(
        self,
        task: BaseTask,
        preview: Path = None,
        file: Path = None,
        description: str = "",
    ) -> bool:
        try:
            if not Path(self._server_root).exists():
                return {
                    "success": False,
                    "message": "Not connected to the server.",
                    "error": "Not connected to the server.",
                    "entity": None,
                }
            if isinstance(task, dict):
                task = BaseTask(**task)
            if file is None:
                file = preview
            work_server_file = Path(
                self._server_root,
                *Path(file).parts[len(Path(self._local_root).parts) :],
            )
            work_server_preview = Path(
                self._server_root,
                *Path(preview).parts[len(Path(self._local_root).parts) :],
            )
            publish_local_file, publish_server_file = self.return_next_publish_file(
                Path(file)
            )
            publish_local_preview = Path(
                publish_local_file.parent,
                publish_local_file.stem + Path(preview).suffix,
            )
            publish_server_preview = Path(
                publish_server_file.parent,
                publish_server_file.stem + Path(preview).suffix,
            )
            if not publish_local_file or not publish_server_file:
                return {
                    "success": False,
                    "message": "The file could not be published on the server. Check that you have selected a correct file.",
                    "error": "The file could not be published on the server. Check that you have selected a correct file.",
                    "entity": None,
                }

            work_server_file.parent.mkdir(exist_ok=True, parents=True)
            publish_local_file.parent.mkdir(exist_ok=True, parents=True)
            publish_server_file.parent.mkdir(exist_ok=True, parents=True)

            if file == preview:
                local_to_server = [
                    [file, work_server_file],
                    [file, publish_local_file],
                    [work_server_file, publish_server_file],
                ]
            else:
                local_to_server = [
                    [file, work_server_file],
                    [preview, work_server_preview],
                    [file, publish_local_file],
                    [preview, publish_local_preview],
                    [work_server_file, publish_server_file],
                    [work_server_preview, publish_server_preview],
                ]
            for src, dst in local_to_server:
                if src == dst:
                    continue
                copy2(src, dst)
            for src, dst in local_to_server:
                if not Path(dst).exists():
                    raise Exception(f"The file could not be copied to {dst}")
        except Exception as e:
            traceback.print_exc()
            for src, dst in local_to_server:
                if src != dst and Path(dst).exists():
                    remove(dst)
            return {
                "success": False,
                "message": f"{str(e)}",
                "error": "Upload failed",
                "entity": None,
            }
        try:
            result = super().publish_version(task, publish_server_preview, description)
        except Exception as e:
            traceback.print_exc()
            result = {
                "success": False,
                "message": f"{str(e)}",
                "error": "Upload failed",
                "entity": None,
            }
        if not result.get("success"):
            for src, dst in local_to_server:
                if src != dst and Path(dst).exists():
                    remove(dst)
        else:
            self.publish_file(publish_server_file, result["entity"], task, description)

        return result
```

As we can see, a series of steps is followed to ensure a correct publication. This involves:

1. **Validating inputs and server connection.**  
2. **Determining paths** for working files and published files (local and server).  
3. **Copying files** to their respective locations in the correct order.  
4. If file copies are successful, **publishing a version** to ShotGrid (or a similar system).  
5. If the ShotGrid publish is successful, **linking the main published file**.  
6. **Rollback** (cleanup of copied files) occurs if any critical step fails.

!!! warning
    The `publish_version` method is complex and critical. It involves multiple file operations and API calls. Implement **comprehensive error handling**, clear logging, and consider **transactional behavior** (i.e., if one step fails, attempt to roll back previous steps to avoid leaving the system in an inconsistent state). The example includes basic rollback for file copies if ShotGrid operations fail.

## 7. **Asset Creation from BDL**: `create_assets_from_bdl`

### 7.1. **create_assets_from_bdl** 
This method processes validated asset entries from a BDL Excel file and publishes them to ShotGrid, including:

- Ensuring the **Episode** exists.
- Hashing and publishing the **BDL file** if it's new.
- Creating or updating **Asset** entities, including parent links and metadata.

**Attributes and Helpers Used:**

- `self.return_all_assets()` : Dictionary of existing SG assets to detect duplicates.

- `self.return_all_episodes()` : Dictionary of existing SG episodes for contextual association.

- `hash_file(excel_file)` :Returns `(md5, sha1)` to check for already published BDLs.

- `self.sg.create(entity_type, data_dict)`  :ShotGrid API helper for creating entities like Assets or Episodes.

- `self.sg.update(entity_type, id, data_dict, multi_entity_update_modes)` : Used to update fields like episodes or parent assemblies.

- `self.publish_version(pseudo_task, src_file, pub_file, description)`: Publishes the BDL Excel to ShotGrid as a Version.

- `self.SG_PROJECT_ID`: The active ShotGrid project ID.

```py
    def create_assets_bdl(self, dict_with_items: dict, excel_file: Path):
        logger.debug("Starting asset generation phase.")
        logger.debug("Collecting SG data.")
        created_assets = self.return_all_assets()
        created_episodes = self.return_all_episodes()
        project = {"type": "Project", "id": int(self.SG_PROJECT_ID)}
        episode = f"{excel_file.name.split('_')[1]}"

        if episode not in created_episodes:
            logger.debug(f"Episode not exists. Generating episode {episode}")
            ep_task_template = self.sg.find_one(
                "TaskTemplate", [["code", "is", f"gwaio_episode"]]
            )
            ep = self.sg.create(
                "Episode",
                {
                    "code": episode,
                    "project": project,
                    "task_template": ep_task_template,
                },
            )
            created_episodes.update({episode: ep})
        else:
            ep = created_episodes[episode]
            logger.debug(f"Episode {episode} found")

        md5hash, sha1hash = hash_file(excel_file)
        description = f"Hashes: \nmd5: '{md5hash}'\nsha1: '{sha1hash}'"

        match_version = self.sg.find_one(
            "Version",
            [["description", "is", description]],
        )
        if not match_version:
            logger.debug(f"Starting generation of BDL version in SG. Episode {episode}")
            logger.debug("Hashing BDL file.")
            sg_task = self.sg.find_one(
                "Task", [["entity", "is", ep], ["content", "is", "bdl"]]
            )
            logger.debug(f"BDL task found {sg_task}")

            class PseudoBaseTask:
                entity = ep
                task_entity = sg_task

            result = self.publish_version(
                PseudoBaseTask, excel_file, excel_file, description
            )
            if not result.get("success"):
                raise Exception(
                    f"Error while publishing BDL file.\n{result.get('message')}"
                )
            logger.debug(f"Published BDL version in SG episode {episode}.")

        for key, value in dict_with_items.items():
            logger.debug(f"Working on item {value}")
            if not value["status"]:
                logger.debug(f"Error on item {value}. Fix it")
                yield True
                continue
            tags = (
                [value["series"][5]]
                if "," not in value["series"][5]
                else value["series"][5].split(",")
            )
            parents = (
                [value["series"][3]]
                if "," not in value["series"][3]
                else value["series"][3].split(",")
            )

            if value["asset_name"] not in created_assets:
                task_template = self.sg.find_one(
                    "TaskTemplate",
                    [["code", "is", f"gwaio_asset_{value['series'][0]}"]],
                )
                logger.debug(f"Task template found {task_template}.")
                data = {
                    "code": value["asset_name"],
                    "project": project,
                    "episodes": [ep],
                    "sg_created_for_episode": ep,
                    "sg_asset_type": value["series"][0],
                    "task_template": task_template,
                    "description": value["series"][4],
                    # "tags": tags,
                }
                logger.debug(data)
                created_asset = self.sg.create("Asset", data)
                logger.debug(f"Asset {value['asset_name']} was created.")
            else:
                created_asset = created_assets[value["asset_name"]]

            self.sg.update(
                "Asset",
                created_asset["id"],
                {
                    "episodes": [ep],
                    "description": value["series"][4],
                    "sg_parent_assemblies": [
                        v for k, v in created_assets.items() if k in parents
                    ],
                },
                multi_entity_update_modes={
                    "episodes": "add",
                    "sg_parent_assemblies": "add",
                },
            )
            created_assets[value["asset_name"]] = created_asset

            yield created_asset
```

!!! tip 💡
Use consistent naming conventions for Excel files, e.g. `bdl_EP01.xlsx`, so episode codes are always found correctly.

---

!!! tip
If the BDL file is already registered in ShotGrid (matched by file hash), it will **not** be re-published.

---

### 7.2. **create_assets_bdw** 

This method processes asset entries from a BDW Excel file and publishes them as Asset entities in ShotGrid, using the currently selected task (`self.last_task_clicked`) as context.

**Attributes and Helpers Used:**

- `self.return_all_assets()`: Retrieves a dictionary of currently registered SG assets.

- `hash_file(excel_file)`: Computes the `md5` and `sha1` of the BDW file for identifying previously published files.

- `self.publish_version(task, src, pub, description)`: Publishes the BDW file to ShotGrid if it hasn't been published before (hash-based).

- `self.sg.find_one(entity, filters)`: ShotGrid API call to find matching Version/Template data.

- `self.sg.create(entity_type, data_dict)`: Creates a new Asset entity in SG if it doesn't exist.

- `self.sg.update(entity_type, id, data_dict, multi_entity_update_modes)`: Updates asset metadata and relationships like parent assemblies.

- `self.SG_PROJECT_ID`: Current ShotGrid project ID.

```py
    def create_assets_bdw(self, dict_with_items: dict, excel_file: Path):
        created_assets = self.return_all_assets()
        project = {"type": "Project", "id": int(self.SG_PROJECT_ID)}
        task = self.last_task_clicked
        md5hash, sha1hash = hash_file(excel_file)
        description = f"Hashes: \nmd5: '{md5hash}'\nsha1: '{sha1hash}'"

        match_version = self.sg.find_one(
            "Version",
            [["description", "is", description]],
        )
        if not match_version:
            result = self.publish_version(task, excel_file, excel_file, description)
            if not result.get("success"):
                raise Exception(
                    f"Error while publishing BDW file.\n{result.get('message')}"
                )

        for key, value in dict_with_items.items():
            if not value["status"]:
                yield True
                continue
            tags = (
                [value["series"][5]]
                if "," not in value["series"][5]
                else value["series"][5].split(",")
            )
            parents = (
                [value["series"][3]]
                if "," not in value["series"][3]
                else value["series"][3].split(",")
            )

            if value["asset_name"] not in created_assets:
                task_template = self.sg.find_one(
                    "TaskTemplate",
                    [["code", "is", f"gwaio_asset_{value['series'][0]}"]],
                )
                data = {
                    "code": value["asset_name"],
                    "project": project,
                    "sg_asset_type": value["series"][0],
                    "task_template": task_template,
                    "description": value["series"][4],
                    # "tags": tags,
                }
                created_asset = self.sg.create("Asset", data)
            else:
                created_asset = created_assets[value["asset_name"]]

            self.sg.update(
                "Asset",
                created_asset["id"],
                {
                    "description": value["series"][4],
                    "sg_parent_assemblies": [
                        v for k, v in created_assets.items() if k in parents
                    ],
                },
                multi_entity_update_modes={
                    "episodes": "add",
                    "sg_parent_assemblies": "add",
                },
            )
            created_assets[value["asset_name"]] = created_asset

            yield created_asset
```

!!! tip 💡:
Use unique BDW content or filenames per iteration to avoid duplicate hash rejections in ShotGrid.  

---

!!! note ⚠️:
Unlike `create_assets_bdl`, this method **does not** associate assets with any Episode. It's typically used for sequences or work files not tied to a specific episode.

### 7.3. **create_assets_from_bdl** 
This method reads a BDL Excel file, validates its rows, and creates new Asset entities in ShotGrid for each entry marked as active.

**Attributes and Helpers Used:**
- `self.read_excel(file_path)` → `(headers, data)`  
  Parses the Excel/BDL file and returns both the raw headers and a dictionary of validated row data.
- `self.sg.create(entity_type, data_dict)`  
  ShotGrid API helper for creating a new entity.

```py
    def create_assets_from_bdl(self, dict_with_items: dict, excel_file: Path):
        if self.last_task_clicked.name == "episode":
            for asset in self.create_assets_bdl(dict_with_items, excel_file):
                yield asset
        else:
            for asset in self.create_assets_bdw(dict_with_items, excel_file):
                yield asset
```

## 8. **Reading Excel/BDL Files:** read_excel()

This method parses an Excel-based BDL file and validates its contents against production rules and existing ShotGrid data. It uses the `pandas` library for robust Excel handling and ensures data integrity before downstream processing.

**Attributes used:**

```py
    def read_excel(self, excel: Path):
        existing_assets = self.return_all_assets()
        data_frame = (
            pandas.read_excel(excel, usecols=[0, 1, 2, 3, 4, 5])
        )
        data_frame.fillna("", inplace=True)
        dupes = data_frame.duplicated(
            subset=data_frame.columns[1:3].tolist(), keep=False
        )

        results = dict()
        for i, row in data_frame.iterrows():
            asset_type, code, variant, parent_assets = row[:4]
            asset_name = f"{code}_{variant}"

            results[i] = {
                "series": [content for content in row[:6].tolist()],
                "errors": list(),
                "warnings": list(),
                "episode": f"{excel.name.split("_")[1]}",
                "asset_name": asset_name,
                "exists": asset_name in existing_assets,
                "status": True,
            }

            if dupes[i]:
                results[i]["errors"].append("This asset is repeated.")

            if asset_type not in ["ch", "pr", "ve", "sp", "mp", "fx", "en"]:
                results[i]["errors"].append(f"Unknown asset type '{asset_type}'")

            if parent_assets:
                if not "," in parent_assets:
                    parent_assets = [parent_assets]
                else:
                    parent_assets = parent_assets.split(",")

                for parent_asset in parent_assets:
                    if parent_asset not in existing_assets:
                        candidate = next(
                            (
                                k
                                for k in existing_assets
                                if smatch(None, k, parent_asset).ratio() > 0.8
                            ),
                            None,
                        )
                        results[i]["errors"].append(
                            f"Parent asset {parent_asset} "
                            + "does not exist in SG, please create it first. "
                            + ("\n" if candidate else "")
                            + f"{('Maybe you meant '+ candidate + '?') if candidate is not None else ''}"
                        )

            if asset_name in existing_assets:
                results[i]["exists"] = True
                results[i]["warnings"].append(f"Asset already exists")

            for content in [*row[:2]]:
                if content in (None, ""):
                    results[i]["errors"].append("There are some empty fields.")

            for tag in (code, variant):
                if not tag.replace("_", "").isalnum() and tag != "":
                    results[i]["errors"].append(
                        f"There are non alphanumeric values: "
                        f"{sub('[^0-9a-zA-Z]+', '*', tag)}"
                    )

            results[i]["status"] = len(results[i]["errors"]) == 0

        return [*data_frame.columns[:6].tolist()], results
```

!!! warning
    This method is provided as a project-specific example.  
    It is highly customizable and should only be used in projects  
    where the Excel parsing and asset creation pipeline matches this implementation exactly.


## 9. **Parsing EDLs and Creating Shots**

If your workflow involves EDLs (Edit Decision Lists) for creating or updating ShotGrid shots, 
you will need methods such as `parse_edl_file()` and `create_shot()`. 
These methods are highly specific to the structure of your EDL files (XML, CSV, standard CMX EDL, etc.) 
and how that information maps to ShotGrid fields (e.g., cut-in, cut-out, sequence/episode linking, etc.).

In most cases, implementing `return_seq_and_shot_from_clipname()` 
along with the required supporting variables should be sufficient for parsing the EDL and generating valid shot names.

```py
    def return_seq_and_shot_from_clipname(self, clip_name: str) -> str:
        _,ep,sq,sh = clip_name.split("_")
        return f"{ep}_{sq}", f"{ep}_{sq}_{sh}"
```

!!! tip  
    This assumes your clip names follow a strict naming convention like `plt_EP001_SQ002_SH010`.  
    Adapt the parsing logic if your naming scheme differs.

!!! warning  
    The default implementation of `parse_edl_file()` is minimal and meant for basic pipelines.  
    If your EDL structure is more complex or requires additional validation/mapping logic,  
    you should override `parse_edl_file()` with a custom implementation tailored to your needs.


## 10. **Custom Callbacks and Hooks**

Plugins can implement callback methods that are triggered by certain events within the launcher application.

* file_added_callback(): This method is invoked automatically after a file has been successfully created or associated with a task through the launcher's UI (e.g., via the "Create File" dialog or by dragging and dropping a file onto a task). It's a useful hook for automating subsequent actions, such as updating the status of the corresponding task in ShotGrid.

```py
def file_added_callback(self) -> None:
        if (
            self.sg.find_one(
                "Task",
                [["id", "is", self.last_task_clicked.task_entity.get("id")]],
                ["sg_status_list"],
            ).get("sg_status_list")
            == "rdy"
        ):
            self.sg.update(
                "Task",
                self.last_task_clicked.task_entity.get("id"),
                {"sg_status_list": "ip"},
            )
```
