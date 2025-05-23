from functools import partial
from pathlib import Path
from os import fspath
from typing import List

try:
    from PySide6.QtWidgets import (  # type: ignore
        QWidget,
        QGridLayout,
        QLabel,
        QPushButton,
        QFrame,
        QVBoxLayout,
        QListWidget,
        QAbstractItemView,
        QListView,
        QTextEdit,
        QSpacerItem,
        QSizePolicy,
        QScrollArea,
        QListWidgetItem,
        QHBoxLayout,
        QSplitter,
        QAbstractScrollArea,
        QStyle,
    )
    from PySide6.QtGui import (
        QIcon,
        QColor,
        QPalette,
        QStandardItemModel,
        QPixmap,
        QFont,
    )
    from PySide6.QtCore import Qt, QEvent, Signal
except:
    from PySide2.QtWidgets import (  # type: ignore
        QWidget,
        QGridLayout,
        QLabel,
        QPushButton,
        QFrame,
        QVBoxLayout,
        QListWidget,
        QAbstractItemView,
        QListView,
        QTextEdit,
        QSpacerItem,
        QSizePolicy,
        QScrollArea,
        QListWidgetItem,
        QHBoxLayout,
        QSplitter,
        QAbstractScrollArea,
        QStyle,
    )
    from PySide2.QtGui import (  # type: ignore
        QIcon,
        QColor,
        QPalette,
        QStandardItemModel,
        QPixmap,
        QFont,
    )
    from PySide2.QtCore import Qt, QEvent, Signal  # type: ignore


from publisher.core import Callback, Process, StatusProcess

UI_FILES_PATH = fspath(
    Path(Path(__file__).parent.parent.parent, "utilities/static/icons/")
)
STATUS_STYLE = {
    StatusProcess.UNINITIALIZED:{"icon": "pause.png", "color": (124, 124, 124)},
    StatusProcess.EXECUTING:{"icon": "synchronize.png", "color": (67,97,117)},
    StatusProcess.SUCCESS:{"icon": "check.png", "color": (56, 118, 29)},
    StatusProcess.WARNING:{"icon": "warning.png", "color": (230, 119, 11)},
    StatusProcess.FAILED:{"icon": "warning.png", "color": (153, 0, 0)},
}

class Dropdown(QWidget):
    """
    Utility class used all throught the UI as a hide and show button.
    """

    def __init__(self, title="", parent=None):
        super(Dropdown, self).__init__(parent)
        self.title = title
        self.expand = True

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.central_layout = QGridLayout(self)
        self.central_layout.setContentsMargins(0, 10, 0, 0)

        self.title = QLabel(self.title)
        self.button = QPushButton(QIcon(UI_FILES_PATH + "/down.png"), "")
        self.button.setMaximumSize(24, 24)
        self.button.setCheckable(True)
        self.button.setChecked(True)
        self.frame = QFrame()
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(0, 0, 0, 0)

    def create_layout(self):
        self.central_layout.addWidget(self.button, 0, 0)
        self.central_layout.addWidget(self.title, 0, 1)
        self.central_layout.addWidget(self.frame, 1, 0, 1, 2)

    def create_connections(self):
        self.button.clicked.connect(partial(self.setExpand))

    def addWidget(self, widget):
        self.frame_layout.addWidget(widget)

    def setExpand(self):
        if self.button.isChecked():
            self.frame.show()
            self.button.setIcon(QIcon(UI_FILES_PATH + "/down.png"))
        else:
            self.frame.hide()
            self.button.setIcon(QIcon(UI_FILES_PATH + "/forward.png"))


class StatusWidget(QLabel):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(24, 24)
        self.setMaximumSize(24, 24)
        self.set_status(StatusProcess.UNINITIALIZED)

    @property
    def status(self):
        return self._status

    def set_status(self, status):
        self._status = status
        self.setStyleSheet(f"background-color:rgb{str(STATUS_STYLE[status]['color'])};border-radius: 5px")


