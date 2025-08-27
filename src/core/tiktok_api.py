import json
import re

from http_utils.http_client import HttpClient
from utils.enums import StatusCode, TikTokError
from utils.logger_manager import logger
from utils.custom_exceptions import (
    UserLiveError,
    TikTokRecorderError,
    LiveNotFound,
)


class TikTokAPI:
    def __init__(self, proxy, cookies):
        self.BASE_URL = "https://www.tiktok.com"
        self.WEBCAST_URL = "https://webcast.tiktok.com"
        self.API_URL = "https://www.tiktok.com/api-live/user/room/"

        self.http_client = HttpClient(proxy, cookies).req
        self._http_client_stream = HttpClient(proxy, cookies).req_stream

    def _is_authenticated(self) -> bool:
        response = self.http_client.get(f"{self.BASE_URL}/foryou")
        response.raise_for_status()

        content = response.text
        return "login-title" not in content

    def is_country_blacklisted(self) -> bool:
        """
        Checks if the user is in a blacklisted country that requires login
        """
        response = self.http_client.get(f"{self.BASE_URL}/live", allow_redirects=False)

        return response.status_code == StatusCode.REDIRECT

    def is_room_alive(self, room_id: str) -> bool:
        """
        Checking whether the user is live.
        """
        if not room_id:
            raise UserLiveError(TikTokError.USER_NOT_CURRENTLY_LIVE)

        data = self.http_client.get(
            f"{self.WEBCAST_URL}/webcast/room/check_alive/"
            f"?aid=1988&region=CH&room_ids={room_id}&user_is_login=true"
        ).json()

        if "data" not in data or len(data["data"]) == 0:
            return False

        return data["data"][0].get("alive", False)

    def get_sec_uid(self):
        """
        Returns the sec_uid of the authenticated user.
        """
        response = self.http_client.get(f"{self.BASE_URL}/foryou")

        sec_uid = re.search('"secUid":"(.*?)",', response.text)
        if sec_uid:
            sec_uid = sec_uid.group(1)

        return sec_uid

    def get_user_from_room_id(self, room_id) -> str:
        """
        Given a room_id, I get the username
        """
        data = self.http_client.get(
            f"{self.WEBCAST_URL}/webcast/room/info/?aid=1988&room_id={room_id}"
        ).json()

        if "Follow the creator to watch their LIVE" in json.dumps(data):
            raise UserLiveError(TikTokError.ACCOUNT_PRIVATE_FOLLOW)

        if "This account is private" in data:
            raise UserLiveError(TikTokError.ACCOUNT_PRIVATE)

        display_id = data.get("data", {}).get("owner", {}).get("display_id")
        if display_id is None:
            raise TikTokRecorderError(TikTokError.USERNAME_ERROR)

        return display_id

    def get_room_and_user_from_url(self, live_url: str):
        """
        Given a url, get user and room_id.
        """
        response = self.http_client.get(live_url, allow_redirects=False)
        content = response.text

        if response.status_code == StatusCode.REDIRECT:
            raise UserLiveError(TikTokError.COUNTRY_BLACKLISTED)

        if response.status_code == StatusCode.MOVED:  # MOBILE URL
            matches = re.findall("com/@(.*?)/live", content)
            if len(matches) < 1:
                raise LiveNotFound(TikTokError.INVALID_TIKTOK_LIVE_URL)

            user = matches[0]

        # https://www.tiktok.com/@<username>/live
        match = re.match(r"https?://(?:www\.)?tiktok\.com/@([^/]+)/live", live_url)
        if match:
            user = match.group(1)

        room_id = self.get_room_id_from_user(user)

        return user, room_id

    def get_room_id_from_user(self, user: str) -> str:
        """
        Given a username, I get the room_id
        """
        response = self.http_client.get(
            self.API_URL, params={"uniqueId": user, "sourceType": 54, "aid": 1988}
        )

        if response.status_code != 200:
            raise UserLiveError(TikTokError.ROOM_ID_ERROR)

        data = response.json()

        if (
            data.get("data")
            and data["data"].get("user")
            and data["data"]["user"].get("roomId")
        ):
            room_id = data["data"]["user"]["roomId"]
            return room_id
        else:
            raise UserLiveError(TikTokError.ROOM_ID_ERROR)

    def get_followers_list(self, sec_uid) -> list:
        """
        Returns all followers for the authenticated user by paginating
        """
        followers = []
        cursor = 0
        has_more = True

        while has_more:
            url = (
                f"{self.BASE_URL}/api/user/list/"
                "?WebIdLastTime=1747672102"
                "&aid=1988&app_language=it-IT&app_name=tiktok_web"
                "&browser_language=it-IT&browser_name=Mozilla&browser_online=true"
                "&browser_platform=Linux%20x86_64"
                "&browser_version=5.0%20%28X11%3B%20Linux%20x86_64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F136.0.0.0%20Safari%2F537.36"
                "&channel=tiktok_web&cookie_enabled=true&count=30&data_collection_enabled=true"
                "&device_id=7506194516308166166&device_platform=web_pc&focus_state=true"
                "&from_page=user&history_len=2&is_fullscreen=false&is_page_visible=true"
                f"&maxCursor={cursor}&minCursor={cursor}"
                "&odinId=7246312836442604570&os=linux&priority_region=IT"
                "&referer=&region=IT&scene=21&screen_height=1080&screen_width=1920"
                f"&secUid={sec_uid}&tz_name=Europe%2FRome&user_is_login=true"
                "&webcast_language=it-IT&msToken=&X-Bogus=&X-Gnarly="
            )

            response = self.http_client.get(url)

            if response.status_code != StatusCode.OK:
                raise TikTokRecorderError("Failed to retrieve followers list.")

            data = response.json()
            user_list = data.get("userList", [])

            for user in user_list:
                username = user.get("user", {}).get("uniqueId")
                if username:
                    followers.append(username)

            has_more = data.get("hasMore", False)
            new_cursor = data.get("minCursor", 0)

            if new_cursor == cursor:
                break

            cursor = new_cursor

        if not followers:
            raise TikTokRecorderError("Followers list is empty.")

        return followers

    def get_live_url(self, room_id: str) -> str:
        """
        Return the cdn (flv or m3u8) of the streaming
        """
        data = self.http_client.get(
            f"{self.WEBCAST_URL}/webcast/room/info/?aid=1988&room_id={room_id}"
        ).json()

        if "This account is private" in data:
            raise UserLiveError(TikTokError.ACCOUNT_PRIVATE)

        stream_url = data.get("data", {}).get("stream_url", {})

        sdk_data_str = (
            stream_url.get("live_core_sdk_data", {})
            .get("pull_data", {})
            .get("stream_data")
        )
        if not sdk_data_str:
            logger.warning(
                "No SDK stream data found. Falling back to legacy URLs. Consider contacting the developer to update the code."
            )
            return (
                stream_url.get("flv_pull_url", {}).get("FULL_HD1")
                or stream_url.get("flv_pull_url", {}).get("HD1")
                or stream_url.get("flv_pull_url", {}).get("SD2")
                or stream_url.get("flv_pull_url", {}).get("SD1")
                or stream_url.get("rtmp_pull_url", "")
            )

        # Extract stream options
        sdk_data = json.loads(sdk_data_str).get("data", {})
        qualities = (
            stream_url.get("live_core_sdk_data", {})
            .get("pull_data", {})
            .get("options", {})
            .get("qualities", [])
        )
        if not qualities:
            logger.warning("No qualities found in the stream data. Returning None.")
            return None
        level_map = {q["sdk_key"]: q["level"] for q in qualities}

        best_level = -1
        best_flv = None
        for sdk_key, entry in sdk_data.items():
            level = level_map.get(sdk_key, -1)
            stream_main = entry.get("main", {})
            if level > best_level:
                best_level = level
                best_flv = stream_main.get("flv")

        if not best_flv and data.get("status_code") == 4003110:
            raise UserLiveError(TikTokError.LIVE_RESTRICTION)

        return best_flv

    def download_live_stream(self, live_url: str):
        """
        Generator che restituisce lo streaming live per un dato room_id.
        """
        stream = self._http_client_stream.get(live_url, stream=True)
        for chunk in stream.iter_content(chunk_size=4096):
            if chunk:
                yield chunk
