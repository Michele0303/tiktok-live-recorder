import json
import re
import requests  

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
        self.EULER_API = "https://tiktok.eulerstream.com"
        self.TIKREC_API = "https://tikrec.com"

        self.http_client = HttpClient(proxy, cookies).req
        self._http_client_stream = HttpClient(proxy, cookies).req_stream

    def _is_authenticated(self) -> bool:
        response = self.http_client.get(f"{self.BASE_URL}/foryou")
        response.raise_for_status()
        content = response.text
        return "login-title" not in content

    def is_country_blacklisted(self) -> bool:
        response = self.http_client.get(f"{self.BASE_URL}/live", allow_redirects=False)
        return response.status_code == StatusCode.REDIRECT

    def is_room_alive(self, room_id: str) -> bool:
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
        response = self.http_client.get(f"{self.BASE_URL}/foryou")
        sec_uid = re.search('"secUid":"(.*?)",', response.text)
        if sec_uid:
            sec_uid = sec_uid.group(1)
        return sec_uid

    def get_user_from_room_id(self, room_id) -> str:
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
        response = self.http_client.get(live_url, allow_redirects=False)
        content = response.text

        if response.status_code == StatusCode.REDIRECT:
            raise UserLiveError(TikTokError.COUNTRY_BLACKLISTED)

        if response.status_code == StatusCode.MOVED:  # MOBILE URL
            matches = re.findall("com/@(.*?)/live", content)
            if len(matches) < 1:
                raise LiveNotFound(TikTokError.INVALID_TIKTOK_LIVE_URL)
            user = matches[0]

        match = re.match(r"https?://(?:www\.)?tiktok\.com/@([^/]+)/live", live_url)
        if match:
            user = match.group(1)

        room_id = self.get_room_id_from_user(user)
        return user, room_id

    def _old_get_room_id_from_user(self, user: str) -> str:
        params = {"uniqueId": user, "giftInfo": "false"}
        response = self.http_client.get(
            f"{self.EULER_API}/webcast/room_info",
            params=params,
            headers={"x-api-key": ""},
        )
        if response.status_code != 200:
            raise UserLiveError(TikTokError.ROOM_ID_ERROR)

        data = response.json()
        room_id = data.get("data", {}).get("room_info", {}).get("id")
        if not room_id:
            raise UserLiveError(TikTokError.ROOM_ID_ERROR)
        return room_id

    def _tikrec_get_room_id_signed_url(self, user: str) -> str:
        response = self.http_client.get(
            f"{self.TIKREC_API}/tiktok/room/api/sign",
            params={"unique_id": user},
        )
        data = response.json()
        signed_path = data.get("signed_path")
        return f"{self.BASE_URL}{signed_path}"

    def get_room_id_from_user(self, user: str) -> str | None:
        signed_url = self._tikrec_get_room_id_signed_url(user)
        response = self.http_client.get(signed_url)
        content = response.text

        if not content or "Please wait" in content:
            raise UserLiveError(TikTokError.WAF_BLOCKED)

        data = response.json()
        return (data.get("data") or {}).get("user", {}).get("roomId")

    def get_followers_list(self, sec_uid) -> list:
        followers = []
        cursor = 0
        has_more = True

        ms_token = self.http_client.get(
            f"{self.BASE_URL}/api/user/list/?"
            "WebIdLastTime=1747672102&aid=1988&app_language=it-IT&app_name=tiktok_web&"
            "browser_language=it-IT&browser_name=Mozilla&browser_online=true&"
            "browser_platform=Linux%20x86_64&"
            "browser_version=5.0%20%28X11%3B%20Linux%20x86_64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F140.0.0.0%20Safari%2F537.36&"
            "channel=tiktok_web&cookie_enabled=true&count=5&data_collection_enabled=true&"
            "device_id=7506194516308166166&device_platform=web_pc&focus_state=true&"
            "from_page=user&history_len=3&is_fullscreen=false&is_page_visible=true&"
            "maxCursor=0&minCursor=0&odinId=7246312836442604570&os=linux&priority_region=IT&"
            "referer=&region=IT&root_referer=https%3A%2F%2Fwww.tiktok.com%2Flive&scene=21&"
            "screen_height=1080&screen_width=1920&tz_name=Europe%2FRome&user_is_login=true&"
            "verifyFp=verify_mh4yf0uq_rdjp1Xwt_OoTk_4Jrf_AS8H_sp31opbnJFre&webcast_language=it-IT&"
            "msToken=GphHoLvRR4QxA5AWVwDkrs3AbumoK5H8toE8LVHtj6cce3ToGdXhMfvDWzOXG-0GXUWoaGVHrwGNA4k_NnjuFFnHgv2S5eMjsvtkAhwMPa13xLmvP7tumx0KreFjPwTNnOj-BvAkPdO5Zrev3hoFBD9lHVo=&X-Bogus=&X-Gnarly="
        ).cookies.get("msToken", "")

        while has_more:
            url = (
                "https://www.tiktok.com/api/user/list/?"
                "WebIdLastTime=1747672102&aid=1988&app_language=it-IT&app_name=tiktok_web"
                "&browser_language=it-IT&browser_name=Mozilla&browser_online=true"
                "&browser_platform=Linux%20x86_64&browser_version=5.0%20%28X11%3B%20Linux%20x86_64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F140.0.0.0%20Safari%2F537.36&channel=tiktok_web&"
                "cookie_enabled=true&count=5&data_collection_enabled=true&device_id=7506194516308166166"
                "&device_platform=web_pc&focus_state=true&from_page=user&history_len=3&"
                f"is_fullscreen=false&is_page_visible=true&maxCursor={cursor}&minCursor={cursor}&"
                "odinId=7246312836442604570&os=linux&priority_region=IT&referer=&"
                "region=IT&scene=21&screen_height=1080&screen_width=1920"
                "&tz_name=Europe%2FRome&user_is_login=true&"
                f"secUid={sec_uid}&verifyFp=verify_mh4yf0uq_rdjp1Xwt_OoTk_4Jrf_AS8H_sp31opbnJFre&"
                f"webcast_language=it-IT&msToken={ms_token}&X-Bogus=&X-Gnarly="
            )

            response = self.http_client.get(url)
            if response.status_code != StatusCode.OK:
                raise TikTokRecorderError("Failed to retrieve followers list.")
            if not response.content:
                raise TikTokRecorderError("Empty response from TikTok followers API.")

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

    def _find_stream_recursively(self, obj):
        if isinstance(obj, dict):
            if "stream_data" in obj and isinstance(obj["stream_data"], str):
                try:
                    parsed = json.loads(obj["stream_data"])
                    flv = parsed.get("data", {}).get("origin", {}).get("main", {}).get("flv")
                    if flv: return flv
                except: pass
            
            if "flv_pull_url" in obj and isinstance(obj["flv_pull_url"], dict):
                pull = obj["flv_pull_url"]
                return pull.get("FULL_HD1") or pull.get("HD1") or pull.get("SD2") or pull.get("SD1")
                
            for v in obj.values():
                res = self._find_stream_recursively(v)
                if res: return res

        elif isinstance(obj, list):
            for item in obj:
                res = self._find_stream_recursively(item)
                if res: return res
        return None

    def _fallback_scrape(self, username: str):
        """If the API hides the stream, steal it straight from the HTML page."""
        url = f"{self.BASE_URL}/@{username}/live"
        try:
            # Put your sessionid and sessionid_ss here
            stealth_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
                "Cookie": "sessionid=; sessionid_ss=;",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.tiktok.com/"
            }
            
            # Bypass http_client and use our authenticated one
            response = requests.get(url, headers=stealth_headers)
            
            match = re.search(r'id="SIGI_STATE"\s*type="application/json">([^<]+)</script>', response.text)
            if match:
                sigi = json.loads(match.group(1))
                return self._find_stream_recursively(sigi)
        except Exception as e:
            logger.error(f"Fallback scrape failed: {e}")
        return None

    def get_live_url(self, room_id: str, username: str = None) -> str | None:
        """
        Return the cdn (flv or m3u8) of the streaming 
        """
        data = self.http_client.get(
            f"{self.WEBCAST_URL}/webcast/room/info/?aid=1988&room_id={room_id}"
        ).json()

        if "This account is private" in data:
            raise UserLiveError(TikTokError.ACCOUNT_PRIVATE)

        # Step 1: Let it loose on API repsponse
        flv_url = self._find_stream_recursively(data)
        if flv_url:
            logger.info("Target locked via Webcast API.")
            return flv_url

        # Step 2: If the API withheld the data, trigger the HTML fallback scrape
        if username:
            logger.warning(f"Webcast API missed. Initiating deep-scrape for @{username}...")
            fallback_url = self._fallback_scrape(username)
            if fallback_url:
                logger.info("Target locked via HTML Fallback.")
                return fallback_url
                
        # Step 3: If both of methods miss, show an error.
        logger.error("[!] All extraction methods failed. They might be completely offline.")
        return None

    def download_live_stream(self, live_url: str):
        """Generator that returns the live stream for a given room_id."""
        stream = self._http_client_stream.get(live_url, stream=True)
        for chunk in stream.iter_content(chunk_size=4096):
            if chunk:
                yield chunk