class ProcessWidget(QFrame):
    on_status = Signal(object)
    on_selected = Signal(object)

    def __init__(self, process, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.process = process
        self._selected = False
        self.create_widget()
        self.create_layout()
        self.create_style()
        self.create_connections()

        self.installEventFilter(self)
        for child in self.findChildren(QWidget):
            child.installEventFilter(self)

    def create_widget(self):
        self.central_layout = QHBoxLayout(self)
        self.status_widget = StatusWidget()
        self.label = QLabel(self.process.name)

    def create_layout(self):
        self.central_layout.addWidget(self.status_widget)
        self.central_layout.addWidget(self.label)

    def create_connections(self):
        self.on_status.connect(self.refresh_status)
        self.on_selected.connect(lambda:self.parent.on_select_process(self))
        self.process.add_callback(Callback.status,self.on_status.emit)
        self.process.add_callback(Callback.pre_process,self.on_selected.emit)

    def create_style(self):
        self.setStyleSheet(
            "ProcessWidget{background-color:palette(dark);border-radius: 5px}"
        )
        self.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed))

    def refresh_status(self):
        self.status_widget.set_status(self.process.status)
        self.parent.parent.info_panel_widget.set_process(self.process)
        self.parent.status_page()

    def eventFilter(self, source, event):
        if event.type() in {QEvent.MouseButtonPress, QEvent.FocusIn}:
            self.parent.on_select_process(self)
        return super().eventFilter(source, event)
    
    def enterEvent(self,event):
        if not self._selected:
            self.setStyleSheet(
                "ProcessWidget{background-color:palette(base);border-radius: 5px}"
            )
            return super().enterEvent(event)
    
    def leaveEvent(self,event):
        if not self._selected:
            self.setStyleSheet(
                "ProcessWidget{background-color:palette(dark);border-radius: 5px}"
            )
            return super().leaveEvent(event)

    def mousePressEvent(self,event):
        self.parent.on_select_process(self)

    def on_select(self):
        self._selected = True
        self.setStyleSheet(
            "ProcessWidget{background-color:palette(highlight);border-radius: 5px}"
        )
        try:
            self.parent.parent.on_tab_page(self.parent)
        except:
            pass
    
    def on_unselect(self):
        self._selected = False
        self.setStyleSheet(
            "ProcessWidget{background-color:palette(dark);border-radius: 5px}"
        )

class ErrorListWidget(QListWidget):
    """
    Used mostly to display a list of the errors that were found in the errors.
    """
    on_error_select = Signal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_view = QStandardItemModel(self)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setEditTriggers(QListView.NoEditTriggers)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setResizeMode(QListWidget.Adjust)
        self.create_connections()

    def on_click(self, index):
        index = self.selectedIndexes()[0]
        self.on_error_select.emit(index.data(3))

    def add_custom_item(self, icon=None, list_items=None):
        if not list_items:
            return
        for item in list_items:
            name = item[0]
            data = item[1]
            if icon:
                obj = QListWidgetItem(icon, name)
            else:
                obj = QListWidgetItem(name)
            obj.setData(3, data)
            obj.setBackground(QColor(self.palette().color(QPalette.Mid).name()))
            font = QFont("Monospace")
            font.setStyleHint(QFont.TypeWriter)
            obj.setFont(font)
            self.addItem(obj)

    def create_connections(self):
        self.clicked.connect(partial(self.on_click))


