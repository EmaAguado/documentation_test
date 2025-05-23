from functools import partial
from typing import Dict, List, Type
from utilities.pipe_utils import thread

try:
    from PySide6.QtWidgets import (  # type:ignore
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QStackedWidget,
        QSplitter,
    )
    from PySide6.QtCore import Qt  # type:ignore
except:
    from PySide2.QtWidgets import (  # type:ignore
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QStackedWidget,
        QSplitter,
    )
    from PySide2.QtCore import Qt  # type:ignore

from publisher.core import (
    Check,
    Collect,
    Extract,
    Manager,
    Push,
    Process,
    StatusProcess,
)
from publisher.ui.collect_page import CollectPage
from publisher.ui.qt_widgets import InfoPanel, ProcessorPage, STATUS_STYLE


class ManagerWidget(QWidget):
    """
    Main window for the task publisher management interface, displaying various task-related tabs.

    This widget initializes as the main application window and dynamically generates
    pages based on the types of processes registered within a `Manager` instance.
    """

    def __init__(self, manager: Manager) -> None:
        """
        Initialize the ManagerWidget, setting up the main window's appearance and
        creating pages for each process type provided by the publisher manager.

        Args:
            manager (Manager): An instance of the Manager class, containing the registered processes.
        """
        super().__init__()

        self.setWindowTitle("Publisher")
        self.setGeometry(100, 100, 800, 600)
        self.manager = manager

        self.main_layout = QVBoxLayout(self)

        self.button_bar = QHBoxLayout()
        self.main_layout.addLayout(self.button_bar)
        self.button_bar.setContentsMargins(0, 0, 0, 0)
        self.button_bar.setSpacing(0)
        self.splitter_widget = QSplitter()
        self.splitter_widget.setOrientation(Qt.Horizontal)
        self.stacked_widget = QStackedWidget()
        self.info_panel_widget = InfoPanel()
        self.splitter_widget.addWidget(self.stacked_widget)
        self.splitter_widget.addWidget(self.info_panel_widget)  
        self.main_layout.addWidget(self.splitter_widget)

        self.publish_button = QPushButton("Publish")
        self.main_layout.addWidget(self.publish_button)
        self.publish_button.clicked.connect(self.publish)
        self.selected_page = None

        self.create_pages(manager.processes())

    def create_pages(self, processes: Dict[Type[Process], List[Process]]) -> None:
        """
        Dynamically create pages in the main window for each type of process in the Manager.

        This method iterates over the provided dictionary of processes and creates
        a specific page for each recognized process type (Collect, Check, Extract, Push).
        It also creates a button in the button bar to switch to each page.

        Args:
            processes (Dict[Type[Process], List[Process]]):
                A dictionary where each key is a process type (such as Collect, Check, etc.)
                and the corresponding value is a list of process instances of that type.
        """
        for process_type, instances in processes.items():
            if not instances:
                continue
            if process_type == Collect:
                page = CollectPage(instances,self)
                name = "Collect"
            elif process_type == Check:
                page = ProcessorPage(instances,self)
                name = "Check"
            elif process_type == Extract:
                page = ProcessorPage(instances,self)
                name = "Extract"
            elif process_type == Push:
                page = ProcessorPage(instances,self)
                name = "Push"

            self.stacked_widget.addWidget(page)
            page.tab_button = QPushButton(name)
            page.tab_button.setCheckable(True)
            page.tab_button.clicked.connect(partial(self.on_tab_page, page))
            self.button_bar.addWidget(page.tab_button)
            self.set_tab_page_status(page, StatusProcess.UNINITIALIZED)

    # @thread
    def publish(self) -> None:
        """
        Trigger the publishing process by calling the manager's publish method.

        This method runs in a separate thread to prevent blocking the UI.
        After publishing, it updates the status of each page based on the results.
        """
        try:
            self.manager.publish()
        except Exception:
            pass

        for index in range(self.stacked_widget.count()):
            page = self.stacked_widget.widget(index)
            status = page.status_page()
            if status == StatusProcess.FAILED:
                self.on_tab_page(page)
                return

    def on_tab_page(self, page: ProcessorPage):
        if self.selected_page:
            self.selected_page.tab_button.setChecked(False)
        self.selected_page = page
        page.tab_button.setChecked(True)
        self.stacked_widget.setCurrentWidget(page)

    def set_tab_page_status(self, page: ProcessorPage, status: StatusProcess) -> None:
        """
        Update the color of the status button in the button bar based on the process status.

        Args:
            page (ProcessorPage): The page whose status button color will be updated.
            status (StatusProcess): The current status of the process, which determines the button color.
        """
        color = STATUS_STYLE[status]["color"]
        if not hasattr(page,"tab_button"):
            return
        page.tab_button.setStyleSheet(
            "QPushButton{background-color:rgb"
            + str(color)
            + ";padding:10px;border: 5px solid palette(mid); border-radius: 5px}"
            "QPushButton:hover{border: 5px solid palette(base)}"
            "QPushButton:checked{border: 5px solid palette(highlight)}"
        )
