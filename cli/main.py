import typer
from commands import project

app = typer.Typer()

app.add_typer(project.app, name="project", help="Manage the project")

@app.command("hello")
def sample_func():
    rprint("[red bold]Hello[/red bold] [yellow]World[yello]")

if __name__ == "__main__":
    app()
