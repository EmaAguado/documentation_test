# # production_plugin.py
# from pathlib import Path
# from typing import Iterable
# import traceback
# from shutil import copy2
# from os import remove, fspath
# import pandas
# from difflib import SequenceMatcher as smatch
# from re import sub

# if __name__ == "__main__":
#     # these are only required if the module is executed stand alone
#     from PySide6.QtWidgets import QApplication
#     import sys

#     base_path = fspath(Path(__file__).parent.parent.parent)
#     app = QApplication()
#     sys.path.append(base_path)

# from task_schema.plugins.shotgrid_plugin import (
#     ShotgridPlugin,
#     BaseTask,
# )  # Core plugin classes
# from launcher.qtclasses.toolbar_maya import (
#     MayaToolbar,
# )  # Optional: UI elements like toolbars
# from publisher.core import (
#     Collect,
#     Push,
# )  # Assuming these are your publisher framework base classes

# # Optional: Utilities
# from utilities.maya.scripts import (
#     batch_playblast,
#     batch_turntable,
# )


# class ProductionPlugin(ShotgridPlugin):
#     title = "Production Project"  # A more descriptive title, can be used in UIs.
#     SG_PROJECT_ID = 999
#     SHOTGRID_URL = "https://yourstudio.shotgunstudio.com"

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         ################
#         # GwaIO Config #
#         ################

#         self._active_entities = [
#             "My Tasks",
#             "Asset",
#             "Sequence",
#             "Episode",
#             "Shot",
#         ]  # Default entity type and filters to apply when the plugin loads in the launcher.
#         self._jobs += [
#             batch_playblast,
#             batch_turntable,
#         ]
#         # Define custom toolbars to be added to the launcher UI for this plugin.
#         # Each item is a list: [ToolbarClass, "Display Name", "Placement (e.g., 'right')"]
#         self._toolbars += [
#             [MayaToolbar, "Maya Toolbar", "right"],
#         ]
#         self.add_tasks_from_plugin_kwargs = {
#             "sg_entity_type": "My Tasks"
#         }  # Default entity type and filters to apply when the plugin loads in the launcher.
#         self.create_file_ext = [
#             "from selected",
#             "psd",
#             "ma",
#             "spp",
#             "xlsx",
#         ]  # File extensions offered in the "Create File" dialog. "from selected" implies using the current task context.
#         self.uses_deadline = (
#             True  # Flag indicating if the project uses a render farm like Deadline.
#         )

#         #############
#         # SG Config #
#         #############

#         # --- ShotGrid Custom Artist Entity Configuration ---
#         # Defines how launcher users are mapped to your specific Artist entity in ShotGrid.
#         self.custom_artist_entity_name = "CustomEntity04"  # Field on your Artist Custom Entity in SG that matches the launcher username.
#         self.custom_artist_login_field = "code"
#         # Fields on various ShotGrid entities that link back to your Artist Custom Entity.
#         self.publishedfile_artist_entity_field = "sg_mondo_artist"  # On PublishedFile
#         self.timelog_artist_entity_field = "sg_mondo_artist"  # On TimeLog
#         self.version_artist_entity_field = "sg_mondo_artist"  # On Version
#         self.custom_artist_task_field = "sg_mondo_artist"  # On Task (for assignments)
#         # Extend or refine the default ShotGrid task filters inherited from ShotgridPlugin.
#         # These filters apply when fetching tasks from ShotGrid.
#         self.plugin_task_filters += [
#             ["sg_status_list", "not_in", ["na", "wtg"]],
#             ["entity.Asset.sg_status_list", "not_in", ["na"]],
#         ]
#         # Default ShotGrid status to assign to newly uploaded Versions (e.g., "rev" for "Pending Review").
#         self._upload_status = "rev"

#         ######################
#         # File System Config #
#         ######################

