import json
import os
import re
import sys
import time

import ffmpeg

from custom_exceptions import AccountPrivate, CountryBlacklisted, \
    LiveNotFound, UserNotLiveException, IPBlockedByWAF, LiveRestriction
from enums import Mode, Error, StatusCode, TimeOut
from http_client import HttpClient


class TikTok:

    def __init__(self, httpclient, output, mode, logger, cookies, url=None,
                 user=None, room_id=None, use_ffmpeg=None, duration=None,
                 convert=False):

        # TikTok
        self.url = url
        self.user = user
        self.room_id = room_id

        # Tool Settings
        self.httpclient = httpclient.req
        self.mode = mode
        self.cookies = cookies

        # Recording Settings
        self.use_ffmpeg = use_ffmpeg
        self.duration = duration
        self.convert = convert

        # Output & Results
        self.output = output
        self.logger = logger

        # Check if the user's country is blacklisted
        is_blacklisted = self.is_country_blacklisted()
        if is_blacklisted:
            if room_id is None:
                raise CountryBlacklisted(Error.BLACKLIST_ERROR)
            if mode == Mode.AUTOMATIC:
                raise ValueError(Error.AUTOMATIC_MODE_ERROR)

        # Get live information based on the provided user data
        if self.url is not None:
            self.get_room_and_user_from_url()
                     
        if self.user is None:
            self.user = self.get_user_from_room_id()

        if self.room_id is None:
            self.room_id = self.get_room_id_from_user()

        self.logger.info(f"USERNAME: {self.user}")
        if self.room_id == "":
            self.logger.info(f"ROOM_ID: {Error.USER_NEVER_BEEN_LIVE}")
        else:
            self.logger.info(f"ROOM_ID:  {self.room_id}")

        # Create a new httpclient without proxy
        self.httpclient = HttpClient(
            self.logger, cookies=self.cookies, proxy=None
        ).req

    def run(self):
        """
        runs the program in the selected mode. 
        
        If the mode is MANUAL, it checks if the user is currently live and if so, starts recording. 
        
        If the mode is AUTOMATIC, it continuously checks if the user is live and if not, waits for the specified timeout before rechecking.
        If the user is live, it starts recording.
        """
        if self.mode == Mode.MANUAL:

            if self.room_id == "":
                raise UserNotLiveException(Error.USER_NEVER_BEEN_LIVE)

            if not self.is_user_in_live():
                raise UserNotLiveException(Error.USER_NOT_CURRENTLY_LIVE)

            self.start_recording()

        if self.mode == Mode.AUTOMATIC:
            while True:

                try:

                    self.room_id = self.get_room_id_from_user()
                    if self.room_id == "":
                        raise UserNotLiveException(Error.USER_NEVER_BEEN_LIVE)

                    if not self.is_user_in_live():
                        raise UserNotLiveException(Error.USER_NOT_CURRENTLY_LIVE)

                    self.start_recording()

                except UserNotLiveException as ex:
                    self.logger.info(ex)
                    self.logger.info(f"waiting {TimeOut.AUTOMATIC_MODE} minutes before recheck\n")
                    time.sleep(TimeOut.AUTOMATIC_MODE * TimeOut.ONE_MINUTE)

                except ConnectionAbortedError:
                    self.logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                    time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

                except Exception as ex:
                    self.logger.error(ex)

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
            self.logger.error("FFmpeg is not installed. -> pip install ffmpeg-python")

    def start_recording(self):
        """
        Start recording live
        """
        live_url = self.get_live_url()
        if not live_url:
            raise LiveNotFound(Error.URL_NOT_FOUND)

        current_date = time.strftime("%Y.%m.%d_%H-%M-%S", time.localtime())

        # TO CHANGE
        if (self.output != "" and isinstance(self.output, str) and not
        (self.output.endswith('/') or self.output.endswith('\\'))):
            if os.name == 'nt':
                self.output = self.output + "\\"
            else:
                self.output = self.output + "/"

        output = f"{self.output if self.output else ''}TK_{self.user}_{current_date}_flv.mp4"

        print("")
        if self.duration:
            self.logger.info(f"START RECORDING FOR {self.duration} SECONDS ")
        else:
            self.logger.info("STARTED RECORDING...")

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
                response = self.httpclient.get(live_url, stream=True)
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
            self.logger.error("FFmpeg is not installed -> pip install ffmpeg-python")
            sys.exit(1)

        except KeyboardInterrupt:
            pass

        self.logger.info(f"FINISH: {output}\n")

        if self.use_ffmpeg:
            return

        if not self.convert:
            self.logger.info("Do you want to convert it to real mp4? [Requires ffmpeg installed] -> pip install ffmpeg-python")
            choice = input("Y/N -> ")
            if choice.lower() == "y":
                self.convertion_mp4(output)
        else:
            self.convertion_mp4(output)

    def get_live_url(self) -> str:
        """
        I get the cdn (flv or m3u8) of the streaming
        """
        url = f"https://webcast.tiktok.com/webcast/room/info/?aid=1988&room_id={self.room_id}"
        data = self.httpclient.get(url).json()

        if 'This account is private' in data:
            raise AccountPrivate

        live_url_flv = data.get(
            'data', {}).get('stream_url', {}).get('rtmp_pull_url', None)

        if live_url_flv is None and data.get('status_code') == 4003110:
            raise LiveRestriction

        self.logger.info(f"LIVE URL: {live_url_flv}")

        return live_url_flv

    def is_user_in_live(self) -> bool:
        """
        Checking whether the user is live.
        """
        data = self.httpclient.get(
            "https://webcast.tiktok.com:443/webcast/room/check_alive/"
            f"?aid=1988&region=CH&room_ids={self.room_id}&user_is_login=true"
        ).json()

        if 'data' not in data or len(data['data']) == 0:
            return False

        return data['data'][0].get('alive', False)

    def get_room_and_user_from_url(self):
        """
        Given a url, get user and room_id.
        """
        response = self.httpclient.get(self.url, allow_redirects=False)
        content = response.text

        if response.status_code == StatusCode.REDIRECT:
            raise CountryBlacklisted('Redirect')

        if response.status_code == StatusCode.MOVED:  # MOBILE URL
            matches = re.findall("com/@(.*?)/live", content)
            if len(matches) < 1:
                raise LiveNotFound(Error.LIVE_NOT_FOUND)

            self.user = matches[0]

        # https://www.tiktok.com/@<username>/live
        match = re.match(
            r"https?://(?:www\.)?tiktok\.com/@([^/]+)/live",
            self.url
        )
        if match:
            self.user = match.group(1)

        self.room_id = self.get_room_id_from_user()

    def get_room_id_from_user(self):
        """
        Given a username, I get the room_id
        """
        content = self.httpclient.get(
            url=f'https://www.tiktok.com/@{self.user}/live'
        ).text

        if 'Please wait...' in content:
            raise IPBlockedByWAF

        pattern = re.compile(
            r'<script id="SIGI_STATE" type="application/json">(.*?)</script>',
            re.DOTALL)
        match = pattern.search(content)

        if not match:
            raise ValueError("[-] Error extracting roomId")

        data = json.loads(match.group(1))

        if 'LiveRoom' not in data and 'CurrentRoom' in data:
            return ""

        room_id = data.get('LiveRoom', {}).get('liveRoomUserInfo', {}).get(
            'user', {}).get('roomId', None)

        if room_id is None:
            raise ValueError("RoomId not found.")

        return room_id

    def get_user_from_room_id(self) -> str:
        """
        Given a room_id, I get the username
        """
        url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={self.room_id}"
        data = self.httpclient.get(url).json()

        unique_id = data.get('LiveRoomInfo', {}).get('ownerInfo', {}).get(
            'uniqueId', None)

        if not unique_id:
            raise AttributeError(Error.USERNAME_ERROR)

        return unique_id

    def is_country_blacklisted(self) -> bool:
        """
        Checks if the user is in a blacklisted country that requires login
        """
        response = self.httpclient.get(
            f"https://www.tiktok.com/@{self.user}/live",
            allow_redirects=False
        )

        return response.status_code == StatusCode.REDIRECT
