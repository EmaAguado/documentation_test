import abc
import logging
import traceback
from typing import Callable, Dict, List, Any, Optional, Type

# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger: logging = logging.getLogger(__name__)


def log_execution(func):
    """Decorator to log the execution of process methods."""

    def wrapper(self, *args, **kwargs):
        logger.info(f"Starting {self.__class__.__name__} process: {self.name}")
        result = func(self, *args, **kwargs)
        logger.info(f"Completed {self.__class__.__name__} process: {self.name}")
        return result

    return wrapper


class ErrorProcess:
    """
    Class to represent an error that occurs during process execution.

    Attributes:
        error (str): A description of the error.
        details (str): Additional details about the error.
        items (list): Optional list of items or data related to the error.
    """

    def __init__(
        self,
        error: Optional[str] = "Unknown error",
        details: Optional[str] = "Unknown details",
        items: Optional[List[str]] = None,
    ):
        self._error: str = error
        self._details: str = details
        self._items: List[str] = items or list()

    @property
    def error(self) -> str:
        """Returns the error description."""
        return self._error

    @property
    def details(self) -> str:
        """Returns additional details about the error."""
        return self._details

    @property
    def items(self) -> List[str]:
        """Returns the list of items related to the error."""
        return self._items


class StatusProcess:
    """Enum-like class representing the status of a process."""

    UNINITIALIZED: int = 0
    EXECUTING: int = 1
    SUCCESS: int = 2
    WARNING: int = 3
    FAILED: int = 4


class Context:
    """
    A shared context object for storing and accessing data across different processes.
    """

    def __init__(self):
        self.__data: Dict[str, Any] = {}

    def set_data(self, key: str, value: Any) -> None:
        """
        Stores or updates data in the context.

        Args:
            key (str): The key or identifier for the data.
            value (Any): The data to store in the context.

        Example:
            context.set_data('collected_files', ['file1.txt', 'file2.txt'])
        """
        self.__data[key] = value
        logger.debug(f"Context updated: {key} = {value}")

    def get_data(self, key: str) -> Any:
        """
        Retrieves data from the context by key.

        Args:
            key (str): The key or identifier for the data.

        Returns:
            Any: The value associated with the key, or None if not found.

        Example:
            files = context.get_data('collected_files')
        """
        return self.__data.get(key)


class Callback:
    pre_process: int = 0
    post_process: int = 1
    status: int = 2


