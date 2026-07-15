import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.tiktok_api import TikTokAPI  # noqa: E402


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = responses
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return FakeResponse(self.responses.pop(0))


def build_api(*responses):
    api = TikTokAPI.__new__(TikTokAPI)
    api.WEBCAST_URL = "https://webcast.tiktok.com"
    api.http_client = FakeHttpClient(list(responses))
    return api


def test_is_room_alive_rejects_fake_check_alive_positive():
    api = build_api(
        {"data": [{"alive": True, "room_id": 123}], "status_code": 0},
        {"data": {"message": "Request params error"}, "status_code": 10011},
    )

    assert api.is_room_alive("123") is False


def test_is_room_alive_accepts_confirmed_stream_room():
    api = build_api(
        {"data": [{"alive": True, "room_id": 123}], "status_code": 0},
        {
            "data": {
                "stream_url": {
                    "live_core_sdk_data": {"pull_data": {"stream_data": '{"data": {}}'}}
                }
            },
            "status_code": 0,
        },
    )

    assert api.is_room_alive("123") is True


def test_is_room_alive_keeps_restricted_live_as_alive():
    api = build_api(
        {"data": [{"alive": True, "room_id": 123}], "status_code": 0},
        {"data": {}, "status_code": 4003110},
    )

    assert api.is_room_alive("123") is True


def test_is_room_alive_skips_room_info_when_check_alive_is_false():
    api = build_api({"data": [{"alive": False, "room_id": 123}], "status_code": 0})

    assert api.is_room_alive("123") is False
    assert len(api.http_client.urls) == 1
