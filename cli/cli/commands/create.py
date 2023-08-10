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
    project_template = base_dir + '/templates/default'
    try:
        shutil.copytree(project_template, name) # Also creates the directory
        print("Directory copied successfully!")
    except Exception as e:
        rprint(f"[red bold]An error occurred setting up the project template:[/red bold] {str(e)}")

    # TODO: all config should be possible to override form CLI options
    default_config = {
        "log_level": "INFO", # INFO, DEBUG, ERROR, WARNING
        "input": {
            "video": {
                "url": 'my_mp4_file.mp4',
                "type": 'mp4',
            },
            # TODO: should we support input audio only?
        },
        "output": {
            "video": {
                "enabled": True, # TODO: if enabled==False, process audio only
                "url": 'my_mp4_output.mp4',
                "type": "mp4",
            },
            "audio": {
                # TODO: either enabled = True only (audio goes with video) or enabled = True + custom output (audio is split from video)
                "enabled": False,
            },
            "data":{
                # TODO: support exporting data to other platforms
                "enabled": False,
            }
        }
    }

    try:
        # TODO: override default config with user provided args
        new_config_file=open(f"{name}/config.yaml","w")
        yaml.dump(default_config, new_config_file)
        new_config_file.close()
        rprint("[yellow]Config file created.[/yellow]")
    except Exception as e:
        rprint(f"[red bold]An error occurred setting up the project config file:[/red bold] {str(e)}")
