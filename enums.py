from enum import Enum, IntEnum


class TimeOut(IntEnum):
    def __mul__(self, operator):
        return self.value * operator

    ONE_MINUTE = 60
    AUTOMATIC_MODE = 5
    CONNECTION_CLOSED = 2


class StatusCode(IntEnum):
    OK = 200
    REDIRECT = 302


class Mode(IntEnum):
    MANUAL = 0
    AUTOMATIC = 1


class Error(Enum):
    def __str__(self):
        return str(self.value)

    AUTOMATIC_MODE_ERROR: str = "[*] Automatic mode can be used only in unblacklisted country. Use a VPN\n[*] " \
                                "Unrestricted country list: " \
                                "https://github.com/Michele0303/TikTok-Live-Recorder/edit/main/GUIDE.md#unrestricted" \
                                "-country"

    HTTP_ERROR = "[*] Captcha require or country blocked. Use a vpn or room_id." \
                 "\n[+] How to get room id: https://github.com/Michele0303/TikTok-Live-Recorder/blob/main/GUIDE.md#how-to-get-room_id" \
                 "\n[+] Unrestricted country list: https://github.com/Michele0303/TikTok-Live-Recorder/edit/main/GUIDE" \
                 ".md#unrestricted-country"

    USERNAME_ERROR = "[*] Error: Username/Room_id not found or the user has never been in live"

    CONNECTION_CLOSED = "[*] Connection broken by the server."
    CONNECTION_CLOSED_AUTOMATIC = f"{CONNECTION_CLOSED}. Try again after Delay of {TimeOut.CONNECTION_CLOSED} minutes"


class Info(Enum):
    def __str__(self):
        return str(self.value)

    VERSION = 2.3

    BANNER = f"""

  _____ _ _   _____    _     _    _           ___                   _         
 |_   _(_) |_|_   _|__| |__ | |  (_)_ _____  | _ \___ __ ___ _ _ __| |___ _ _ 
   | | | | / / | |/ _ \ / / | |__| \ V / -_) |   / -_) _/ _ \ '_/ _` / -_) '_|
   |_| |_|_\_\ |_|\___/_\_\ |____|_|\_/\___| |_|_\___\__\___/_| \__,_\___|_| 

   VERSION: {VERSION}
"""
