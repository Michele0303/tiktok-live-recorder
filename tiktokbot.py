import time
import requests as req
import re
import os
import ffmpeg
import sys

from enums import Mode, Error, StatusCode, TimeOut


class TikTok:

    def __init__(self, output, mode, logger, user=None, room_id=None, use_ffmpeg=None, duration=None, convert=False):
        self.output = output
        self.user = user
        self.mode = mode
        self.room_id = room_id
        self.use_ffmpeg = use_ffmpeg
        self.duration = duration
        self.convert = convert
        self.logger = logger

        if self.user is None:
            self.user = self.get_user_from_room_id()
        if self.room_id is None:
            self.room_id = self.get_room_id_from_user()

        self.logger.info(f"USERNAME: {self.user}")
        self.logger.info(f"ROOM_ID:  {self.room_id}")

        is_blacklisted = self.is_country_blacklisted()
        if mode == Mode.AUTOMATIC and is_blacklisted:
            raise ValueError(Error.AUTOMATIC_MODE_ERROR)

    def run(self):
        """
        runs the program in the selected mode. 
        
        If the mode is MANUAL, it checks if the user is currently live and if so, starts recording. 
        
        If the mode is AUTOMATIC, it continuously checks if the user is live and if not, waits for the specified timeout before rechecking.
        If the user is live, it starts recording.
        """
        if self.mode == Mode.MANUAL:
            if not self.is_user_in_live():
                self.logger.info(f"{self.user} is offline\n")
                exit(0)

            self.start_recording()

        if self.mode == Mode.AUTOMATIC:
            while True:
                self.room_id = self.get_room_id_from_user()
                if not self.is_user_in_live():
                    self.logger.info(f"{self.user} is offline")
                    self.logger.info(f"waiting {TimeOut.AUTOMATIC_MODE} minutes before recheck\n")
                    time.sleep(TimeOut.AUTOMATIC_MODE * TimeOut.ONE_MINUTE)
                    continue

                self.start_recording()

    def convertion_mp4(self, file):
        """
        Convert the video from flv format to mp4 format
        """
        try:
            self.logger.info("Converting {} to MP4 format...".format(file))
            ffmpeg.input(file).output(file.replace('_flv.mp4', '.mp4'), y='-y').run(quiet=True)
            os.remove(file)
            self.logger.info("Finished converting {}".format(file))
        except FileNotFoundError:
            self.logger.error("FFmpeg is not installed.")

    def start_recording(self):
        """
        Start recording live
        """
        live_url = self.get_live_url()
        if not live_url:
            raise ValueError(Error.URL_NOT_FOUND)

        current_date = time.strftime("%Y.%m.%d_%H-%M-%S", time.gmtime())

        if self.output != "" and isinstance(self.output, str) and not (
                self.output.endswith('/') or self.output.endswith('\\')):
            if os.name == 'nt':
                self.output = self.output + "\\"
            else:
                self.output = self.output + "/"

        output = f"{self.output if self.output else ''}TK_{self.user}_{current_date}_flv.mp4"

        print("")
        (
            self.logger.info(f"START RECORDING FOR {self.duration} SECONDS ")
            if self.duration else self.logger.info("STARTED RECORDING...")
        )

        try:
            if self.use_ffmpeg:
                self.logger.info("[PRESS 'q' TO STOP RECORDING]")
                stream = ffmpeg.input(live_url)

                if self.duration is not None:
                    stream = ffmpeg.output(stream, output.replace("_flv.mp4", ".mp4"), c='copy', t=self.duration)
                else:
                    stream = ffmpeg.output(stream, output.replace("_flv.mp4", ".mp4"), c='copy')

                ffmpeg.run(stream, quiet=True)
            else:
                self.logger.info("[PRESS ONLY ONCE CTRL + C TO STOP]")
                response = req.get(live_url, stream=True)
                with open(output, "wb") as out_file:
                    start_time = time.time()
                    for chunk in response.iter_content(chunk_size=4096):
                        out_file.write(chunk)
                        elapsed_time = time.time() - start_time
                        if self.duration is not None and elapsed_time >= self.duration:
                            break

        except ffmpeg.Error as e:
            self.logger.error('FFmpeg Error:')
            self.logger.error(e.stderr.decode('utf-8'))

        except FileNotFoundError:
            self.logger.error("FFmpeg is not installed")
            sys.exit(1)
        except KeyboardInterrupt:
            pass

        self.logger.info(f"FINISH: {output}\n")

        if self.use_ffmpeg:
            return

        if not self.convert:
            self.logger.info("Do you want to convert it to real mp4? [Requires ffmpeg installed]")
            choice = input("Y/N -> ")
            if choice.lower() == "y":
                self.convertion_mp4(output)
        else:
            self.convertion_mp4(output)

    def get_live_url(self) -> str:
        """
        I get the cdn (flv or m3u8) of the streaming
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://www.tiktok.com/",
            }
            url = f"https://webcast.tiktok.com/webcast/room/info/?aid=1988&room_id={self.room_id}"
            json = req.get(url, headers=headers).json()

            # live_url_m3u8 = json['data']['stream_url']['hls_pull_url']
            live_url_flv = json['data']['stream_url']['rtmp_pull_url']
            self.logger.info(f"LIVE URL: {live_url_flv}")

            return live_url_flv
        except Exception as ex:
            self.logger.error(ex)

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
                self.logger.error(Error.CONNECTION_CLOSED)
            else:
                self.logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)
            return False
        except Exception as ex:
            self.logger.error(ex)

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

            return re.findall("room_id=(.*?)\"/>", content)[0]
        except req.HTTPError:
            raise req.HTTPError(Error.BLACKLIST_ERROR)
        except ValueError:
            self.logger.error(f"Unable to find room_id. I'll try again in {TimeOut.CONNECTION_CLOSED} minutes")
            time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)
            return self.get_room_id_from_user()
        except AttributeError:
            if self.mode != Mode.AUTOMATIC:
                raise AttributeError(Error.USERNAME_ERROR)
            time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)
        except Exception as ex:
            self.logger.error(ex)

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
            self.logger.error(ex)

    def is_country_blacklisted(self) -> bool:
        """
        Checks if the user is in a blacklisted country that requires login
        """
        try:
            response = req.get(f"https://www.tiktok.com/@{self.user}/live", allow_redirects=False)
            return response.status_code == StatusCode.REDIRECT
        except Exception as ex:
            self.logger.error(ex)