#         # Set the local root path for the project.
#         # Reads "PRODUCTION_LOCAL_PATH" env var
#         self._local_root = Path(self.env_handler.get_env("PRODUCTION_LOCAL_PATH"))
#         # Set the server root path for the project.
#         # Reads "PRODUCTION_SERVER_PATH" env var, or uses hardcode path
#         self._server_root = Path(
#             self.env_handler.get_env(
#                 "PRODUCTION_SERVER_PATH",
#                 Path("\\\\qsrv01.mondotvcanarias.lan\\proj_production\\Production"),
#             )
#         )
#         self.TEMPLATES_FOLDER = Path(
#             self._server_root, "production/publish/templates"
#         )  # Path to project file templates.
#         self.SL_SERVER_PATH = Path(
#             self._server_root, "production/publish/library/anim_lib"
#         )  # Path to a studio library.

#         # Relative path within a task's local directory where previews (e.g., thumbnails, playblasts) are stored.
#         # If Path(), previews are at the root of the task's local_path.
#         self._preview_location = Path()
#         # If True, the entity's code (e.g., asset/shot name) must be part of the versioned filename.
#         self._version_includes_entity = True
#         # Regex to extract version numbers from filenames (e.g., gets '001' from 'file_w001.ma').
#         self.version_regex = r"(?<=_[wv])\d\d\d"
#         # List of regex patterns to validate filenames against project conventions.
#         # "prd" is an example prefix; adapt these to your project's specific naming scheme.
#         self._naming_regex = [
#             r"^prd_[a-z]{2}_[A-Za-z0-9]+_[A-Za-z0-9]+_[a-z]+_[wv]\d\d\d.*",
#             r"^prd(_\d\d\d)_([a-z]+)_[wv]\d\d\d.*",
#             r"^prd(_\d\d\d){2}_([a-z]+)_[wv]\d\d\d.*",
#             r"^prd(_\d\d\d){3}_([a-z]+)_[wv]\d\d\d.*",
#             r"^prd(_\d\d\d){3}(_[a-z]+){1,3}_[wv]\d\d\d.*",
#         ]
#         # Regular expression to validate BDL (Bill of Data List) filenames.
#         self.bdlregex = (
#             r"prd_(\d\d\d_|[a-zA-Z]{2}_([a-zA-Z09]*._){2})bd[lw]_[vw]\d\d\d\.xlsx"
#         )
#         # Base path for asset work directories.
#         self._asset_folder = fspath(self.local_root) + "/PROD/assets/work"
#         # Regex to help an asset browser find asset work folders.
#         self._asset_folder_regex = fspath(self.local_root) + "/PROD/assets/work/*/*/*"

#         # Provides default template files. Used by return_next_version_name.
#         self._dict_file_templates = {
#             "bdl": Path(self.TEMPLATES_FOLDER, "prd_template_bdl.xlsx"),
#             "bdw": Path(self.TEMPLATES_FOLDER, "prd_template_bdl.xlsx"),
#             "skt": Path(self.TEMPLATES_FOLDER, "prd_template_psd.psd"),
#         }

#         ##############
#         # DCC Config #
#         ##############

#         # Paths to shared custom scripts, plugins, or shelves for DCC applications.
#         # These are often added to environment variables in generate_environment_for_app().
#         self.CUSTOM_MAYA_TOOLS = Path(self.server_root, "pipeline/publish/dev/maya")
#         self.CUSTOM_NUKE_TOOLS = Path(self.server_root, "pipeline/publish/dev/nuke")

#         ##################
#         # Project Config #
#         ##################

#         self._fps = 25  # Frames per second for the project.
#         self._starting_frame = (
#             101  # Default start frame for animation, playblasts, etc.
#         )
#         # --- Previous Task Mapping ---
#         # Defines dependencies: maps a current task name to its typical upstream task.
#         # Used to find outputs from previous steps (e.g., model from blocking for rigging).
#         # Key: current task's long SG name. Value: dict {task_name: prev_task_long_SG_name, step: prev_task_SG_Step_code}.
#         self._dict_previous_tasks = {
#             "line": {"task": "sketch", "step": "ConceptArtStep"},
#             "color": {"task": "line", "step": "ConceptArtStep"},
#             "model": {"task": "blocking", "step": "ModelingStep"},
#             "uvs": {"task": "model", "step": "ModelingStep"},
#         }

#         ##############
#         # EDL Config #
#         ##############

