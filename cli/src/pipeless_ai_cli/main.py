import typer
from .commands import create, install, run, list

app = typer.Typer()

app.add_typer(create.app, name="create", help="Create project resources")

@app.command('run', help='Execute the project')
def run_project(component: str = typer.Argument("all")):
    run.run_app(component)

app.add_typer(install.app, name="install", help="Install project resources such as plugins")
app.add_typer(list.app, name="list", help="List available project resources")

if __name__ == "__main__":
    app()
