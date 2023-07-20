import typer
from commands import create

app = typer.Typer()

app.add_typer(create.app, name="create", help="Create project resources")
app.add_typer(project.app, name="run", help="Execute the project")

@app.command("hello")
def sample_func():
    rprint("[red bold]Hello[/red bold] [yellow]World[/yellow]")

if __name__ == "__main__":
    app()