#         self._edl_target_task = "animatic"  # Default SG Task name for EDL processing
#         self._edl_task_name = "EDL"
#         self._edl_shot_prefix = ""
#         self._edl_sequence_prefix = ""
#         self._edl_episode_prefix = "plt_"
#         self.edl_sequence_regex = compile(r"(?<=plt_)\d{3}_\d{3}")
#         self._edl_shot_regex = compile(r"(?<=plt_)\d{3}_\d{3}_\d{3}")
#         self.edl_version_regex = compile(r"(?<=_[VvWw])\d\d\d")
#         self._shot_task_tpl_id = 1069
#         self._episode_edl_workflow = True
#         self._edl_episode_regex = compile(r"plt_\d{3}")

#         ####################
#         # Publisher Config #
#         ####################

#         # Configures the publisher UI by mapping task types to Collect and Push classes.
#         # self.publisher_builder_data = {
#         #     "line": {
#         #         CollectTask,
#         #         CollectFileConcept,
#         #         CollectPreview,
#         #         CollectBID,
#         #         CollectDescription,
#         #         PushSG,
#         #     },
#         #     "color": {
#         #         CollectTask,
#         #         CollectFileConcept,
#         #         CollectPreview,
#         #         CollectBID,
#         #         CollectDescription,
#         #         PushSG,
#         #     },
#         #     "sbRough": {
#         #         CollectTask,
#         #         CollectFileVideo,
#         #         CollectPreviewVideo,
#         #         CollectBID,
#         #         PushSG,
#         #     },
#         #     "model": {
#         #         CollectTask,
#         #         CollectFileVideo,
#         #         CollectPreviewVideo,
#         #         CollectBID,
#         #         PushSG,
#         #     },
#         # }

#     def get_task_filesystem(
#         self, code, entity_type, task, step, asset_type, state="work", *args, **kwargs
#     ):
#         slug: str = None
#         if entity_type == "Asset":
#             slug = Path(
#                 "production", state, "assets", asset_type, *code.split("_"), task
#             )
#         elif entity_type == "Episode":
#             slug = Path(f"production/{state}/episodes", code, task)
#         elif entity_type == "Shot":
#             slug = Path("production", state, "shots", *code.split("_")[0:3], task)
#         if slug is None:
#             return None, None

#         return self._local_root / slug, self._server_root / slug

#     def file_added_callback(self) -> None:
#         if (
#             self.sg.find_one(
#                 "Task",
#                 [["id", "is", self.last_task_clicked.task_entity.get("id")]],
#                 ["sg_status_list"],
#             ).get("sg_status_list")
#             == "rdy"
#         ):
#             self.sg.update(
#                 "Task",
#                 self.last_task_clicked.task_entity.get("id"),
#                 {"sg_status_list": "ip"},
#             )

#     def return_next_version_name(self, ext: Iterable, version: int = None) -> dict:
#         # ext: A list of possible file extensions (e.g., [".ma"], [".spp"]).
#         #      The first extension in the list is typically used for the new file.
#         # version: Optional integer to force a specific version number (rarely used by typical UI calls).
#         task = self.last_task_clicked
#         if task is not None:
#             task_name = self.task_long_to_short(task.name)
#             link = task.link_name
#             type_ = task.asset_type
#             v, last_file = self.return_last_file(ext, task=task)
#             v = version or v
#             match task.entity_type:
#                 case "Asset":
#                     file_name = f"plt_{type_}_{link}_{task_name}_w{v+1:03}"
#                 case "Shot":
#                     file_name = f"plt_{link}_{task_name}_w{v+1:03}"
#                 case "Episode":
#                     file_name = f"plt_{link}_{task_name}_w{v+1:03}"
#             if last_file is None:
#                 last_file = self._dict_file_templates.get(task_name)
#                 if not last_file:
#                     last_file = Path(self.TEMPLATES_FOLDER)

#             return {
#                 "local_path": Path(task.local_path),
#                 "file_name": file_name,
#                 "previous_file": last_file,
#                 "full_file_name": Path(task.local_path, f"{file_name}.{ext[0]}"),
#             }

#     def work_to_publish(self, task: BaseTask = None) -> Path:
#         task = task or self.last_task_clicked
#         if task is None:
#             return None, None
#         publish_local_path = Path(
#             *[p if p != "work" else "publish" for p in task.local_path.parts]
#         )
#         publish_server_path = Path(
#             *[p if p != "work" else "publish" for p in task.server_path.parts]
#         )
#         return publish_local_path, publish_server_path

