from time import gmtime, strftime
import time
import requests as req
import re
import argparse
from argparse import RawTextHelpFormatter

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
        print("[*] Captcha require or country blocked. Use a vpn")
    except AttributeError:
        print("[*] Error: Username not found")
    exit(1)


def is_user_in_live(room_id: str) -> bool:
    url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={room_id}"
    content = req.get(url).text

    return '"status":2' in content


def get_live_url(room_id: str) -> str:
    url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={room_id}"
    content = req.get(url).text

    return re.search('"liveUrl":"(.*?)"', content).group(1).replace("https", "http")


def start_recording(user: str, room_id: str) -> None:
    live_url_m3u8 = get_live_url(room_id)
    live_url_flv = live_url_m3u8.replace("pull-hls", "pull-flv").replace("/playlist.m3u8", ".flv").replace("https", "http").replace(".m3u8", ".flv")
    print("[*] URL M3U8", live_url_m3u8)
    print("[*] URL FLV", live_url_flv)

    current_date = strftime("%Y.%m.%d_%H-%M-%S", gmtime())
    output = f"TK_{user}_{current_date}.flv"

    print("\n[*] RECORDING... ")
    stream = req.get(live_url_flv, stream=True, verify=False, timeout=15)
    with open(output, "wb") as f:
        for chunk in stream.iter_content():
            f.write(chunk)

    print(f"[*] FINISH {output}")


def main():
    banner()

    user: str
    mode: str

    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument("-user",
                        dest="user",
                        help="record a live from the username.",
                        action='store')
    parser.add_argument("-mode",
                        dest="mode",
                        help="recording mode: (manual,automatic) [Default: manual]\n[manual] => manual live recording\n[automatic] => automatic live recording when the user is in live).",
                        default="manual",
                        action='store')
    args = parser.parse_args()

    if not args.user:
        raise Exception("[*] Missing user value")
    if args.mode and args.mode != "manual" and args.mode != "automatic":
        raise Exception("[*] Incorrect -mode value")
    user = args.user
    mode = args.mode

    room_id = get_room_id(user)
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
                print("waiting 5 minutes before recheck")
                time.sleep(TIMEOUT * 60)
                continue
            
            start_recording(user, room_id)

if __name__ == '__main__':
    main()
