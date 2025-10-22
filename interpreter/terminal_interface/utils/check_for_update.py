from importlib.metadata import version as get_version, PackageNotFoundError
import requests
from packaging import version


def check_for_update():
    # Fetch the latest version from the PyPI API
    response = requests.get(f"https://pypi.org/pypi/open-interpreter/json")
    latest_version = response.json()["info"]["version"]

    # Get the current version using importlib.metadata
    current_version = get_version("open-interpreter")

    # Use packaging.version.parse for proper semantic version comparison
    return version.parse(latest_version) > version.parse(current_version)