#     def return_next_publish_file(self, work_file: Path, task: BaseTask = None):
#         task = task or self.last_task_clicked
#         if task is None:
#             return None, None
#         publish_local_path, publish_server_path = self.work_to_publish(task)
#         v = self.return_last_version_number(publish_server_path)
#         task_name = self.task_long_to_short(task.name)
#         link = task.link_name
#         type_ = task.asset_type
#         ext = work_file.suffix
#         match task.entity_type:
#             case "Asset":
#                 file_name = f"plt_{type_}_{link}_{task_name}_v{v+1:03}"
#             case "Shot":
#                 file_name = f"plt_{link}_{task_name}_v{v+1:03}"
#             case "Episode":
#                 file_name = f"plt_{link}_{task_name}_v{v+1:03}"

#         return Path(publish_local_path, f"{file_name}{ext}"), Path(
#             publish_server_path, f"{file_name}{ext}"
#         )

#     def publish_version(
#         self,
#         task: BaseTask,
#         preview: Path = None,
#         file: Path = None,
#         description: str = "",
#     ) -> bool:

#         try:
#             if not Path(self._server_root).exists():
#                 return {
#                     "success": False,
#                     "message": "Not connected to the server.",
#                     "error": "Not connected to the server.",
#                     "entity": None,
#                 }
#             if isinstance(task, dict):
#                 task = BaseTask(**task)
#             if file is None:
#                 file = preview
#             work_server_file = Path(
#                 self._server_root,
#                 *Path(file).parts[len(Path(self._local_root).parts) :],
#             )
#             work_server_preview = Path(
#                 self._server_root,
#                 *Path(preview).parts[len(Path(self._local_root).parts) :],
#             )
#             publish_local_file, publish_server_file = self.return_next_publish_file(
#                 Path(file)
#             )
#             publish_local_preview = Path(
#                 publish_local_file.parent,
#                 publish_local_file.stem + Path(preview).suffix,
#             )
#             publish_server_preview = Path(
#                 publish_server_file.parent,
#                 publish_server_file.stem + Path(preview).suffix,
#             )
#             if not publish_local_file or not publish_server_file:
#                 return {
#                     "success": False,
#                     "message": "The file could not be published on the server. Check that you have selected a correct file.",
#                     "error": "The file could not be published on the server. Check that you have selected a correct file.",
#                     "entity": None,
#                 }

#             work_server_file.parent.mkdir(exist_ok=True, parents=True)
#             publish_local_file.parent.mkdir(exist_ok=True, parents=True)
#             publish_server_file.parent.mkdir(exist_ok=True, parents=True)

#             if file == preview:
#                 local_to_server = [
#                     [file, work_server_file],
#                     [file, publish_local_file],
#                     [work_server_file, publish_server_file],
#                 ]
#             else:
#                 local_to_server = [
#                     [file, work_server_file],
#                     [preview, work_server_preview],
#                     [file, publish_local_file],
#                     [preview, publish_local_preview],
#                     [work_server_file, publish_server_file],
#                     [work_server_preview, publish_server_preview],
#                 ]
#             for src, dst in local_to_server:
#                 if src == dst:
#                     continue
#                 copy2(src, dst)
#             for src, dst in local_to_server:
#                 if not Path(dst).exists():
#                     raise Exception(f"The file could not be copied to {dst}")
#         except Exception as e:
#             traceback.print_exc()
#             for src, dst in local_to_server:
#                 if src != dst and Path(dst).exists():
#                     remove(dst)
#             return {
#                 "success": False,
#                 "message": f"{str(e)}",
#                 "error": "Upload failed",
#                 "entity": None,
#             }
#         try:
#             result = super().publish_version(task, publish_server_preview, description)
#         except Exception as e:
#             traceback.print_exc()
#             result = {
#                 "success": False,
#                 "message": f"{str(e)}",
#                 "error": "Upload failed",
#                 "entity": None,
#             }
#         if not result.get("success"):
#             for src, dst in local_to_server:
#                 if src != dst and Path(dst).exists():
#                     remove(dst)
#         else:
#             self.publish_file(publish_server_file, result["entity"], task, description)

