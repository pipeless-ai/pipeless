import os

import typer
from rich import print as rprint
import yaml

app = typer.Typer()

@app.command(help="Create a new project")
def create(name: str):
    rprint(f"[yellow bold]Creating new project: {name}[/yellow bold]")
    os.mkdir(name)
    # TODO: all config should be possible to override form CLI options
    default_config = {
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
    # TODO: override default config with user provided args
    new_config_file=open(f"{name}/retina_config.yaml","w")
    yaml.dump(default_config, new_config_file)
    new_config_file.close()
    rprint("[yellow]Config file created.[yellow]")
