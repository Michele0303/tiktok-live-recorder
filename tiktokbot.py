import time
import requests as req
import re
import os
from enums import Mode, Error, StatusCode, TimeOut
import shutil
import ffmpeg

class TikTok:

    def __init__(self, output, mode, user=None, room_id=None):
        self.output = output
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

    def convertion_mp4(self, file):
        """
        Convert the video from flv format to mp4 format
        """
        try:
            ffmpeg.input(file).output(file.replace('_flv.mp4', '.mp4'), y='-y').run()
            os.remove(file)
            print("Finished converting {}".format(file))
        except FileNotFoundError:
            print("[-] FFmpeg is not installed.")

    def start_recording(self):
        """
        Start recording live
        """
        live_url = self.get_live_url()
        if not live_url:
            raise ValueError(Error.URL_NOT_FOUND)

        current_date = time.strftime("%Y.%m.%d_%H-%M-%S", time.gmtime())

        if self.output != "" and isinstance(self.output, str) and not ( self.output.endswith('/') or self.output.endswith('\\') ):
            if os.name == 'nt':
                self.output = self.output + "\\"
            else:
                self.output = self.output + "/"

        output = f"{self.output}TK_{self.user}_{current_date}_flv.mp4"

        print("\n[*] STARTED RECORDING... [PRESS ONLY ONCE CTRL + C TO STOP]")

        try:
            response = req.get(live_url, stream=True)
            with open(output, "wb") as out_file:
                shutil.copyfileobj(response.raw, out_file)
        except KeyboardInterrupt:
            pass

        print(f"FINISH: {output}\n")

        print("Do you want to convert it to real mp4? [Requires ffmpeg installed]")
        print("Y/N -> ", end="")
        if input() == "Y" or "y":
            self.convertion_mp4(output)

        #cmd = f"streamlink {live_url} best -o {output}"
        #cmd = f"youtube-dl --hls-prefer-ffmpeg --no-continue --no-part -o {output} {live_url}"
        '''
        with open("error.log", "w") as error_log, open("info.log", "w") as info:
            p = subprocess.Popen(cmd, stderr=error_log, stdout=info, shell=True)
            signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))
            p.communicate()
        '''

    def get_live_url(self) -> str:
        """
        I get the cdn (flv or m3u8) of the streaming
        """
        try:

            url = f"https://webcast.tiktok.com/webcast/room/info/?aid=1988&room_id={self.room_id}"
            json = req.get(url).json()

            live_url_m3u8 = json['data']['stream_url']['hls_pull_url']
            live_url_flv = json['data']['stream_url']['rtmp_pull_url']
            print("[*] URL FLV", live_url_flv)

            return live_url_flv
        except Exception as ex:
            print(ex)

    def is_user_in_live(self) -> bool:
        """
        Checking whether the user is live
        """
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
        except Exception as ex:
            print(ex)

    def get_room_id_from_user(self) -> str:
        """
        Given a username, I get the room_id
        """
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
                f"[-] Unable to find room_id. I'll try again in {TimeOut.CONNECTION_CLOSED} minutes")
            time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)
            return self.get_room_id_from_user()
        except AttributeError:
            if self.mode != Mode.AUTOMATIC:
                raise AttributeError(Error.USERNAME_ERROR)
            time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)
        except Exception as ex:
            print(ex)

    def get_user_from_room_id(self) -> str:
        """
        Given a room_id, I get the username
        """
        try:
            url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={self.room_id}"
            content = req.get(url).text

            if "LiveRoomInfo" not in content:
                raise AttributeError(Error.USERNAME_ERROR)

            return re.search('uniqueId":"(.*?)",', content).group(1)
        except Exception as ex:
            print(ex)

    def is_country_blacklisted(self) -> bool:
        """
        Checks if the user is in a blacklisted country that requires login
        """
        try:
            response = req.get(f"https://www.tiktok.com/@{self.user}/live", allow_redirects=False)
            return response.status_code == StatusCode.REDIRECT
        except Exception as ex:
            print(ex)
