from rich import print as rprint
import yaml
import os
from pipeless_ai.core import Pipeless

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

    app_filename = 'app.py'
    app_path = os.path.join(exec_dir, app_filename)

    Pipeless(config, component, app_path)
