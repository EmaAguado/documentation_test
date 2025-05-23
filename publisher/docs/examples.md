# Introduction to Publisher Framework

This guide introduces you to a practical use of the Task Publishing Framework, illustrating how to create a simple publishing pipeline with custom collection, checking, extraction, and data push processes.

We will walk through defining specific tasks, checks, extraction, and push steps, and finally create an interface to execute the process.

## Code Overview

Our example includes the following components:

-   **Collection Tasks**: `CollectTask`, `CollectPreview`, `CollectFile`, `CollectBID`, and `CollectDescription`.
-   **Validation Checks**: `CheckRepeatedNameNodes`, `CheckPastedNodes`, and `CheckUnknownNodes`.
-   **Extraction**: `ExtractModel`.
-   **Push**: `PushSGModel`.

These processes are registered with the `Manager` and executed in sequence.

## Requirements

Ensure that `PySide6` or `PySide2` and any other necessary dependencies are installed:

```bash
pip install PySide6
```
or
```bash
pip install PySide2
```

Prerequisites
Before you begin, ensure you have Python, PySide2 or PySide6, and a compatible environment to run this application. Familiarity with Maya's Python API will be helpful if you plan to implement checks for Maya nodes.

Setup Imports and Logging

First, set up the necessary imports and configure a basic logger:

``` py linenums="1"
from pathlib import Path
import logging

try:
    from PySide6.QtWidgets import QApplication
except:
    from PySide2.QtWidgets import QApplication

from publisher.core import Collect, Check, Extract, Push, Manager
from publisher.ui.widget import ManagerWidget

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

Explanation: This block imports required modules and configures a logger for debugging.
Creating Collect Classes

Define classes to collect different types of data. Each Collect class represents a piece of data you want to gather in your workflow. Here’s a breakdown of the collect classes:

Python
``` py linenums="1"
class CollectTask(Collect):
    name = "task_id"
    collect_type = int

    def process(self, context):
        self.value = 512

class CollectPreview(Collect):
    name = "preview"
    collect_type = Path

    def process(self, context):
        self.value = Path("/test_folder/preview.jpg")
```

Explanation:
CollectTask collects an integer ID for the task.
CollectPreview collects the path to a preview image.
Both classes override process to set the value attribute.
Creating Check Classes

Checks validate data collected in the previous step. In this example, we create checks for repeated node names, pasted nodes, and unknown nodes in Maya.

``` py linenums="1"
class CheckRepeatedNameNodes(Check):
    name = "Check repeated node names"
    info = "Checks whether there are 2 or more nodes sharing the same short name."

    def process(self, context):
        import maya.cmds as cmds

        status = True
        errors = []

        # Retrieve all node names and check for duplicates
        all_dag_list_long = cmds.ls(type="transform", l=True)
        all_dag_list_short = [item.split("|")[-1] for item in all_dag_list_long]
        all_dag_set = set(all_dag_list_short)

        # Collect duplicates
        if len(all_dag_list_short) != len(all_dag_set):
            repeated_nodes = [node for node in all_dag_list_long if all_dag_list_short.count(node.split("|")[-1]) > 1]
            errors = [{"text": "Repeated node names", "list": [[node, node] for node in repeated_nodes]}]
            status = False

        return status, errors
```

Explanation:
This CheckRepeatedNameNodes class examines Maya nodes for duplicated names.
If duplicates are found, errors are reported, and status is set to False.
Creating Extract and Push Classes

Extraction and pushing represent the final stages of the process, where data is saved and uploaded, respectively.

``` py linenums="1"
class ExtractModel(Extract):
    name = "Extract USD"

    def process(self, context):
        file = context.get_data("file")
        logger.debug(f"THIS IS FILE: {file}")

class PushSGModel(Push):
    name = "Push Version"

    def process(self, context): ...
```

Explanation:
ExtractModel logs the file being processed, while PushSGModel is designed to push a new version.
Creating and Running the Manager

Register the processes with the Manager and launch the application interface using ManagerWidget:

``` py linenums="1"
def main() -> None:
    app = QApplication()
    manager = Manager()

    # Register all custom processes
    manager.register(CollectTask)
    manager.register(CollectFile)
    manager.register(CollectPreview)
    manager.register(CollectBID)
    manager.register(CollectDescription)
    manager.register(CheckRepeatedNameNodes)
    manager.register(CheckPastedNodes)
    manager.register(CheckUnknownNodes)
    manager.register(ExtractModel)
    manager.register(PushSGModel)

    # Create and show the UI
    interface = ManagerWidget(manager)
    interface.show()

    try:
        app.exec()
    except:
        app.exec_()

if __name__ == "__main__":
    main()
```

Explanation:
The main() function sets up the application environment.
Each custom process is registered with the manager.
The UI is displayed via ManagerWidget, showing all registered processes.
Running the Application
To run the application, execute the script in your terminal:

Bash

python your_script_name.py
You will see a user interface displaying each registered process. Through this interface, you can run each process sequentially, view results, and handle errors.

Conclusion
This example demonstrates how to set up a simple workflow for collecting data, validating it, and saving or pushing it. The modular structure allows you to easily expand functionality by adding new Collect, Check, Extract, or Push classes, making the framework adaptable to various use cases.