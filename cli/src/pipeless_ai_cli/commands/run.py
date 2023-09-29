import sys
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
    rprint("[yellow]Running project...[/yellow]")

    exec_dir = os.getcwd()
    config_file_path = os.path.join(exec_dir, 'config.yaml')
    if not os.path.exists(config_file_path):
        rprint('[orange3]No config file detected, initializing empty default config[/orange3]')
        config = {}
    else:
        rprint('Loading config.yaml...')
        with open(config_file_path, "r") as config_file:
            config = yaml.safe_load(config_file)
            rprint('[green]Config file config.yaml detected[/green]')

    app_filename = 'app.py'
    app_path = os.path.join(exec_dir, app_filename)
    if component in ['worker', 'all']:
        # We only load the application into the worker
        if not os.path.exists(app_path):
            rprint("[red]Unable to find app.py file, are you running the command from your application directory?[/red]")
            sys.exit(1)

    Pipeless(config, component, app_path)