class InfoPanel(QFrame):
    on_error_select = Signal(object)
    on_select_all_errors = Signal(list)
    def __init__(self):
        super().__init__()
        self.setStyleSheet("QFrame{background-color:palette(midlight)}")
        self.expand = False
        self.create_widgets()
        self.create_layout()

    def set_process(self, process):
        name = process.name
        info = process.info
        errors = process.errors
        status = process.status

        try:
            if self.button_error:
                code = []
                for button in self.button_error.keys():
                    self.button_error[button].deleteLater()
                    self.error_type[button].deleteLater()
                    self.list_error[button].deleteLater()
                    code.append(button)
                for button in code:
                    del self.button_error[button]
                    del self.error_type[button]
                    del self.list_error[button]
        except:
            pass

        self.label_title.setText(name)
        self.label_status.setStyleSheet(f"background-color:rgb{STATUS_STYLE[status]['color']}")
        self.label_status.setPixmap(
            QPixmap(UI_FILES_PATH + "/" + STATUS_STYLE[status]["icon"]).scaled(32, 32)
        )
        self.text_info.setText(info)
        self.error_type = dict()
        self.list_error = dict()
        self.button_error = dict()

        if errors:
            for error in errors:
                text = error.error
                details = error.details
                items = error.items
                self.error_type[text] = Dropdown(text)
                self.error_type[text].central_layout.setContentsMargins(10, 2, 0, 0)
                self.error_type[text].central_layout.setHorizontalSpacing(0)
                self.error_type[text].frame.setStyleSheet(
                    "QFrame{background-color:palette(dark)}"
                )
                self.error_type[text].title.setStyleSheet(
                    "background-color:palette(dark);padding:5px"
                )
                self.list_error[text] = ErrorListWidget()
                self.error_type[text].addWidget(self.list_error[text])
                self.list_error[text].add_custom_item(
                    icon=self.style().standardIcon(QStyle.SP_MessageBoxCritical),
                    list_items=items,
                )
                self.list_error[text].on_error_select.connect(self.on_error_select.emit)

                self.button_error[text] = QPushButton("Select All")
                self.button_error[text].clicked.connect(
                    partial(self.on_select_all_errors.emit, items)
                )
                self.error_type[text].addWidget(self.button_error[text])

                self.drop_errors.addWidget(self.error_type[text])
        self.show()

    def create_widgets(self):
        self.central_layout = QVBoxLayout(self)
        self.fr_title = QFrame()
        self.fr_title.setStyleSheet("QFrame{background-color:palette(dark)}")
        self.title_layout = QGridLayout(self.fr_title)
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.label_status = QLabel()
        self.label_status.setAlignment(Qt.AlignCenter)
        self.label_status.setMinimumSize(40, 60)
        self.label_status.setMaximumSize(40, 60)
        self.label_title = QLabel()
        self.label_pass = QLabel()
        self.title_layout.addWidget(self.label_status, 0, 0, 2, 1)
        self.title_layout.addWidget(self.label_title, 0, 1)

        self.drop_info = Dropdown("Information")
        self.text_info = QTextEdit()
        self.text_info.setStyleSheet("background-color:palette(dark)")
        self.text_info.setReadOnly(True)
        self.drop_info.addWidget(self.text_info)

        self.drop_errors = Dropdown("Errors")

    def create_layout(self):
        self.central_layout.addWidget(self.fr_title)
        self.central_layout.addWidget(self.drop_info)
        self.central_layout.addWidget(self.drop_errors)
        self.central_layout.addItem(
            QSpacerItem(5, 1, QSizePolicy.Preferred, QSizePolicy.Expanding)
        )
        

class ProcessorPage(QWidget):
    def __init__(self, list_process: List[Process], parent: QWidget = None):
        super().__init__()
        self.parent = parent
        self.create_widgets()
        self.create_layout()
        self.create_style()
        self.selected_process_widget = None
        self.list_process_widgets = list()
        for process in list_process:
            self.add_process_widget(process)
        self.list_process_layout.addItem(
            QSpacerItem(5, 1, QSizePolicy.Expanding, QSizePolicy.Expanding)
        )

    def create_widgets(self):
        self.central_widget = QScrollArea()
        self.main_layout = QVBoxLayout(self)
        self.list_widget_process = QWidget()
        self.central_widget.setWidget(self.list_widget_process)
        self.list_process_layout = QVBoxLayout(self.list_widget_process)

    def create_layout(self):
        self.main_layout.addWidget(self.central_widget)

    def create_style(self):
        self.central_widget.setStyleSheet("QScrollArea{border:none}")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.central_widget.setWidgetResizable(True)
        self.central_widget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    def add_process_widget(self, process: Process):
        process_widget = ProcessWidget(process,self)
        self.list_process_widgets.append(process_widget)
        self.list_process_layout.addWidget(process_widget)

    def on_select_process(self,process_widget):
        if self.selected_process_widget:
            self.selected_process_widget.on_unselect()
        process_widget.on_select()
        self.selected_process_widget = process_widget      
        self.parent.info_panel_widget.set_process(process_widget.process)

    def status_page(self):
        statuses = []
        for process_widget in self.list_process_widgets:
            statuses.append(process_widget.process.status)
        if any([status == StatusProcess.EXECUTING for status in statuses]):
            self.parent.set_tab_page_status(self, StatusProcess.EXECUTING)
        elif any([status == StatusProcess.FAILED for status in statuses]):
            self.parent.set_tab_page_status(self, StatusProcess.FAILED)
        elif any([status == StatusProcess.WARNING for status in statuses]):
            self.parent.set_tab_page_status(self, StatusProcess.WARNING)
        elif any([status == StatusProcess.UNINITIALIZED for status in statuses]):
            self.parent.set_tab_page_status(self, StatusProcess.UNINITIALIZED)
        else:
            self.parent.set_tab_page_status(self, StatusProcess.SUCCESS)
