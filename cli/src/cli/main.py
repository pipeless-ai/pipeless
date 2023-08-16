import typer
from .commands import create, run

app = typer.Typer()

app.add_typer(create.app, name="create", help="Create project resources")

@app.command('run', help='Execute the project')
def run_project(component: str = typer.Argument("all")):
    run.run_app(component)

if __name__ == "__main__":
    app()
