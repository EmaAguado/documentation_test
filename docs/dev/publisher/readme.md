# Task Publishing Framework

This Python task publishing framework is designed to streamline the
execution of sequential processes such as file collection, validation,
extraction, and database updating. The framework allows developers to
register and execute custom processes within a flexible structure, using
a shared context for data exchange.

## Features

-   **Modular**: Define and register different types of processes
    ([Collect]{.title-ref}, [Check]{.title-ref}, [Extract]{.title-ref},
    [Push]{.title-ref}).
-   **Shared Context**: Use a [Context]{.title-ref} object to share data
    between processes.
-   **Error Handling**: Efficiently track and manage errors through the
    [ErrorProcess]{.title-ref} class.
-   **Callbacks**: Execute callback functions after processes finish.
-   **Easy Integration**: Extensible and flexible, allowing for the
    creation of custom processes.

## Installation

First, clone the repository and navigate to the project folder:

``` bash
git clone https://github.com/mondotv/publisher.git
cd task-publishing-framework
```

Ensure you have a virtual environment set up, and install dependencies
if required:

``` bash
pip install -r requirements.txt
```

## Basic Usage

1.  **Create a custom process class**

    To define a new process, subclass one of the abstract process types
    ([Collect]{.title-ref}, [Check]{.title-ref}, [Extract]{.title-ref},
    [Push]{.title-ref}) and implement the [process]{.title-ref} method.
    Here\'s an example of a custom collection process:

    ``` py linenums="1"
    from publisher.core import Collect

    class CustomCollect(Collect):
       name = "Collect Files"
       collect_type = list  # Expected data type

       def process(self, context):
          # Implement collection logic
          files = ["file1.txt", "file2.txt"]
          self.value = files
    ```

2.  **Register and execute processes**

    After defining the process, register it with the
    [Manager]{.title-ref} and run the publishing sequence:

    ``` py linenums="1"
    from publisher.core import Manager

    # Create an instance of manager
    manager = Manager()

    # Register the processes
    manager.register(CustomCollect)

    # Execute the processes
    manager.publish()

    # Retrieve results from the shared context
    collected_files = manager.context.get_data("Collect Files")
    print(collected_files)  # Output: ['file1.txt', 'file2.txt']
    ```

3.  **Error management and status**

    The framework captures and manages errors automatically. You can add
    errors to any process, and the [Process]{.title-ref} class will log
    them:

    ``` py linenums="1"
    from publisher.core import Process, Context

    class MyCheck(Process):
       name = "Custom Check"

       def process(self, context):
          # Simulate a failure
          if not context.get_data("required_data"):
             self.add_error("Missing data", "The required_data key is missing in context.")
             self.set_status(False)

    # Register and execute
    check = MyCheck(manager)
    manager.register(check)
    manager.publish()
    ```

4.  **Callbacks**

    You can add callbacks to any process, which will execute once the
    process finishes:

    ``` py linenums="1"
    def notify_user(process):
       print(f"Process {process.name} has finished!")

    check.add_callback(notify_user)
    ```

## Project Structure

-   \`core.py\`: Contains the base classes for processes
    ([Process]{.title-ref}, [Collect]{.title-ref}, [Check]{.title-ref},
    [Extract]{.title-ref}, [Push]{.title-ref}) and the
    [Manager]{.title-ref} class.
-   \`tests/\`: Includes tests to validate the framework\'s
    functionality.
-   \`examples/\`: Includes practical examples of how to make a simple
    publisher with the framework.
-   \`docs/\`: Project documentation, generated using Sphinx.

## Extensibility

This framework is easily extensible. You can create new types of
processes by subclassing the base [Process]{.title-ref} class and
tailoring them to your application needs. Here\'s an example of an
extraction process:

``` py linenums="1"
from publisher.core import Extract

class CustomExtract(Extract):
   name = "Extract Data"

   def process(self, context):
      # Extraction logic
      data = context.get_data("collected_files")
      extracted_data = [file.upper() for file in data]  # Example transformation
      self.context.set_data("extracted_data", extracted_data)
```

## Documentation

For more details on the classes and methods, refer to the project
documentation located in the [docs/]{.title-ref} directory. The
documentation includes:

-   Detailed guides
-   Usage examples
-   Descriptions of each class and function

## Modules

- [Índice de módulos](modules.md)
- [Ejemplos](examples.md)