#         return result

#     def create_assets_bdl(self, dict_with_items: dict, excel_file: Path):
#         created_assets = self.return_all_assets()
#         created_episodes = self.return_all_episodes()
#         project = {"type": "Project", "id": int(self.SG_PROJECT_ID)}
#         episode = f"{excel_file.name.split('_')[1]}"

#         if episode not in created_episodes:
#             ep_task_template = self.sg.find_one(
#                 "TaskTemplate", [["code", "is", f"gwaio_episode"]]
#             )
#             ep = self.sg.create(
#                 "Episode",
#                 {
#                     "code": episode,
#                     "project": project,
#                     "task_template": ep_task_template,
#                 },
#             )
#             created_episodes.update({episode: ep})
#         else:
#             ep = created_episodes[episode]

#         md5hash, sha1hash = hash_file(excel_file)
#         description = f"Hashes: \nmd5: '{md5hash}'\nsha1: '{sha1hash}'"

#         match_version = self.sg.find_one(
#             "Version",
#             [["description", "is", description]],
#         )
#         if not match_version:
#             sg_task = self.sg.find_one(
#                 "Task", [["entity", "is", ep], ["content", "is", "bdl"]]
#             )

#             class PseudoBaseTask:
#                 entity = ep
#                 task_entity = sg_task

#             result = self.publish_version(
#                 PseudoBaseTask, excel_file, excel_file, description
#             )
#             if not result.get("success"):
#                 raise Exception(
#                     f"Error while publishing BDL file.\n{result.get('message')}"
#                 )

#         for key, value in dict_with_items.items():
#             if not value["status"]:
#                 yield True
#                 continue
#             tags = (
#                 [value["series"][5]]
#                 if "," not in value["series"][5]
#                 else value["series"][5].split(",")
#             )
#             parents = (
#                 [value["series"][3]]
#                 if "," not in value["series"][3]
#                 else value["series"][3].split(",")
#             )

#             if value["asset_name"] not in created_assets:
#                 task_template = self.sg.find_one(
#                     "TaskTemplate",
#                     [["code", "is", f"gwaio_asset_{value['series'][0]}"]],
#                 )
#                 data = {
#                     "code": value["asset_name"],
#                     "project": project,
#                     "episodes": [ep],
#                     "sg_created_for_episode": ep,
#                     "sg_asset_type": value["series"][0],
#                     "task_template": task_template,
#                     "description": value["series"][4],
#                     # "tags": tags,
#                 }
#                 created_asset = self.sg.create("Asset", data)
#             else:
#                 created_asset = created_assets[value["asset_name"]]

#             self.sg.update(
#                 "Asset",
#                 created_asset["id"],
#                 {
#                     "episodes": [ep],
#                     "description": value["series"][4],
#                     "sg_parent_assemblies": [
#                         v for k, v in created_assets.items() if k in parents
#                     ],
#                 },
#                 multi_entity_update_modes={
#                     "episodes": "add",
#                     "sg_parent_assemblies": "add",
#                 },
#             )
#             created_assets[value["asset_name"]] = created_asset

#             yield created_asset

#     def create_assets_bdw(self, dict_with_items: dict, excel_file: Path):
#         created_assets = self.return_all_assets()
#         project = {"type": "Project", "id": int(self.SG_PROJECT_ID)}
#         task = self.last_task_clicked
#         md5hash, sha1hash = hash_file(excel_file)
#         description = f"Hashes: \nmd5: '{md5hash}'\nsha1: '{sha1hash}'"

#         match_version = self.sg.find_one(
#             "Version",
#             [["description", "is", description]],
#         )
#         if not match_version:
#             result = self.publish_version(task, excel_file, excel_file, description)
#             if not result.get("success"):
#                 raise Exception(
#                     f"Error while publishing BDW file.\n{result.get('message')}"
#                 )

#         for key, value in dict_with_items.items():
#             if not value["status"]:
#                 yield True
#                 continue
#             tags = (
#                 [value["series"][5]]
#                 if "," not in value["series"][5]
#                 else value["series"][5].split(",")
#             )
#             parents = (
#                 [value["series"][3]]
#                 if "," not in value["series"][3]
#                 else value["series"][3].split(",")
#             )

