import json
import os

from utils.enums import Info

# cookies.json / telegram.json hold user-specific secrets (session cookies,
# Telegram API credentials) and are intentionally NOT committed to the repo
# (see .gitignore) to avoid ever accidentally leaking real credentials. To
# keep the app working on a fresh checkout without an extra manual copy
# step, we create an empty template on first run if the file is missing.
DEFAULT_COOKIES = {"sessionid_ss": "", "tt-target-idc": "useast2a"}
DEFAULT_TELEGRAM_CONFIG = {"api_id": "", "api_hash": "", "chat_id": "me"}


def banner() -> None:
    """
    Prints a banner with the name of the tool and its version number.
    """
    print(Info.BANNER, flush=True)


def _load_or_create_json_config(filename: str, default: dict) -> dict:
    """
    Load a local JSON config file from the project root's `src/` directory,
    creating it from `default` if it doesn't exist yet.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "..", filename)

    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            json.dump(default, f, indent=2)
            f.write("\n")
        return dict(default)

    with open(config_path, "r") as f:
        return json.load(f)


def read_cookies():
    """
    Loads cookies.json, creating an empty template on first run.
    """
    return _load_or_create_json_config("cookies.json", DEFAULT_COOKIES)


def read_telegram_config():
    """
    Loads telegram.json, creating an empty template on first run.
    """
    return _load_or_create_json_config("telegram.json", DEFAULT_TELEGRAM_CONFIG)


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
