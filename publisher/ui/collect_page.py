from typing import List
import logging

try:
    from PySide6.QtWidgets import ( #type: ignore
        QLabel,
        QWidget,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QComboBox,
        QSpinBox,
        QSizePolicy,
    )
    from PySide6.QtCore import Qt, QEvent #type: ignore

except:
    from PySide2.QtWidgets import ( #type: ignore
        QLabel,
        QWidget,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QComboBox,
        QSpinBox,
        QSizePolicy,
    )
    from PySide2.QtCore import Qt, QEvent #type: ignore

from publisher.ui.qt_widgets import ProcessorPage, StatusWidget, ProcessWidget
from publisher.core import Process, StatusProcess

logger = logging.getLogger(__name__)


class CollectWidget(ProcessWidget):
    def create_widget(self):
        self.central_layout = QHBoxLayout(self)
        self.status_widget = StatusWidget()
        self.label = QLabel(self.process.name)
        self.input = self.create_collector_input(self.process)

        self.label.setMinimumWidth(100)
        self.label.setMaximumWidth(100)
        self.input.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred)

    def create_layout(self):
        self.central_layout.addWidget(self.status_widget)
        self.central_layout.addWidget(self.label)
        self.central_layout.addWidget(self.input)

    def create_collector_input(self, collect) -> None:
        """
        Add an input field based on the collect_type of each instance.

        Args:
            collect (Collect): The collect instance.
        """
        collect_type = collect.collect_type
        label = QLabel(collect.name)
        label.setAlignment(Qt.AlignLeft)

        if collect_type == str:
            input_widget = QLineEdit()
            input_widget.return_value = input_widget.text
            input_widget.set_value = input_widget.setText
            input_widget.value_changed = input_widget.textChanged
        elif collect_type == int:
            input_widget = QSpinBox()
            input_widget.return_value = input_widget.value
            input_widget.set_value = input_widget.setValue
            input_widget.value_changed = input_widget.valueChanged
        elif collect_type == list:
            input_widget = QComboBox()
            input_widget.addItems(["Option 1", "Option 2", "Option 3"])
            input_widget.return_value = input_widget.currentText
            input_widget.set_value = input_widget.setCurrentText
            input_widget.value_changed = input_widget.textChanged
        else:
            input_widget = QLabel()
            input_widget.return_value = str
            input_widget.set_value = str
        if hasattr(input_widget,"value_changed"):
            input_widget.value_changed.connect(self.value_changed)
        input_widget.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred)
        return input_widget
    
    def set_value(self,value):
        self.input.set_value(value)
        self.process.value = value

    def return_value(self):
        return self.input.value()

    def value_changed(self,value):
        logger.debug(f"{self.process.name} Updating value: {value} ")
        self.process.set_status(StatusProcess.UNINITIALIZED)
        self.process.value = value


class CollectPage(ProcessorPage):
    """
    This class generates a CollectPage dynamically based on the instances
    of Collect processes registered in the manager publisher.
    """

    def __init__(self, list_process: List[Process], parent: QWidget = None):
        super().__init__(list_process,parent)
        self.start_collection()

    def add_process_widget(self,process):
        process_widget = CollectWidget(process,self)
        self.list_process_widgets.append(process_widget)
        self.list_process_layout.addWidget(process_widget)

    def start_collection(self) -> None:
        """
        Start the collection process by calling the execute method of each instance.
        Determines whether the collect requires manual input.
        """
        for collect_widget in self.list_process_widgets:
            collect = collect_widget.process
            logger.info(f"Executing collection for {collect.name}")
            collect._execute()
            if collect.value is not None:
                collect_widget.set_value(collect.value)
            else:
                logger.info(f"Manual input required for {collect.name}")
            collect.set_status(StatusProcess.UNINITIALIZED)