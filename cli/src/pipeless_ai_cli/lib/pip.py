import subprocess
import sys
from rich import print as rprint
from packaging.version import Version, parse
from packaging.requirements import Requirement

def install_pip_packages(packages: list[str]):
    """
    Receive a list of packages like ["package1@version", "package2@version"]
    and installs the packages with pip
    """
    rprint("[yellow]Installing Python dependencies...[/yellow]")
    for package in packages:
        if "@" in package:
            package_name, package_version = package.split('@')
            version_specifier = Requirement(package_version)
            version = parse(package_version)

            # If the version specifier is "^", convert it to a compatible version specifier
            if version_specifier.specs and version_specifier.specs[0][0] == "==":
                compatible_version = version.base_version
            else:
                compatible_version = f">={version.base_version}"
        else:
            package_name = package
            compatible_version = ""

        pip_command = ["pip", "install", f"{package_name}{compatible_version}"]

        try:
            subprocess.check_call(pip_command)
            rprint(f"\t[green]Successfully installed {package_name}{compatible_version}[/green]")
        except subprocess.CalledProcessError:
            rprint(f"\t[red]Failed to install pip package {package_name}{compatible_version}[/red]")
            sys.exit(1)