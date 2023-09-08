import os
import sys
import typer
from rich import print as rprint

from pipeless_ai_cli.lib.pip import install_pip_packages
from pipeless_ai_cli.lib.plugins import get_latest_plugin_version_number, get_plugins_registry, download_plugin_from_repo_tag

app = typer.Typer()

@app.command(name="plugin", help="Install a plugin")
def install_plugin(id: str, version: str = None, plugins_root: str = 'plugins'):
    if not os.path.exists('app.py'):
        rprint("[red]Unable to find 'app.py'. This command must be executed from the root of your Pipeless project[/red]")
        sys.exit(1)

    rprint(f"[yellow bold]Installing plugin with ID: {id}[/yellow bold]")
    plugins_registry = get_plugins_registry()
    install_success = False
    for plugin in plugins_registry['plugins']:
        if plugin.get("id") == id:
            plugin_versions = plugin.get("versions")
            if version is None:
                # Default to latest version if no version specified
                version = get_latest_plugin_version_number(plugin_versions)
                rprint(f'[yellow]No version specified, installing latest version: {version}[/yellow]')

            # Install the version
            for plugin_version in plugin_versions:
                if plugin_version.get('version') == version:
                    repo_url = plugin_version.get("repo_url")
                    tag_name = plugin_version.get("version")
                    subdir = plugin_version.get("subdir")
                    download_plugin_from_repo_tag(repo_url, tag_name, subdir, f'{plugins_root}/{id}')
                    install_success = True
                    python_deps = plugin_version.get("python_dependencies")
                    install_pip_packages(python_deps)
                    system_deps = plugin_version.get("system_dependencies")
                    if len(system_deps) > 0:
                        rprint(f"[yellow]The plugin {id} requires the following system dependencies, please install them now: {system_deps}[/yellow]")
    if install_success:
        rprint(f'[green]Plugin {id} sucessfully instaled![/green]')
        rprint(f'[yellow]IMPORTANT: Remember to add "{id}" to the plugins execution order either in "config.yaml" or running:\n\t $ export PIPELESS_PLUGINS_ORDER=$PIPELESS_PLUGINS_ORDER,{id}[/yellow]')
    else:
        rprint('[red]The plugin (or plugin version) specified does not exit into the plugins registry[/red]')
