import os
from pathlib import Path
import requests
import zipfile
import shutil

URL = "https://raw.githubusercontent.com/Michele0303/tiktok-live-recorder/main/src/utils/enums.py"
URL_REPO = "https://github.com/Michele0303/tiktok-live-recorder/archive/refs/heads/main.zip"
FILE_TEMP = "enums_temp.py"
FILE_NAME_UPDATE = URL_REPO.split("/")[-1]


def delete_tmp_file():
    try:
        os.remove(FILE_TEMP)
    except:
        pass

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
        delete_tmp_file()
        print("The temporary file does not exist.")
        return False

    try:
        from enums_temp import Info
        from utils.enums import Info as InfoOld
    except ImportError:
        print("Error importing the file or missing module.")
        delete_tmp_file()
        return False

    if float(Info.__str__(Info.VERSION)) != float(InfoOld.__str__(InfoOld.VERSION)):
        print(Info.BANNER)
        print(f"Current version: {InfoOld.__str__(InfoOld.VERSION)}\nNew version available: {Info.__str__(Info.VERSION)}")
        print("\nNew features:")
        for feature in Info.NEW_FEATURES:
            print("*", feature)
    else:
        delete_tmp_file()
        # print("No updates available.")
        return False

    download_file(URL_REPO, FILE_NAME_UPDATE)

    dir_path = Path(__file__).parent
    temp_update_dir = dir_path / "update_temp"

    # Extract content from zip to a temporary update directory
    with zipfile.ZipFile(dir_path / FILE_NAME_UPDATE, "r") as zip_ref:
        zip_ref.extractall(temp_update_dir)

    # Find the extracted folder (it will have the name 'tiktok-live-recorder-main')
    extracted_folder = temp_update_dir / "tiktok-live-recorder-main" / "src"

    # Copy all files and folders from the extracted folder to the main directory
    files_to_preserve = {"check_updates.py", "cookies.json", "telegram.json"}
    for item in extracted_folder.iterdir():
        source = item
        destination = dir_path / item.name

        # Skip overwriting the files we want to preserve
        if source.name in files_to_preserve:
            continue

        # If it's a file, overwrite it
        if source.is_file():
            shutil.copy2(source, destination)
        # If it's a directory, copy its contents file by file
        elif source.is_dir():
            for sub_item in source.rglob('*'):
                sub_destination = destination / sub_item.relative_to(source)
                if sub_item.is_file():
                    sub_destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(sub_item, sub_destination)

    # Delete the temporary files and folders
    shutil.rmtree(temp_update_dir)
    try:
        Path(FILE_TEMP).unlink()
    except Exception as e:
        print(f"Failed to remove the temporary file {FILE_TEMP}: {e}")

    delete_tmp_file()

    try:
        Path(FILE_NAME_UPDATE).unlink()
    except Exception as e:
        print(f"Failed to remove the temporary file {FILE_NAME_UPDATE}: {e}")

    return True
