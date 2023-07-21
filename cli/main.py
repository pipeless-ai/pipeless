import typer
from commands import create, run

app = typer.Typer()

app.add_typer(create.app, name="create", help="Create project resources")

@app.command('run', help='Execute the project')
def run_project():
    run.run_app()

if __name__ == "__main__":
    app()