#             if value["asset_name"] not in created_assets:
#                 task_template = self.sg.find_one(
#                     "TaskTemplate",
#                     [["code", "is", f"gwaio_asset_{value['series'][0]}"]],
#                 )
#                 data = {
#                     "code": value["asset_name"],
#                     "project": project,
#                     "sg_asset_type": value["series"][0],
#                     "task_template": task_template,
#                     "description": value["series"][4],
#                     # "tags": tags,
#                 }
#                 created_asset = self.sg.create("Asset", data)
#             else:
#                 created_asset = created_assets[value["asset_name"]]

#             self.sg.update(
#                 "Asset",
#                 created_asset["id"],
#                 {
#                     "description": value["series"][4],
#                     "sg_parent_assemblies": [
#                         v for k, v in created_assets.items() if k in parents
#                     ],
#                 },
#                 multi_entity_update_modes={
#                     "episodes": "add",
#                     "sg_parent_assemblies": "add",
#                 },
#             )
#             created_assets[value["asset_name"]] = created_asset

#             yield created_asset

#     def create_assets_from_bdl(self, dict_with_items: dict, excel_file: Path):
#         if self.last_task_clicked.name == "episode":
#             for asset in self.create_assets_bdl(dict_with_items, excel_file):
#                 yield asset
#         else:
#             for asset in self.create_assets_bdw(dict_with_items, excel_file):
#                 yield asset

#     def read_excel(self, excel: Path):
#         existing_assets = self.return_all_assets()
#         data_frame = (
#             pandas.read_excel(excel, usecols=[0, 1, 2, 3, 4, 5])
#         )
#         data_frame.fillna("", inplace=True)
#         dupes = data_frame.duplicated(
#             subset=data_frame.columns[1:3].tolist(), keep=False
#         )

#         results = dict()
#         for i, row in data_frame.iterrows():
#             asset_type, code, variant, parent_assets = row[:4]
#             asset_name = f"{code}_{variant}"

#             results[i] = {
#                 "series": [content for content in row[:6].tolist()],
#                 "errors": list(),
#                 "warnings": list(),
#                 "episode": f"{excel.name.split("_")[1]}",
#                 "asset_name": asset_name,
#                 "exists": asset_name in existing_assets,
#                 "status": True,
#             }

#             if dupes[i]:
#                 results[i]["errors"].append("This asset is repeated.")

#             if asset_type not in ["ch", "pr", "ve", "sp", "mp", "fx", "en"]:
#                 results[i]["errors"].append(f"Unknown asset type '{asset_type}'")

#             if parent_assets:
#                 if not "," in parent_assets:
#                     parent_assets = [parent_assets]
#                 else:
#                     parent_assets = parent_assets.split(",")

#                 for parent_asset in parent_assets:
#                     if parent_asset not in existing_assets:
#                         candidate = next(
#                             (
#                                 k
#                                 for k in existing_assets
#                                 if smatch(None, k, parent_asset).ratio() > 0.8
#                             ),
#                             None,
#                         )
#                         results[i]["errors"].append(
#                             f"Parent asset {parent_asset} "
#                             + "does not exist in SG, please create it first. "
#                             + ("\n" if candidate else "")
#                             + f"{('Maybe you meant '+ candidate + '?') if candidate is not None else ''}"
#                         )

#             if asset_name in existing_assets:
#                 results[i]["exists"] = True
#                 results[i]["warnings"].append(f"Asset already exists")

#             for content in [*row[:2]]:
#                 if content in (None, ""):
#                     results[i]["errors"].append("There are some empty fields.")

#             for tag in (code, variant):
#                 if not tag.replace("_", "").isalnum() and tag != "":
#                     results[i]["errors"].append(
#                         f"There are non alphanumeric values: "
#                         f"{sub('[^0-9a-zA-Z]+', '*', tag)}"
#                     )

#             results[i]["status"] = len(results[i]["errors"]) == 0

#         return [*data_frame.columns[:6].tolist()], results

#     def return_seq_and_shot_from_clipname(self, clip_name: str) -> str:
#         _,ep,sq,sh = clip_name.split("_")
#         return f"{ep}_{sq}", f"{ep}_{sq}_{sh}"