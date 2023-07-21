from rich import print as rprint
import yaml
import os
import importlib.util

def run_app():
    """
    The run command must be executed from the project dir.
    It will load all apps under the project's 'apps' directory.
    """
    rprint(f"[yellow bold]Running project...[/yellow bold]")

    exec_dir = os.getcwd()
    apps_dir = os.path.join(exec_dir, 'apps')

    for filename in os.listdir(apps_dir):
        if filename.endswith(".py"):
            app_name = filename[:-3]  # Remove the ".py" extension
            app_path = os.path.join(apps_dir, filename)

            # Load the module
            spec = importlib.util.spec_from_file_location(app_name, app_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # The app main class must be called like the app file
            if hasattr(module, app_name.capitalize()):
                app_class = getattr(module, app_name.capitalize())

                # Instantiate the app
                instance = app_class()
                instance.run()
