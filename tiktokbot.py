import time
import requests as req
import re
import os
import subprocess
from enums import Mode, Error, StatusCode, TimeOut


class TikTok:

    def __init__(self, mode, user=None, room_id=None):
        self.user = user
        self.mode = mode
        self.room_id = room_id

        if self.user is None:
            self.user = self.get_user_from_room_id()
        if self.room_id is None:
            self.room_id = self.get_room_id_from_user()

        print(f"[*] USERNAME {self.user}")
        print(f"[*] ROOM_ID {self.room_id}\n")

        is_blacklisted = self.is_country_blacklisted()
        if mode == Mode.AUTOMATIC and is_blacklisted:
            raise ValueError(Error.AUTOMATIC_MODE_ERROR)

    def run(self):
        if self.mode == Mode.MANUAL:
            if not self.is_user_in_live():
                print(f"[*] {self.user} is offline\n")
                exit(0)

            self.start_recording()

        if self.mode == Mode.AUTOMATIC:
            while True:
                self.room_id = self.get_room_id_from_user()
                if not self.is_user_in_live():
                    print(f"[*] {self.user} is offline")
                    print(f"waiting {TimeOut.AUTOMATIC_MODE} minutes before recheck\n")
                    time.sleep(TimeOut.AUTOMATIC_MODE * TimeOut.ONE_MINUTE)
                    continue

                self.start_recording()

    def start_recording(self):

        live_url = self.get_live_url()

        current_date = time.strftime("%Y.%m.%d_%H-%M-%S", time.gmtime())
        output = f"TK_{self.user}_{current_date}.mp4"

        print("\n[*] RECORDING... [PRESS *ONLY ONCE* CTRL + C TO STOP]")

        cmd = f"youtube-dl --hls-prefer-ffmpeg --no-continue --no-part -o {output} {live_url}"
        with open(os.devnull, 'w') as tempf:
            p = subprocess.Popen(cmd, stderr=tempf, stdout=tempf, shell=True)
            p.communicate()

        print(f"[*] FINISH {output}")

    def get_live_url(self) -> str:
        url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={self.room_id}"
        content = req.get(url).text

        live_url_m3u8 = re.search('"liveUrl":"(.*?)"', content).group(1).replace("https", "http")
        print("[*] URL M3U8", live_url_m3u8)
        return live_url_m3u8

    def is_user_in_live(self) -> bool:
        try:
            url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={self.room_id}"
            content = req.get(url).text

            return '"status":4' not in content
        except ConnectionAbortedError:
            if self.mode == Mode.MANUAL:
                print(Error.CONNECTION_CLOSED)
            else:
                print(Error.CONNECTION_CLOSED_AUTOMATIC)
                time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)
            return False

    def get_room_id_from_user(self) -> str:
        try:
            response = req.get(f"https://www.tiktok.com/@{self.user}/live", allow_redirects=False)
            if response.status_code == StatusCode.REDIRECT:
                raise req.HTTPError()

            content = response.text
            if "room_id" not in content:
                raise ValueError()

            return re.search("room_id=(.*?)\"/>", content).group(1)
        except req.HTTPError:
            raise req.HTTPError(Error.HTTP_ERROR)
        except ValueError:
            print(
                f"[-] Unable to find room_id. I'll try again in {TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE} minutes")
            time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)
            return self.get_room_id_from_user()
        except AttributeError:
            if self.mode != Mode.AUTOMATIC:
                raise AttributeError(Error.USERNAME_ERROR)
            time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

    def get_user_from_room_id(self) -> str:
        url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={self.room_id}"
        content = req.get(url).text

        if "LiveRoomInfo" not in content:
            raise AttributeError(Error.USERNAME_ERROR)

        return re.search('uniqueId":"(.*?)",', content).group(1)

    def is_country_blacklisted(self) -> bool:
        response = req.get(f"https://www.tiktok.com/@{self.user}/live", allow_redirects=False)
        return response.status_code == StatusCode.REDIRECT
