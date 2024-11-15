from pathlib import Path
import requests
import zipfile

URL = "https://raw.githubusercontent.com/Michele0303/tiktok-live-recorder/main/src/utils/enums.py"
URL_REPO = "https://github.com/Michele0303/tiktok-live-recorder/archive/refs/heads/main.zip"
FILE_TEMP = "enums_temp.py"
FILE_NAME_UPDATE = URL_REPO.split("/")[-1]


def check_file(path: str) -> bool:
    """
    Check if a file exists at the given path.

    Args:
        path (str): Path to the file.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    return Path(path).exists()


def download_file(url: str, file_name: str) -> None:
    """
    Download a file from a URL and save it locally.

    Args:
        url (str): URL to download the file from.
        file_name (str): Name of the file to save.
    """
    response = requests.get(url, stream=True)

    if response.status_code == 200:
        with open(file_name, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
    else:
        print("Error downloading the file.")


def check_updates() -> bool:
    """
    Check if there is a new version available and update if necessary.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    download_file(URL, FILE_TEMP)

    if not check_file(FILE_TEMP):
        print("The temporary file does not exist.")
        return False

    try:
        from enums_temp import Info
        from utils.enums import Info as InfoOld
    except ImportError:
        print("Error importing the file or missing module.")
        return False

    if float(Info.__str__(Info.VERSION)) != float(InfoOld.__str__(InfoOld.VERSION)):
        print(Info.BANNER)
        print(f"Current version: {InfoOld.__str__(InfoOld.VERSION)}\nNew version available: {Info.__str__(Info.VERSION)}")
        print("\nNew features:")
        for feature in Info.NEW_FEATURES:
            print("*", feature)
    else:
        print("No updates available.")
        return False

    download_file(URL_REPO, FILE_NAME_UPDATE)

    dir_path = Path(__file__).parent
    output_path = dir_path.parent.parent.parent

    # Extract content from zip in the parent directory
    with zipfile.ZipFile(dir_path / FILE_NAME_UPDATE, "r") as zip_ref:
        zip_ref.extractall(output_path)

    # Delete the temporary files
    Path(FILE_TEMP).unlink()
    Path(FILE_NAME_UPDATE).unlink()
    return True
