## Task Schema
The task schema defines how the task folders will be grouped
together, it is essentially a blue print that the task plugin will abide to.
The task schema is essentially the file system format, and it is primarly composed of two parts: the [task input](#task-input) and the [task plugin](#task-plugin).

### Task Input
This is essentially a list of tasks formated as a json, with both
compulsory and non-compulsory fields. Many of these fields will be gathered form either a hardcoded list or a method for gathering this list from somewhere else defined in the  plugin.

1. **Compulsory fields**: those fields that are needed for keeping the tools functioning as expected. These are defined by developers.
   1. **local_root**: the local root of the file system. Can -should- be a environment variable.
   2. **server_root**: the server root of the file system. Can -should- be a environment variable.
   3. **directory**: an upstream hardcoded directory of folders, or a method of making up the parent folders from compulsory fields.
   4. **name**: the name of the task. This is the name of the folder of this task.
2. **Project fields**: project relative compulsory fields.Compulsory elements that may be re-define for each project.
   1. **entity**: generally a task would belong to an specific entity from the following list: episode, sequence, shot, asset. This is useful for sorting.
   2. **assignee**: a list of people the task is assigned to.
3. **Optional fields**: those that will allow for non-critical
and additional tool functionality. Some optional fields may become compulsory depending on each pipeline. These fields are usually handly for sorting and filtering purposes.
   1. **subfolders**: a list of folders that are contained withing the "task folder".
   2. **id**: the unique identifyer for this task. May be defined by the plugin.

### Task plugin
This is an utility that allows for the translation of the raw input data into Task Input friendly data. This is where the programing work is done and it has to be crafted for each input each time every input changes. So there will be one plugin for input comming from Shotgrid, another one for data comming from and Excel, Google Sheets etc. There should be only one plugin used for each project and no more than one plugin should be used as it would mean that the project doesn't have a centralized data base.

