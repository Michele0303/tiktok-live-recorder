from time import gmtime, strftime
import time
import requests as req
import re
import argparse
from argparse import RawTextHelpFormatter
import os

TIMEOUT = 5

def banner() -> None:
    print("""

  _____ _ _   _____    _     _    _           ___                   _         
 |_   _(_) |_|_   _|__| |__ | |  (_)_ _____  | _ \___ __ ___ _ _ __| |___ _ _ 
   | | | | / / | |/ _ \ / / | |__| \ V / -_) |   / -_) _/ _ \ '_/ _` / -_) '_|
   |_| |_|_\_\ |_|\___/_\_\ |____|_|\_/\___| |_|_\___\__\___/_| \__,_\___|_|  
                                                                              

""")

def get_room_id(user: str) -> str:
    tiktok_url = f"https://www.tiktok.com/@{user}/live"
    try:
        response = req.get(tiktok_url)
        response.raise_for_status()
        content = response.text
        return re.search("room_id=(.*?)\"/>", content).group(1)
    except req.HTTPError:
        print("[*] Captcha require or country blocked. Use a vpn or room_id.\n")
        print("[+] How to get room id: https://github.com/Michele0303/TikTok-Live-Recorder/blob/main/GUIDE.md#how-to-get-room_id")
        print("[+] Unrestricted country list: https://github.com/Michele0303/TikTok-Live-Recorder/edit/main/GUIDE.md#unrestricted-country")
    except AttributeError:
        print("[*] Error: Username not found or the user has never been in live")
    exit(1)

def get_user_from_room_id(room_id: str) -> str:
    url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={room_id}"
    content = req.get(url).text

    if "LiveRoomInfo" not in content:
        raise Exception("[*] Incorrect Room_Id or the user has never been in live")

    return re.search('uniqueId":"(.*?)",', content).group(1)


def is_user_in_live(room_id: str) -> bool:
    url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={room_id}"
    content = req.get(url).text

    return '"status":2' in content


def get_live_url(room_id: str) -> str:
    url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={room_id}"
    content = req.get(url).text

    live_url_m3u8 = re.search('"liveUrl":"(.*?)"', content).group(1).replace("https", "http")
    print("[*] URL M3U8", live_url_m3u8)
    return live_url_m3u8


def start_recording(user: str, room_id: str) -> None:
    live_url = get_live_url(room_id)

    current_date = strftime("%Y.%m.%d_%H-%M-%S", gmtime())
    output = f"TK_{user}_{current_date}.mp4"

    print("\n[*] RECORDING... ")
    
    os.system(f"youtube-dl.exe --hls-prefer-ffmpeg --no-continue --no-part -o {output} {live_url}")

    print(f"[*] FINISH {output}")


def main():
    banner()

    user: str
    mode: str
    room_id: str

    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument("-user",
                        dest="user",
                        help="record a live from the username.",
                        action='store')
    parser.add_argument("-room_id",
                        dest="room_id",
                        help="record a live from the room_id.",
                        action='store')
    parser.add_argument("-mode",
                        dest="mode",
                        help="recording mode: (manual,automatic) [Default: manual]\n[manual] => manual live recording\n[automatic] => automatic live recording when the user is in live).",
                        default="manual",
                        action='store')
    args = parser.parse_args()

    try:
        if not args.user and not args.room_id:
            raise Exception("[*] Missing user/room_id value")
        if args.mode and args.mode != "manual" and args.mode != "automatic":
            raise Exception("[*] Incorrect -mode value")
        if args.user and args.room_id:
            raise Exception("[*] Enter the username or room_id, not both.")

        if args.user:
            user = args.user
            room_id = get_room_id(user)
        else:
            room_id = args.room_id
            user = get_user_from_room_id(room_id)
            
        mode = args.mode

        print("[*] USERNAME:", user)
        print("[*] ROOM_ID:", room_id)

        if mode == "manual":
            if not is_user_in_live(room_id):
                print(f"\n[*] {user} is offline")
                exit(0)

            start_recording(user, room_id)

        if mode == "automatic":
            while True:
                if not is_user_in_live(room_id):
                    print(f"\n[*] {user} is offline")
                    print(f"waiting {TIMEOUT} minutes before recheck")
                    time.sleep(TIMEOUT * 60)
                    continue
                
                start_recording(user, room_id)
    except Exception as ex:
        print(ex)

if __name__ == '__main__':
    main()
