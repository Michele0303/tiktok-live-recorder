import json
import os

from utils.enums import Info


def banner() -> None:
    """
    Prints a banner with the name of the tool and its version number.
    """
    print(Info.BANNER, flush=True)

def get_configfile_path(config_path, filename):
    """
    Creates the absolute path of the given config file
    """
    if config_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, "..", filename)
    else:
        return os.path.join(config_path, filename)

def read_cookies(config_path):
    """
    Loads the config file and returns it.
    """
    config_path = get_configfile_path(config_path, "cookies.json")
    with open(config_path, "r") as f:
        return json.load(f)


def read_telegram_config(config_path):
    """
    Loads the telegram config file and returns it.
    """
    config_path = get_configfile_path(config_path, "telegram.json")
    with open(config_path, "r") as f:
        return json.load(f)


def is_termux() -> bool:
    """
    Checks if the script is running in Termux.

    Returns:
        bool: True if running in Termux, False otherwise.
    """
    import distro
    import platform

    return platform.system().lower() == "linux" and distro.like() == ""


def is_windows() -> bool:
    """
    Checks if the script is running on Windows.

    Returns:
        bool: True if running on Windows, False otherwise.
    """
    import platform

    return platform.system().lower() == "windows"


def is_linux() -> bool:
    """
    Checks if the script is running on Linux.

    Returns:
        bool: True if running on Linux, False otherwise.
    """
    import platform

    return platform.system().lower() == "linux"
