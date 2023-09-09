import typer
from rich import print as rprint

from pipeless_ai_cli.lib.plugins import get_latest_plugin_version_dict, get_plugins_registry

app = typer.Typer()

@app.command(name="available-plugins", help="List plugins from the plugin registry that can be installed")
def list_plugins():
    plugins_registry = get_plugins_registry()
    for plugin in plugins_registry['plugins']:
        rprint(f'[green]{plugin.get("name")}[/green]')
        rprint(f'\tID: {plugin.get("id")}')
        rprint(f'\tDescription: {plugin.get("description")}')
        version = get_latest_plugin_version_dict(plugin.get('versions'))
        rprint(f'\tDocs URL: {version.get("docs_url")}')
        rprint(f'\tLatest version: {version.get("version")}')
        rprint(f'\tRepository URL: {version.get("repo_url")}')
        rprint(f'\tRepository subdirectory: {version.get("subdir")}')
        rprint(f'\tPython dependencies: {version.get("python_dependencies")}')
        rprint(f'\tSystem dependencies: {version.get("system_dependencies")}')
        rprint(f'\tPlugin dependencies: {version.get("plugin_dependencies")}')