class Process(abc.ABC):
    """
        Abstract base class for all processes in the task publishing pipeline.

        Attributes:
            name (str): The name of the process.
            compulsory (bool): Indicates if the process is mandatory.
            status (bool): The status of the process (True for success, False for failure, None for not yet executed).
            info (str): Information or description of the process.
            errors (list): A list of ErrorProcess objects representing errors encountered during execution.
            context (Context): A reference to the shared Context object for data exchange.
            callbacks (dict): A dict of callback functions to be executed when a specified action occurs.
    .
    """
    __context: Context = None
    __errors: List[ErrorProcess] = list()
    __status: StatusProcess = StatusProcess.UNINITIALIZED
    compulsory: bool = True
    info: str = "..."
    name: str = "Default Process"

    def __init__(self, manager: "Manager"):
        super().__init__()
        self.__callbacks: Dict[Type[Callback], Callable] = dict()
        self._set_context(manager.context)

    @property
    def callbacks(self) -> Dict[Type[Callback], Callable]:
        """Returns the dict of registered callbacks."""
        return self.__callbacks

    @property
    def context(self) -> Context:
        """Returns the shared context."""
        return self.__context

    @property
    def errors(self) -> List[ErrorProcess]:
        """Returns the list of errors encountered during execution."""
        return self.__errors

    @property
    def status(self) -> StatusProcess:
        """Returns the current status of the process."""
        return self.__status

    def _clear_errors(self) -> None:
        """Clears the list of errors before starting execution."""
        self.__errors = []
        logger.debug(f"Cleared errors for {self.name}.")

    @log_execution
    def _execute(self) -> None:
        """
        Entry point to execute the process, applying the process logic with access to the shared context.

        This method should not be overridden. It handles the execution of the process, including logging,
        handling exceptions, setting the status, and managing errors.

        Before execution, it runs all registered callbacks.
        After execution, it runs all registered callbacks.
        """
        self._clear_errors()
        self.set_status(StatusProcess.EXECUTING)

        try:
            self._run_callbacks(Callback.pre_process)
            self.process(self.__context)
            if self.errors and self.compulsory:
                self.set_status(StatusProcess.FAILED)
                return
            elif self.errors:
                self.set_status(StatusProcess.WARNING)
            else:
                self.set_status(StatusProcess.SUCCESS)
            self._run_callbacks(Callback.post_process)
        except Exception as e:
            traceback.print_exc()
            self.add_error("Failed process", str(e), [[str(e), str(e)]])
            self.set_status(StatusProcess.FAILED)


    def _run_callbacks(self, callback_type: Callback) -> None:
        """Executes all registered callbacks after process execution."""
        for callback in self.__callbacks.get(callback_type, []):
            try:
                logger.debug(f"{self.name} callback {callback_type} executing: {callback}")
                callback(self)
            except Exception as e:
                logger.error(f"Callback execution failed: {e}")

    def _set_context(self, context: Context) -> None:
        """
        Sets the shared context for the process, allowing the process to access and modify shared data.

        Args:
            context (Context): The shared context to be assigned to the process.
        """
        self.__context = context

    def add_callback(self, callback_type: Callback, callback: callable) -> None:
        """Adds a callback function to be executed after the process finishes."""
        if not self.__callbacks.get(callback_type):
            self.__callbacks[callback_type] = list()
        self.__callbacks[callback_type].append(callback)
        logger.debug(f"Add callback {self.name}  {callback_type} added: {callback}")

    def add_error(
        self,
        error: Optional[str] = "Unknown error",
        details: Optional[str] = "Unknown details",
        items: Optional[List[str]] = None,
    ) -> None:
        """
        Adds an error to the list of errors.

        Args:
            error (str): The error message or name.
            details (str): Detailed description of the error.
            items (list): Optional list of items related to the error.
        """
        self.__errors.append(ErrorProcess(error, details, items or []))

    @abc.abstractmethod
    def process(self, context: Context) -> None:
        """
        The core logic of the process. This method should be implemented by subclasses with specific logic for the process.

        Args:
            context (Context): The shared context for accessing and storing data during execution.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the 'process' method."
        )

    def set_status(self, status: StatusProcess) -> None:
        """
        Sets the status of the process.

        Args:
            status (StatusProcess): Set status.
        """
        self.__status = status
        self._run_callbacks(Callback.status)
        logger.debug(f"Status for {self.name} set to {self.__status}")


class Collect(Process):
    """
    A class representing the file collection process.

    This class is responsible for handling the collection of files, storing the collected value,
    and updating the shared context with the collected data.

    Attributes:
        name (str): The name of the collection process.
        collect_type (Type): The expected type of the collected data (default is `str`).
        _value (Any): The collected value, initially set to None.
    """

    name: str = "Default Collect"
    collect_type = str

    def __init__(self, manager):
        super().__init__(manager)
        self._value: Any = None
        self._update_context()

    @log_execution
    def _execute(self) -> None:
        """
        Entry point to execute the process, applying the process logic with access to the shared context.

        This method should not be overridden. It handles the execution of the process, including logging,
        handling exceptions, setting the status, and managing errors.

        Before execution, it runs all registered callbacks.
        After execution, it runs all registered callbacks.
        """
        self._clear_errors()
        self.set_status(StatusProcess.EXECUTING)

        try:
            self._run_callbacks(Callback.pre_process)
            self.process(self.context)
            if self.value in [None,""]:
                self.add_error(
                    "Failed collect", "missing value", [["missing value", "missing value"]]
                )
            if self.errors and self.compulsory:
                self.set_status(StatusProcess.FAILED)
                return
            elif self.errors:
                self.set_status(StatusProcess.WARNING)
            else:
                self.set_status(StatusProcess.SUCCESS)
            self._run_callbacks(Callback.post_process)
        except Exception as e:
            traceback.print_exc()
            self.add_error("Failed process", str(e), [[str(e), str(e)]])
            self.set_status(StatusProcess.FAILED)
        
            # self.set_status(StatusProcess.FAILED)

    @property
    def value(self) -> Any:
        """Returns the current collected value."""
        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        """
        Sets a new value for the collection process and updates the context.

        Args:
            value (Any): The new value to be collected.
        """
        if self.collect_type is not None and not isinstance(value, self.collect_type):
            logger.error(
                f"{self.name}: Value must be of type {self.collect_type.__name__} -> {value}"
            )
            self.add_error(
                "Failed collect",
                f"Value must be of type {self.collect_type.__name__}",
                [
                    [
                        f"Value must be of type {self.collect_type.__name__}",
                        f"Value must be of type {self.collect_type.__name__}",
                    ]
                ],
            )
            # self.set_status(StatusProcess.FAILED)
            raise TypeError(f"Value must be of type {self.collect_type.__name__}")
        self._value = value
        self._update_context()

    def _update_context(self) -> None:
        """
        Updates the shared context with the current collected value.
        """
        if self.context is not None:
            self.context.set_data(self.name, self._value)


class Check(Process):
    name: str = "Default Check"

    def fix_method(self) -> None:
        """Provides a method to fix issues detected by the check."""
        logger.debug(f"Fix method not yet implemented for {self.name}.")


class Extract(Process):
    """A class representing the file extraction process."""

    name: str = "Default Extract"


class Push(Process):
    """A class representing the process to push data to the database."""

    name: str = "Default Push"


class Manager:
    """
    Manager class that manages the registration and execution
    of different processes, including collecting, checking,
    extraction, and pushing to the database.

    Attributes:
        context (Context): The shared context for managing data
                           among the different processes.
        collectors (List[Collect]): A list of collecting processes.
        checks (List[Check]): A list of checking processes.
        extractors (List[Extract]): A list of extraction processes.
        pushes (List[Push]): A list of push processes for database operations.
    """

    def __init__(self) -> None:
        """Initializes the Manager with empty process lists."""
        self._context: Context = Context()
        self.collectors: List[Collect] = []
        self.checks: List[Check] = []
        self.extractors: List[Extract] = []
        self.pushes: List[Push] = []

    @property
    def context(self):
        """Gets the shared context for the Manager."""
        return self._context

    def register(self, process: Process) -> None:
        """
        Registers a process in the correct category based on its type.

        Args:
            process (Process): An process of a subclass of Process to be registered.

        Raises:
            ValueError: If the process type is unknown.
        """
        if issubclass(process, Collect):
            self.collectors.append(process(self))
            logger.debug(f"Registered {process.name} as a collector.")
        elif issubclass(process, Check):
            self.checks.append(process(self))
            logger.debug(f"Registered {process.name} as a validator.")
        elif issubclass(process, Extract):
            self.extractors.append(process(self))
            logger.debug(f"Registered {process.name} as an extractor.")
        elif issubclass(process, Push):
            self.pushes.append(process(self))
            logger.debug(f"Registered {process.name} as a database updater.")
        else:
            logger.error(f"Unknown process type: {process}")
            raise ValueError(f"Unknown process type: {process}")

    def processes(self) -> Dict[str, List["Process"]]:
        """
        Returns a dictionary with all the registered processes.

        Returns:
            dict: A dictionary with process types as keys and lists of instances as values.
        """
        return {
            Collect: self.collectors,
            Check: self.checks,
            Extract: self.extractors,
            Push: self.pushes,
        }

    def publish(self) -> None:
        """Executes the registered processes in sequence."""
        logger.info(f"Publisher starting publish...")
        try:
            for type_, processes in self.processes().items():
                for process in processes:
                    # if process.status == StatusProcess.SUCCESS:
                    #     continue
                    logger.info(f"Executing {type_}: {process.name}")
                    process._execute()
                    if process.status == StatusProcess.FAILED and process.compulsory:
                        err_str = "\n".join(
                            [f"{ err.error}:{ err.details}" for err in process.errors]
                        )
                        raise Exception(f"{process.name} failed:\n {err_str}")


            logger.info(f"Publisher finished publish...")
        except Exception as e:
            traceback.print_exc()
            logger.error(f"An error occurred during publishing: {e}")
            raise Exception(e)
