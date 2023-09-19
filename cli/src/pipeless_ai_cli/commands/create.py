import os
import typer
from rich import print as rprint
import yaml
import shutil

app = typer.Typer()

@app.command(name="project", help="Create a new project")
def create_project(name: str):
    rprint(f"[yellow bold]Creating new project: {name}[/yellow bold]")

    # TODO: support more templates
    base_dir = os.path.dirname(__file__)
    project_template = f'{base_dir}/templates/default'
    try:
        shutil.copytree(project_template, name) # Also creates the directory
    except Exception as e:
        rprint(f"[red bold]An error occurred setting up the project template:[/red bold] {str(e)}")

    # TODO: should be able to override default config via CLI options
    default_config = {
        'log_level': 'INFO',
        'input': {
            'video': {
                'enable': True,
                'uri': 'file:///home/your/path'
            },
            'address': { # address where the input component runs for the nng connections
                'host': 'localhost',
                'port': 1234
            },
        },
        "output": {
            'video': {
                'enable': True,
                'uri': 'file:///home/your/path'
            },
            'address': { # address where the input component runs for the nng connections
                'host': 'localhost',
                'port': 1237
            },
        },
        'worker': {
            'n_workers': 1,
        },
        'plugins': {
            'order': ''
        }
    }

    try:
        with open(f"{name}/config.yaml","w") as new_config_file:
            yaml.dump(default_config, new_config_file)
        rprint("[yellow]Config file created.[/yellow]")
    except Exception as e:
        rprint(f"[red bold]An error occurred setting up the project config file:[/red bold] {str(e)}")
