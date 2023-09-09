import git
import shutil
import os
import sys
import json
from rich import print as rprint
import re

def get_plugins_registry():
    current_module_dir = os.path.dirname(__file__)
    json_file_path = os.path.join(current_module_dir, "../plugins-registry.json")
    try:
        registry_json=open(json_file_path,"r")
        registry_dict = json.load(registry_json)
        registry_json.close()
        return registry_dict
    except Exception as e:
        rprint(f"[red bold]An error occurred reading the registry:[/red bold] {e}")
        sys.exit(1)

def download_plugin_from_repo_tag(repo_url, tag_name, subdir, target_path):
    download_repo_dir = "/tmp/temp_repo"
    try:
        if shutil.os.path.exists(download_repo_dir):
            shutil.rmtree(download_repo_dir)
        git.Repo.clone_from(repo_url, download_repo_dir)
        repo = git.Repo(download_repo_dir)
    except git.GitCommandError as e:
        rprint(f'[red]Unable to download plugin repository "{repo_url}" into "{download_repo_dir}"[/red]')
        print(e)
        sys.exit(1)
    try:
        repo.git.checkout(tag_name)
    except git.GitCommandError as e:
        rprint(f'[red]The tag {tag_name} was not found on the target plugin repository[/red]')
        shutil.rmtree(download_repo_dir) # Cleanup downloaded folders
        print(e)
        sys.exit(1)
    source_path = os.path.join(download_repo_dir, subdir)
    if shutil.os.path.exists(target_path):
        shutil.rmtree(target_path)
    shutil.copytree(source_path, target_path)
    shutil.rmtree(download_repo_dir)

def version_to_tuple(version_str):
    """
    Function to convert a version semver string to a tuple for comparison
    Ex: "1.2.3" -> (1,2,3)
    """
    return tuple(map(int, re.findall(r'\d+', version_str)))

def get_latest_plugin_version_number(plugin_versions: dict):
    """
    Takes the dict of versions of a plugin and returns the max version number
    """
    latest_version = get_latest_plugin_version_dict(plugin_versions)
    return latest_version.get("version")

def get_latest_plugin_version_dict(plugin_versions: dict):
    """
    Takes the dict of versions of a plugin and returns the max version dict
    """
    latest_version = next((v for v in plugin_versions if v["latest"]), None)
    return latest_version