import json
import os
import re
import time
from http.client import HTTPException

from requests import RequestException

from utils.logger_manager import logger
from core.video_management import VideoManagement
from utils.custom_exceptions import LiveNotFound, UserLiveException, \
    IPBlockedByWAF, TikTokException
from utils.enums import Mode, Error, StatusCode, TimeOut, TikTokError
from http_utils.http_client import HttpClient


class TikTok:

    def __init__(
        self,
        httpclient,
        output,
        mode,
        cookies,
        url=None,
        user=None,
        room_id=None,
        duration=None
    ):

        # TikTok
        self.url = url
        self.user = user
        self.room_id = room_id

        # Tool Settings
        self.httpclient = httpclient.req
        self.mode = mode
        self.cookies = cookies

        # Recording Settings
        self.duration = duration

        # Output & Results
        self.output = output

        # Check if the user's country is blacklisted
        is_blacklisted = self.is_country_blacklisted()
        if is_blacklisted:
            if room_id is None:
                raise UserLiveException(TikTokError.COUNTRY_BLACKLISTED)
            if mode == Mode.AUTOMATIC:
                raise ValueError(Error.AUTOMATIC_MODE_ERROR)

        # Get live information based on the provided user data
        if self.url is not None:
            self.get_room_and_user_from_url()
                     
        if self.user is None:
            self.user = self.get_user_from_room_id()

        if self.room_id is None:
            self.room_id = self.get_room_id_from_user()

        logger.info(f"USERNAME: {self.user}" + ("\n" if not self.room_id else ""))
        if self.room_id == "" or self.room_id is None:
            if mode == Mode.MANUAL:
                raise UserLiveException(TikTokError.USER_NOT_CURRENTLY_LIVE)
        else:
            logger.info(f"ROOM_ID:  {self.room_id}" + ("\n" if not self.is_user_in_live() else ""))

        # Create a new httpclient without proxy
        self.httpclient = HttpClient(cookies=self.cookies).req

    def run(self):
        """
        runs the program in the selected mode. 
        
        If the mode is MANUAL, it checks if the user is currently live and
        if so, starts recording.
        
        If the mode is AUTOMATIC, it continuously checks if the user is live
        and if not, waits for the specified timeout before rechecking.
        If the user is live, it starts recording.
        """
        if self.mode == Mode.MANUAL:
            self.manual_mode()

        if self.mode == Mode.AUTOMATIC:
            self.automatic_mode()

    def manual_mode(self):
        if not self.is_user_in_live():
            raise UserLiveException(TikTokError.USER_NOT_CURRENTLY_LIVE)

        self.start_recording()

    def automatic_mode(self):
        while True:
            try:
                self.room_id = self.get_room_id_from_user()

                if self.room_id == '' or not self.is_user_in_live():
                    raise UserLiveException(TikTokError.USER_NOT_CURRENTLY_LIVE)

                self.start_recording()

            except UserLiveException as ex:
                logger.info(ex)
                logger.info(f"Waiting {TimeOut.AUTOMATIC_MODE} minutes before recheck\n")
                time.sleep(TimeOut.AUTOMATIC_MODE * TimeOut.ONE_MINUTE)

            except ConnectionError:
                logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

            except Exception as ex:
                logger.error(f"Unexpected error: {ex}\n")

    def start_recording(self):
        """
        Start recording live
        """
        live_url = self.get_live_url()
        if live_url is None or live_url == '':
            raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

        current_date = time.strftime("%Y.%m.%d_%H-%M-%S", time.localtime())

        if isinstance(self.output, str) and self.output != '':
            if not (self.output.endswith('/') or self.output.endswith('\\')):
                if os.name == 'nt':
                    self.output = self.output + "\\"
                else:
                    self.output = self.output + "/"

        output = f"{self.output if self.output else ''}TK_{self.user}_{current_date}_flv.mp4"

        if self.duration:
            logger.info(f"Started recording for {self.duration} seconds ")
        else:
            logger.info("Started recording...")

        BUFFER_SIZE = 3 * (1024 * 1024)  # 3 MB buffer
        buffer = bytearray()

        logger.info("[PRESS CTRL + C ONCE TO STOP]")
        with open(output, "wb") as out_file:
            stop_recording = False
            while not stop_recording:
                try:
                    if not self.is_user_in_live():
                        logger.info("User is no longer live. Stopping recording.")
                        break

                    response = self.httpclient.get(live_url, stream=True)
                    start_time = time.time()
                    for chunk in response.iter_content(chunk_size=None):
                        if not chunk or len(chunk) == 0:
                            continue

                        buffer.extend(chunk)
                        if len(buffer) >= BUFFER_SIZE:
                            out_file.write(buffer)
                            buffer.clear()

                        elapsed_time = time.time() - start_time
                        if self.duration is not None and elapsed_time >= self.duration:
                            stop_recording = True
                            break

                except ConnectionError:
                    if self.mode == Mode.AUTOMATIC:
                        logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                        time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

                except (RequestException, HTTPException):
                    time.sleep(2)

                except KeyboardInterrupt:
                    logger.info("Recording stopped by user.")
                    stop_recording = True

                except Exception as ex:
                    logger.error(f"Unexpected error: {ex}\n")
                    stop_recording = True

                finally:
                    if buffer:
                        out_file.write(buffer)
                        buffer.clear()

        logger.info(f"Recording finished: {output}\n")

        VideoManagement.convert_flv_to_mp4(output)

    def get_live_url(self) -> str:
        """
        I get the cdn (flv or m3u8) of the streaming
        """
        url = f"https://webcast.tiktok.com/webcast/room/info/?aid=1988&room_id={self.room_id}"
        data = self.httpclient.get(url).json()

        if 'This account is private' in data:
            raise UserLiveException(TikTokError.ACCOUNT_PRIVATE)

        live_url_flv = data.get(
            'data', {}).get('stream_url', {}).get('rtmp_pull_url', None)

        if live_url_flv is None and data.get('status_code') == 4003110:
            raise UserLiveException(TikTokError.LIVE_RESTRICTION)

        logger.info(f"LIVE URL: {live_url_flv}\n")

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
            raise UserLiveException(TikTokError.COUNTRY_BLACKLISTED)

        if response.status_code == StatusCode.MOVED:  # MOBILE URL
            matches = re.findall("com/@(.*?)/live", content)
            if len(matches) < 1:
                raise LiveNotFound(TikTokError.INVALID_TIKTOK_LIVE_URL)

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

        if match is None:
            raise UserLiveException(TikTokError.ROOM_ID_ERROR)

        data = json.loads(match.group(1))

        if 'LiveRoom' not in data and 'CurrentRoom' in data:
            return ""

        room_id = data.get('LiveRoom', {}).get('liveRoomUserInfo', {}).get(
            'user', {}).get('roomId', None)

        if room_id is None:
            raise UserLiveException(TikTokError.ROOM_ID_ERROR)

        return room_id

    def get_user_from_room_id(self) -> str:
        """
        Given a room_id, I get the username
        """
        url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={self.room_id}"
        data = self.httpclient.get(url).json()

        unique_id = data.get('LiveRoomInfo', {}).get('ownerInfo', {}).get(
            'uniqueId', None)

        if unique_id is None:
            raise TikTokException(TikTokError.USERNAME_ERROR)

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
