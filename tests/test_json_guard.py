import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.tiktok_api import TikTokAPI  # noqa: E402
from utils.custom_exceptions import TikTokRecorderError  # noqa: E402
from utils.utils import parse_json  # noqa: E402


class HtmlResponse:
    """What TikTok sends when a request is blocked or rate-limited."""

    text = "<html><body>Please wait...</body></html>"
    status_code = 200

    def json(self):
        raise json.JSONDecodeError("Expecting value", self.text, 0)

    def raise_for_status(self):
        return None


class EmptyResponse:
    text = ""

    def json(self):
        raise json.JSONDecodeError("Expecting value", "", 0)


class ListResponse:
    def json(self):
        return [1, 2, 3]


class JsonResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeHttpClient:
    def __init__(self, response):
        self.response = response
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        # a plain dict stands for "TikTok answered with this JSON payload"
        if hasattr(self.response, "json"):
            return self.response
        return JsonResponse(self.response)


def build_api(response):
    api = TikTokAPI.__new__(TikTokAPI)
    api.BASE_URL = "https://www.tiktok.com"
    api.WEBCAST_URL = "https://webcast.tiktok.com"
    api.TIKREC_API = "https://tikrec.com"
    api.EULER_API = "https://tiktok.eulerstream.com"
    api.http_client = FakeHttpClient(response)
    return api


def test_parse_json_raises_readable_error_on_html():
    with pytest.raises(TikTokRecorderError) as ctx:
        parse_json(HtmlResponse(), "room info")

    message = str(ctx.value)
    assert "room info" in message
    assert "non-JSON response" in message
    assert "Please wait" in message


def test_parse_json_raises_on_empty_body():
    with pytest.raises(TikTokRecorderError) as ctx:
        parse_json(EmptyResponse(), "check_alive")

    assert "empty body" in str(ctx.value)


def test_parse_json_rejects_non_object_payload():
    with pytest.raises(TikTokRecorderError) as ctx:
        parse_json(ListResponse(), "room info")

    assert "unexpected JSON payload" in str(ctx.value)


def test_is_room_alive_does_not_crash_on_blocked_response():
    api = build_api(HtmlResponse())

    with pytest.raises(TikTokRecorderError):
        api.is_room_alive("1234567890")


def test_dict_shaped_stream_data_falls_back_to_legacy_urls():
    # stream_data is normally a JSON *string*; TikTok sometimes ships it as an
    # object, which made json.loads() raise TypeError.
    api = build_api(
        {
            "data": {
                "status": 2,
                "stream_url": {
                    "live_core_sdk_data": {
                        "pull_data": {"stream_data": {"data": {"hd": {}}}}
                    },
                    "flv_pull_url": {"HD1": "https://cdn/legacy_hd.flv"},
                },
            },
            "status_code": 0,
        }
    )

    assert api.get_live_urls("123") == ["https://cdn/legacy_hd.flv"]


def test_malformed_stream_data_keeps_legacy_urls_without_qualities():
    # truncated payload *and* no qualities block: the early return used to hand
    # back an empty candidate list, losing the flv_pull_url fallback.
    api = build_api(
        {
            "data": {
                "status": 2,
                "stream_url": {
                    "live_core_sdk_data": {"pull_data": {"stream_data": '{"data": '}},
                    "flv_pull_url": {"HD1": "https://cdn/legacy_hd.flv"},
                },
            },
            "status_code": 0,
        }
    )

    assert api.get_live_urls("123") == ["https://cdn/legacy_hd.flv"]


def test_get_room_id_from_user_does_not_crash_on_blocked_response():
    api = build_api(HtmlResponse())

    with pytest.raises(TikTokRecorderError):
        api.get_room_id_from_user("someone")
