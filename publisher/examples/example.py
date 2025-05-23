from pathlib import Path
import logging
import time
if __name__ == "__main__":
    # these are only required if the module is executed stand alone
    from pathlib import Path
    import sys
    from os import fspath
    sys.path.append(fspath(Path(__file__).parent.parent.parent))

try:
    from PySide6.QtWidgets import QApplication  # type: ignore
except:
    from PySide2.QtWidgets import QApplication  # type: ignore

from publisher.core import Collect, Check, Extract, Push, Manager, StatusProcess
from publisher.widget import ManagerWidget

# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# MODEL PUBLISHER manager


class CollectTask(Collect):
    name = "task_id"
    collect_type = int
    info = "Unique identifier for the task in the publishing context."

    def process(self, context):
        self.value = 512
        time.sleep(0.2)


class CollectPreview(Collect):
    name = "preview"
    collect_type = str
    info = "Path to the preview image for the task."

    def process(self, context):
        self.value = "/test_folder/preview.jpg"
        time.sleep(0.2)


class CollectFile(Collect):
    name = "file"
    collect_type = str
    info = "Path to the main file for the task, such as the primary project file."

    def process(self, context):
        self.value = "/test_folder/file.ma"
        time.sleep(0.2)


class CollectBID(Collect):
    name = "BID"
    collect_type = str
    compulsory = False
    info = "Job time in version, optional for some tasks."

    def process(self, context):
        time.sleep(0.2)


class CollectDescription(Collect):
    name = "Description"
    collect_type = str
    info = "Short description or summary of the task."

    def process(self, context):
        time.sleep(0.2)




class CheckRepeatedNameNodes(Check):
    name = "Check repeated node names"
    info = "Checks whether there are 2 or more nodes\n" "sharing the same short name."

    def process(self, context):
        time.sleep(10)
        import maya.cmds as cmds  # type: ignore

        status = True
        errors = []

        status = True
        all_dag_list_long = cmds.ls(type="transform", l=True)
        all_dag_list_short = [item.split("|")[-1] for item in all_dag_list_long]
        all_dag_set = set(all_dag_list_short)
        diff = []
        repeated_nodes = []
        errors_nodes = []
        errors = []

        if len(all_dag_list_short) != len(all_dag_set):
            for item in all_dag_list_short:
                if item in all_dag_set:
                    all_dag_set.remove(item)
                else:
                    diff.append(item)

        for item in set(diff):
            for node in all_dag_list_long:
                if item in node:
                    repeated_nodes.append(node)

        if len(repeated_nodes) != 0:
            status = False
            for item in repeated_nodes:
                errors_nodes.append([item.split("|")[-1], item])
            errors = [{"text": "Repeated node names", "list": errors_nodes}]

        return status, errors


class CheckPastedNodes(Check):
    name = "Checks pasted nodes"
    info = "Checks whether there is any pasted node.\n"

    def process(self, context):
        import maya.cmds as cmds  # type: ignore

        status = True
        errors = []
        self.errors_nodes = []

        for node in cmds.ls(ap=True, l=True):
            if "pasted__" in node:
                self.errors_nodes.append([node.split("|")[-1], node])
                status = False

        if not status:
            errors = [{"text": "Pasted nodes", "list": self.errors_nodes}]

        return status, errors

    def fix_method(self, context):
        import maya.cmds as cmds  # type: ignore

        for node in cmds.ls(ap=True, l=True):
            if "pasted__" not in node:
                continue
            try:
                if cmds.objExists(node):
                    cmds.delete(node)
            except Exception as e:
                print("[ERROR] - Failed to remove the node {} ->".format(node))
                print(e)


class CheckUnknownNodes(Check):
    name = "Check unknown nodes"
    info = "Looks for unknown nodes\n" "and if so, fixing will remove them."

    def process(self, context):
        import maya.cmds as cmds  # type: ignore
        from maya_utils import return_unknown_nodes  # type: ignore

        self.unknown_nodes = list(return_unknown_nodes())
        if len(self.unknown_nodes) != 0:
            all_unknown_nodes = [[item, item] for item in self.unknown_nodes]
            errors = [{"text": "There are unknown nodes", "list": all_unknown_nodes}]
            status = False
        else:
            errors = []
            status = True

        return status, errors

    def fix_method(self, context):
        import maya.cmds as cmds  # type: ignore

        for node in self.unknown_nodes:
            try:
                try:
                    if cmds.lockNode(node, query=True, lock=True)[0]:
                        cmds.lockNode(node, lock=False)
                except:
                    pass
                cmds.delete(node)
            except:
                pass


class ExtractModel(Extract):
    name = "Extract USD"

    def process(self, context):
        file = context.get_data("file")
        logger.debug(f"THIS IS FILE: {file}")


class PushSGModel(Push):
    name = "Push Version"

    def process(self, context): ...


def main() -> None:
    """Main entry point for the application."""
    app = QApplication()
    manager = Manager()
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

    interface = ManagerWidget(manager)
    interface.show()

    try:
        app.exec()
    except:
        app.exec_()


if __name__ == "__main__":
    main()
