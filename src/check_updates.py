import re

import requests

URL = "https://raw.githubusercontent.com/Michele0303/tiktok-live-recorder/main/src/utils/enums.py"
RELEASES_URL = "https://github.com/Michele0303/tiktok-live-recorder/releases"


def _fetch_remote_version_info() -> dict | None:
    """
    Fetch the raw enums.py source from the main branch and pull the VERSION /
    NEW_FEATURES values out of it with regex.

    This deliberately does NOT execute or import the downloaded file, and
    does NOT download/extract a source zip over the local install like the
    previous updater did. Importing remote code and overwriting local files
    based on a network response is a supply-chain risk: a compromised repo,
    a tampered response (e.g. on a hostile network), or even an accidental
    bad push to `main` could run arbitrary code on the user's machine, and
    it also made installs non-reproducible. This function only reads plain
    text to decide whether a newer version exists; it changes nothing.
    """
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as ex:
        print(f"Could not check for updates: {ex}")
        return None

    text = response.text

    version_match = re.search(r'VERSION\s*=\s*"([^"]+)"', text)
    if not version_match:
        return None

    features = []
    features_block_match = re.search(r"NEW_FEATURES\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if features_block_match:
        features = re.findall(r'"((?:[^"\\]|\\.)*)"', features_block_match.group(1))

    return {"version": version_match.group(1), "features": features}


def _parse_version(v) -> tuple[int, ...]:
    """
    Parse a version string like "7.7.1" or "7.7.1-rc1" into a tuple of ints
    for ordinal comparison.

    Each dot-separated chunk is reduced to its leading digits (0 if a chunk
    has none), so this never raises on unexpected input and never mixes
    float/int tuples of different lengths/types the way the previous
    float(str(v)) implementation did (which also silently collapsed
    distinct versions like "7.10" and "7.1" into the same float, 7.1).
    """
    parts = []
    for chunk in str(v).split("."):
        match = re.match(r"\d+", chunk)
        parts.append(int(match.group()) if match else 0)
    return tuple(parts)


def _is_newer(remote: tuple[int, ...], current: tuple[int, ...]) -> bool:
    """
    True if `remote` is strictly greater than `current`, treating missing
    trailing components as 0 (so (7, 7) == (7, 7, 0)).
    """
    length = max(len(remote), len(current))
    remote = remote + (0,) * (length - len(remote))
    current = current + (0,) * (length - len(current))
    return remote > current


def check_updates() -> bool:
    """
    Check whether a newer version is available on the main branch and, if
    so, print a notice pointing the user to the releases page.

    This function never downloads, imports, or executes remote code, and
    never modifies local files. Installing an update is an explicit, manual
    step left to the user — e.g. reviewing and pulling a tagged/versioned
    release — so a compromised or tampered response can't run code on this
    machine or silently change the installed program.

    Returns:
        bool: Always False. The updater only notifies; it never triggers an
        exit-and-update flow the way the old auto-updater did.
    """
    from utils.enums import Info as CurrentInfo

    remote = _fetch_remote_version_info()
    if remote is None:
        return False

    if not _is_newer(
        _parse_version(remote["version"]), _parse_version(CurrentInfo.VERSION)
    ):
        return False

    print(
        f"Current version: {CurrentInfo.VERSION}\n"
        f"New version available: {remote['version']}"
    )
    if remote["features"]:
        print("\nNew features:")
        for feature in remote["features"]:
            print("*", feature)

    print(
        f"\nTo update, review and install the latest release yourself: {RELEASES_URL}"
    )

    return False
