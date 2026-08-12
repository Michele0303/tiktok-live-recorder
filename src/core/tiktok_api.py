import html
import json
import re

from http_utils.http_client import HttpClient
from utils.enums import StatusCode, TikTokError
from utils.logger_manager import logger
from utils.custom_exceptions import (
    UserLiveError,
    TikTokRecorderError,
    LiveNotFound,
    TikRecUnavailableError,
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

        alive_data = self.http_client.get(
            f"{self.WEBCAST_URL}/webcast/room/check_alive/"
            f"?aid=1988&region=CH&room_ids={room_id}&user_is_login=true"
        ).json()

        data_list = alive_data.get("data")
        if (
            not isinstance(data_list, list)
            or not data_list
            or not isinstance(data_list[0], dict)
            or not data_list[0].get("alive", False)
        ):
            return False

        room_info = self.http_client.get(
            f"{self.WEBCAST_URL}/webcast/room/info/?aid=1988&room_id={room_id}"
        ).json()

        status_code = room_info.get("status_code", 0)
        if status_code == 4003110:
            return True

        if status_code != 0:
            return False

        room_data = room_info.get("data") or {}
        room_status = room_data.get("status")
        if room_status is not None and str(room_status) != "2":
            return False

        stream_url = room_data.get("stream_url") or {}
        sdk_stream_data = (
            (stream_url.get("live_core_sdk_data") or {})
            .get("pull_data", {})
            .get("stream_data")
        )

        return bool(
            sdk_stream_data
            or stream_url.get("flv_pull_url")
            or stream_url.get("hls_pull_url")
            or stream_url.get("hls_pull_url_map")
            or stream_url.get("rtmp_pull_url")
        )

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

    def _old_get_room_id_from_user(self, user: str) -> str:
        params = {"uniqueId": user, "giftInfo": "false"}

        response = self.http_client.get(
            f"{self.EULER_API}/webcast/room_info",
            params=params,
            headers={"x-api-key": ""},
        )

        if response.status_code != 200:
            raise UserLiveError(TikTokError.ROOM_ID_ERROR)

        try:
            data = response.json()
        except ValueError as error:
            raise UserLiveError(TikTokError.ROOM_ID_ERROR) from error

        room_id = data.get("data", {}).get("room_info", {}).get("id")
        if not room_id:
            raise UserLiveError(TikTokError.ROOM_ID_ERROR)

        return room_id

    def _tikrec_get_room_id_signed_url(self, user: str) -> str:
        try:
            response = self.http_client.get(
                f"{self.TIKREC_API}/tiktok/room/api/sign",
                params={"unique_id": user},
            )
            response.raise_for_status()
        except Exception as e:
            raise TikRecUnavailableError(
                f"tikrec signing service is unreachable: {e}"
            ) from e

        try:
            data = response.json()
        except ValueError as e:
            raise TikRecUnavailableError(
                "tikrec signing service returned an invalid response "
                "(expected JSON, got something else — the service may be down)."
            ) from e

        signed_path = data.get("signed_path")
        if not signed_path:
            raise TikRecUnavailableError(
                "tikrec signing service did not return a signed_path "
                "(the service may be down or overloaded)."
            )

        return f"{self.BASE_URL}{signed_path}"

    def get_room_id_from_user(self, user: str) -> str | None:
        """Given a username, get the room_id."""
        try:
            signed_url = self._tikrec_get_room_id_signed_url(user)
        except TikRecUnavailableError as e:
            logger.warning(
                f"[!] tikrec is unavailable ({e}). "
                "Falling back to unsigned API — recording continues but may be less reliable."
            )
            return self._old_get_room_id_from_user(user)

        try:
            response = self.http_client.get(signed_url)
        except Exception as error:
            return self._fallback_room_id(user, f"signed room lookup failed: {error}")

        if response.status_code != StatusCode.OK:
            return self._fallback_room_id(
                user, f"signed room lookup returned HTTP {response.status_code}"
            )

        content = response.text

        if not content or "Please wait" in content:
            raise UserLiveError(TikTokError.WAF_BLOCKED)

        try:
            data = response.json()
        except ValueError:
            return self._fallback_room_id(
                user, "signed room lookup returned invalid JSON"
            )

        room_id = (data.get("data") or {}).get("user", {}).get("roomId")
        if not room_id:
            return self._fallback_room_id(
                user, "signed room lookup did not include a RoomID"
            )

        return room_id

    def _fallback_room_id(self, user: str, reason: str) -> str:
        logger.warning(
            "[!] tikrec signed room lookup failed (%s). "
            "Falling back to unsigned API - recording continues but may be less reliable.",
            reason,
        )
        return self._old_get_room_id_from_user(user)

    def get_followers_list(self, sec_uid) -> list:
        """
        Returns all followers for the authenticated user by paginating
        """
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
        ).cookies["msToken"]

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

    def _get_stream_url_from_page(self, user: str) -> str | None:
        """
        Fallback: fetch the live page HTML and extract the stream URL directly.
        Used when the webcast API returns status code 4003110 (WAF/access restriction).
        """
        try:
            live_page_url = f"{self.BASE_URL}/@{user}/live"
            response = self.http_client.get(live_page_url)
            content = response.text

            flv_matches = re.findall(r'https?://[^\s"\'<>]+\.flv[^\s"\'<>]*', content)
            if flv_matches:
                # Prefer original (_or4) or SD quality
                for url in flv_matches:
                    url = html.unescape(url.rstrip("\\"))
                    if "_or4" in url or "_sd" in url:
                        logger.info(f"Found stream URL from page: {url[:80]}...")
                        return url
                return html.unescape(flv_matches[0].rstrip("\\"))

            hls_matches = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', content)
            if hls_matches:
                return html.unescape(hls_matches[0].rstrip("\\"))

            return None
        except Exception as e:
            logger.warning(f"Failed to extract stream URL from page: {e}")
            return None

    def _add_live_url_candidate(self, candidates: list[str], url: str | None) -> None:
        if url and url not in candidates:
            candidates.append(url)

    def get_live_urls(self, room_id: str, user: str = None) -> list[str]:
        """
        Return candidate CDN URLs (flv or m3u8) for the streaming.
        If the API returns status code 4003110 and a username is provided,
        falls back to scraping the live page directly.
        """
        data = self.http_client.get(
            f"{self.WEBCAST_URL}/webcast/room/info/?aid=1988&room_id={room_id}"
        ).json()

        if "This account is private" in data:
            raise UserLiveError(TikTokError.ACCOUNT_PRIVATE)

        status_code = data.get("status_code", 0)

        if status_code == 4003110:
            if user:
                logger.info(
                    "API blocked by WAF (4003110). Trying fallback: extract stream URL from live page..."
                )
                fallback_url = self._get_stream_url_from_page(user)
                if fallback_url:
                    return [fallback_url]

            raise UserLiveError(TikTokError.LIVE_RESTRICTION)

        room_data = data.get("data") or {}
        room_status = room_data.get("status")
        if room_status is not None and str(room_status) != "2":
            raise UserLiveError(TikTokError.USER_NOT_CURRENTLY_LIVE)

        stream_url = room_data.get("stream_url", {})

        sdk_data_str = (
            stream_url.get("live_core_sdk_data", {})
            .get("pull_data", {})
            .get("stream_data")
        )
        candidates = []
        if not sdk_data_str:
            logger.warning(
                "No SDK stream data found. Falling back to legacy URLs. Consider contacting the developer to update the code."
            )
            flv_pull_url = stream_url.get("flv_pull_url", {})
            for key in ("FULL_HD1", "HD1", "SD2", "SD1"):
                self._add_live_url_candidate(candidates, flv_pull_url.get(key))
            self._add_live_url_candidate(candidates, stream_url.get("hls_pull_url"))
            self._add_live_url_candidate(candidates, stream_url.get("rtmp_pull_url"))
            return candidates

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
            return candidates
        level_map = {q["sdk_key"]: q["level"] for q in qualities}

        ordered_sdk_keys = sorted(
            sdk_data.keys(), key=lambda key: level_map.get(key, -1), reverse=True
        )
        for sdk_key in ordered_sdk_keys:
            entry = sdk_data[sdk_key]
            stream_main = entry.get("main", {})
            self._add_live_url_candidate(candidates, stream_main.get("flv"))
            self._add_live_url_candidate(
                candidates, stream_main.get("hls") or stream_main.get("m3u8")
            )

        flv_pull_url = stream_url.get("flv_pull_url", {})
        for key in ("FULL_HD1", "HD1", "SD2", "SD1"):
            self._add_live_url_candidate(candidates, flv_pull_url.get(key))
        self._add_live_url_candidate(candidates, stream_url.get("hls_pull_url"))
        self._add_live_url_candidate(candidates, stream_url.get("rtmp_pull_url"))

        return candidates

    def get_live_url(self, room_id: str, user: str = None) -> str | None:
        """Return the first candidate CDN URL for the streaming."""
        live_urls = self.get_live_urls(room_id, user=user)
        if live_urls:
            return live_urls[0]
        return None

    def get_live_url_candidates(self, room_id: str, user: str = None) -> list[str]:
        """Return candidate CDN URLs for the streaming."""
        return self.get_live_urls(room_id, user=user)

    def download_live_stream(self, live_url: str):
        """Generator that returns the live stream for a given room_id."""
        stream = self._http_client_stream.get(live_url, stream=True)
        for chunk in stream.iter_content(chunk_size=4096):
            if chunk:
                yield chunk
