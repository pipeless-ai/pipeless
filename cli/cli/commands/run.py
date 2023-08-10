from rich import print as rprint
import yaml
import os
import importlib.util
from pupila.pupila import Pupila

def run_app(component: str):
    """
    The run command must be executed from the project dir.
    It will load all apps under the project's 'apps' directory.

    The component is 'input', 'output', 'worker' or 'all'
    """
    rprint(f"[yellow]Running project...[/yellow]")

    exec_dir = os.getcwd()
    config_file_path = os.path.join(exec_dir, 'config.yaml')

    rprint('Loading config.yaml...')
    config_file=open(config_file_path, "r")
    config = yaml.safe_load(config_file)
    config_file.close()
    rprint('[green]Config loaded[/green]')

    # NOTE: We used to search for the .py files, however moved to
    #       use a standard name: app.py
    app_filename = 'app.py'
    app_name = app_filename[:-3]  # Remove the ".py" extension
    app_path = os.path.join(exec_dir, app_filename)

    # Load the module
    spec = importlib.util.spec_from_file_location(app_name, app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # The app main class must be called like the app file
    if hasattr(module, app_name.capitalize()):
        app_class = getattr(module, app_name.capitalize())
        # Instantiate the app
        app_instance = app_class()
        Pupila(config, component)
