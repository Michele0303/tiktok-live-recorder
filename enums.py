from enum import Enum, IntEnum


class Regex(Enum):

    def __str__(self):
        return str(self.value)

    IS_TIKTOK_LIVE = ".*www\.tiktok\.com.*|.*vm\.tiktok\.com.*"


class TimeOut(IntEnum):
    """ 
    Enumeration that defines timeout values. 
    """

    def __mul__(self, operator):
        return self.value * operator

    ONE_MINUTE = 60
    AUTOMATIC_MODE = 5
    CONNECTION_CLOSED = 2


class StatusCode(IntEnum):
    OK = 200
    REDIRECT = 302
    MOVED = 301


class Mode(IntEnum):
    """
    Enumeration that represents the recording modes.
    """
    MANUAL = 0
    AUTOMATIC = 1


class Error(Enum):
    """
    Enumeration that contains possible errors while using TikTok-Live-Recorder.
    """

    def __str__(self):
        return str(self.value)

    AUTOMATIC_MODE_ERROR: str = "[-] Automatic mode can be used only in unblacklisted country. Use a VPN\n[*] " \
                                "Unrestricted country list: " \
                                "https://github.com/Michele0303/TikTok-Live-Recorder/edit/main/GUIDE.md#unrestricted" \
                                "-country"

    BLACKLIST_ERROR = "[-] Captcha require or country blocked. Use a vpn or room_id." \
                      "\n[-] How to get room id: https://github.com/Michele0303/TikTok-Live-Recorder/blob/main/GUIDE.md#how-to-get-room_id" \
                      "\n[-] Unrestricted country list: https://github.com/Michele0303/TikTok-Live-Recorder/edit/main/GUIDE" \
                      ".md#unrestricted-country"

    USERNAME_ERROR = "[-] Error: Username/Room_id not found or the user has never been in live"

    CONNECTION_CLOSED = "[-] Connection broken by the server."
    CONNECTION_CLOSED_AUTOMATIC = f"{CONNECTION_CLOSED}. Try again after Delay of {TimeOut.CONNECTION_CLOSED} minutes"

    URL_NOT_FOUND = "[-] Unable to find stream url."
    LIVE_NOT_FOUND = "The link provided is not a live tiktok"


class Info(Enum):
    """
    Enumeration that defines the version number and the banner message.
    """

    def __str__(self):
        return str(self.value)

    VERSION = 4.1
    BANNER = f"""

  _____ _ _   _____    _     _    _           ___                   _         
 |_   _(_) |_|_   _|__| |__ | |  (_)_ _____  | _ \___ __ ___ _ _ __| |___ _ _ 
   | | | | / / | |/ _ \ / / | |__| \ V / -_) |   / -_) _/ _ \ '_/ _` / -_) '_|
   |_| |_|_\_\ |_|\___/_\_\ |____|_|\_/\___| |_|_\___\__\___/_| \__,_\___|_| 

   V{VERSION}
"""
