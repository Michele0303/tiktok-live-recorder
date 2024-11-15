from datetime import datetime
import json
from pathlib import Path
import requests

# TODO: "move to a module"

data = {
    "last_date_search": "2024-11-15",
}
URL = "https://raw.githubusercontent.com/Michele0303/tiktok-live-recorder/main/src/utils/enums.py"
URL_REPO = (
    "https://github.com/Michele0303/tiktok-live-recorder/archive/refs/heads/main.zip"
)
FILE_TEMP = "enums_temp.py"
FILE_NAME_UPDATE = URL_REPO.split("/")[-1]


def save_data():
    try:
        with open("data.json", "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=True,
                sort_keys=True,
            )
    except FileNotFoundError:
        print("File not found")


def check_file(path: str):
    if Path(path).exists():
        return True
    return False


def a_week_has_passed() -> bool:
    """check if a week has passed since the last search

    Returns:
        bool: _description_
    """
    try:
        with open("data.json", "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print("File not found")
        return False

    last_date = datetime.strptime(data["last_date_search"], "%Y-%m-%d")
    today = datetime.now()

    if (today - last_date).days >= 7:
        print(today, last_date)
        return True

    return False


def download_file(url: str, file_name: str):
    """download a file from a url

    Args:
        url (str): url to download the file
        file_name (str): name of the file to save
    """
    response = requests.get(url, stream=True)

    if response.status_code == 200:  # 200 OK
        with open(file_name, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)

    else:
        print("Error al descargar el archivo")
        # exit()
        # return False


def check_updates():
    if not check_file("data.json"):
        save_data()
    if not a_week_has_passed():
        return False

    download_file(URL, FILE_TEMP)

    if not check_file(FILE_TEMP):
        print("the file does not exist")
        return False

    try:
        from enums_temp import Info #type: ignore
        from utils.enums import Info as Info_old
        import zipfile

    except ImportError:
        print("Error trying to import the file or missing file or module")
        # exit()
        return False

    if float(Info.__str__(Info.VERSION)) != float(Info_old.__str__(Info_old.VERSION)):
        print(Info.BANNER)
        print(
            f"----- New version available: {Info.__str__(Info.VERSION)}\n----- Current version: {Info_old.__str__(Info_old.VERSION)}"
        )
        print("\nNew features:")
        for feature in Info.NEW_FEACTURES:
            print("*", feature)

        # TODO: "Question: Do you want to update the tool? [Y/n]"
        # exit()
        # return True
    else:
        print("No updates available")
        # print("No hay actualizaciones disponibles")
        return False

    download_file(
        URL_REPO,
        FILE_NAME_UPDATE,
    )

    dir = Path(__file__).parent
    ouput = Path(__file__).parent.parent.parent

    # Extract content zip in the same directory
    with zipfile.ZipFile(dir / FILE_NAME_UPDATE, "r") as zip_ref:
        zip_ref.extractall(ouput)

    # save the date of the last search
    save_data()

    # delete the temporary file
    Path(FILE_TEMP).unlink()
    Path(FILE_NAME_UPDATE).unlink()
    return True

    # alternastivas
    # se actualiza usando los comandos de git
    # se actualiza usando el comnado curl
