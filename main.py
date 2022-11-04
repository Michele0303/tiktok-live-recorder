from time import gmtime, strftime
import requests as req
import re


def banner() -> None:
    print("""

  _____ _ _   _____    _     _    _           ___                   _         
 |_   _(_) |_|_   _|__| |__ | |  (_)_ _____  | _ \___ __ ___ _ _ __| |___ _ _ 
   | | | | / / | |/ _ \ / / | |__| \ V / -_) |   / -_) _/ _ \ '_/ _` / -_) '_|
   |_| |_|_\_\ |_|\___/_\_\ |____|_|\_/\___| |_|_\___\__\___/_| \__,_\___|_|  
                                                                              

""")


def get_room_id(user: str) -> str:
    tiktok_url = f"https://www.tiktok.com/@{user}/live"
    url = "https://base64.guru:443/tools/http-request-online"
    data = {"form_is_submited": "base64-tools-http-request-online", "form_action_url": "/tools/http-request-online",
            "url": tiktok_url, "http_method": "GET", "http_version": "1_0",
            "http_headers": '', "http_body": '', "execute_http_request": "1"}
    try:
        content = req.post(url, data=data).text
        return re.search("room_id=(.*?)&", content).group(1)
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


def start_recording(live_url: str, output: str) -> None:
    print("\n[*] RECORDING... ")
    stream = req.get(live_url, stream=True, verify=False, timeout=15)
    open(output, "wb").write(stream.content)

    print(f"[*] FINISH {output}")


def main():
    banner()

    print("USERNAME-> ", end='')
    user = input()

    room_id = get_room_id(user)
    print("[*] ROOM_ID:", room_id)
    if not is_user_in_live(room_id):
        print(f"\n[*] {user} is offline")
        exit(0)

    live_url_m3u8 = get_live_url(room_id)
    live_url_flv = live_url_m3u8.replace("pull-hls", "pull-flv").replace("/playlist.m3u8", ".flv").replace("https", "http").replace(".m3u8", ".flv")
    print("[*] URL M3U8", live_url_m3u8)
    print("[*] URL FLV", live_url_flv)

    current_date = strftime("%Y.%m.%d_%H-%M-%S", gmtime())
    output = f"TK_{user}_{current_date}.flv"
    start_recording(live_url_flv, output)


if __name__ == '__main__':
    main()
