import json
import re

from http_utils.http_client import HttpClient
from utils.enums import StatusCode, TikTokError
from utils.logger_manager import logger
from utils.custom_exceptions import UserLiveException, TikTokException, \
    LiveNotFound, IPBlockedByWAF


class TikTokAPI:

    def __init__(self, proxy, cookies):
        self.BASE_URL = 'https://www.tiktok.com'
        self.WEBCAST_URL = 'https://webcast.tiktok.com'

        self.http_client = HttpClient(proxy, cookies).req

    def is_country_blacklisted(self) -> bool:
        """
        Checks if the user is in a blacklisted country that requires login
        """
        response = self.http_client.get(
            f"{self.BASE_URL}/live",
            allow_redirects=False
        )

        return response.status_code == StatusCode.REDIRECT

    def is_room_alive(self, room_id: str) -> bool:
        """
        Checking whether the user is live.
        """
        if not room_id:
            raise UserLiveException(TikTokError.USER_NOT_CURRENTLY_LIVE)

        data = self.http_client.get(
            f"{self.WEBCAST_URL}/webcast/room/check_alive/"
            f"?aid=1988&region=CH&room_ids={room_id}&user_is_login=true"
        ).json()

        if 'data' not in data or len(data['data']) == 0:
            return False

        return data['data'][0].get('alive', False)

    def get_user_from_room_id(self, room_id) -> str:
        """
        Given a room_id, I get the username
        """
        data = self.http_client.get(
            f"{self.WEBCAST_URL}/webcast/room/info/?aid=1988&room_id={room_id}"
        ).json()

        if 'Follow the creator to watch their LIVE' in json.dumps(data):
            raise UserLiveException(TikTokError.ACCOUNT_PRIVATE_FOLLOW)

        if 'This account is private' in data:
            raise UserLiveException(TikTokError.ACCOUNT_PRIVATE)

        display_id = data.get("data", {}).get("owner", {}).get("display_id")
        if display_id is None:
            raise TikTokException(TikTokError.USERNAME_ERROR)

        return display_id

    def get_room_and_user_from_url(self, live_url: str):
        """
        Given a url, get user and room_id.
        """
        response = self.http_client.get(live_url, allow_redirects=False)
        content = response.text

        if response.status_code == StatusCode.REDIRECT:
            raise UserLiveException(TikTokError.COUNTRY_BLACKLISTED)

        if response.status_code == StatusCode.MOVED:  # MOBILE URL
            matches = re.findall("com/@(.*?)/live", content)
            if len(matches) < 1:
                raise LiveNotFound(TikTokError.INVALID_TIKTOK_LIVE_URL)

            user = matches[0]

        # https://www.tiktok.com/@<username>/live
        match = re.match(
            r"https?://(?:www\.)?tiktok\.com/@([^/]+)/live",
            live_url
        )
        if match:
            user = match.group(1)

        room_id = self.get_room_id_from_user(user)

        return user, room_id

    def get_room_id_from_user(self, user: str) -> str:
        """
        Given a username, I get the room_id
        """
        content = self.http_client.get(
            url=f'https://www.tiktok.com/@{user}/live'
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

    def get_live_url(self, room_id: str) -> str:
        """
        Return the cdn (flv or m3u8) of the streaming
        """
        data = self.http_client.get(
            f"{self.WEBCAST_URL}/webcast/room/info/?aid=1988&room_id={room_id}"
        ).json()

        if 'This account is private' in data:
            raise UserLiveException(TikTokError.ACCOUNT_PRIVATE)

        stream_url = data.get('data', {}).get('stream_url', {})

        sdk_data_str = stream_url.get('live_core_sdk_data', {}).get('pull_data', {}).get('stream_data')
        if not sdk_data_str:
            logger.warning("No SDK stream data found. Falling back to legacy URLs. Consider contacting the developer to update the code.")
            return stream_url.get('flv_pull_url', {}).get('HD1') or stream_url.get('rtmp_pull_url', '')

        # Extract stream options
        sdk_data = json.loads(sdk_data_str).get('data', {})
        qualities = stream_url['live_core_sdk_data']['pull_data']['options']['qualities']
        level_map = {q['sdk_key']: q['level'] for q in qualities}

        best_level = -1
        best_flv = None
        for sdk_key, entry in sdk_data.items():
            level = level_map.get(sdk_key, -1)
            stream_main = entry.get('main', {})
            if level > best_level:
                best_level = level
                best_flv = stream_main.get('flv')

        if not best_flv and data.get('status_code') == 4003110:
            raise UserLiveException(TikTokError.LIVE_RESTRICTION)

        return best_flv

    def download_live_stream(self, live_url: str):
        """
        Generator che restituisce lo streaming live per un dato room_id.
        """
        stream = self.http_client.get(live_url, stream=True)
        for chunk in stream.iter_content(chunk_size=4096):
            if not chunk:
                continue

            yield chunk
