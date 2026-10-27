import json
import os

from utils.custom_exceptions import TikTokRecorderError
from utils.enums import Info


def parse_json(response, context="TikTok"):
    """
    Decode a TikTok response body as JSON, with a readable error on failure.

    TikTok answers with an HTML/captcha page, an empty body or a truncated
    payload when a request is rate-limited, blocked by the WAF or when the
    signing service is in a bad state. Calling ``response.json()`` directly on
    such a response raises ``json.JSONDecodeError`` and kills the whole process
    with a traceback that says nothing about the actual cause.

    Args:
        response: object exposing ``json()`` (requests/curl_cffi response).
        context (str): where the response came from, used in the message.

    Raises:
        TikTokRecorderError: when the body is not valid JSON.
    """
    try:
        payload = response.json()
    except ValueError as ex:  # JSONDecodeError is a ValueError
        body = getattr(response, "text", "") or ""
        snippet = " ".join(str(body).split())[:120]
        detail = f" ({snippet!r})" if snippet else " (empty body)"
        raise TikTokRecorderError(
            f"{context}: TikTok returned a non-JSON response{detail}. "
            "This usually means the request was blocked or rate-limited; "
            "retry later, use a proxy (-proxy) or add cookies (cookies.json)."
        ) from ex

    if not isinstance(payload, dict):
        raise TikTokRecorderError(
            f"{context}: unexpected JSON payload ({type(payload).__name__})"
        )

    return payload


def banner() -> None:
    """
    Prints a banner with the name of the tool and its version number.
    """
    print(Info.BANNER, flush=True)


def read_cookies():
    """
    Loads the config file and returns it.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "..", "cookies.json")
    with open(config_path, "r") as f:
        return json.load(f)


def read_telegram_config():
    """
    Loads the telegram config file and returns it.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "..", "telegram.json")
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
