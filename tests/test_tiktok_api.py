import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.tiktok_api import TikTokAPI  # noqa: E402
from utils.custom_exceptions import (  # noqa: E402
    TikRecUnavailableError,
    UserLiveError,
)


class FakeResponse:
    def __init__(self, data, status_code=200, text=None):
        self._data = data
        self.status_code = status_code
        self.text = text if text is not None else "response"

    def json(self):
        if isinstance(self._data, Exception):
            raise self._data
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = responses
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        response = self.responses.pop(0)
        if isinstance(response, FakeResponse):
            return response
        return FakeResponse(response)


def build_api(*responses):
    api = TikTokAPI.__new__(TikTokAPI)
    api.WEBCAST_URL = "https://webcast.tiktok.com"
    api.http_client = FakeHttpClient(list(responses))
    return api


def build_room_id_api(*responses):
    api = build_api(*responses)
    api.BASE_URL = "https://www.tiktok.com"
    api.TIKREC_API = "https://tikrec.com"
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
                "status": 2,
                "stream_url": {
                    "live_core_sdk_data": {"pull_data": {"stream_data": '{"data": {}}'}}
                },
            },
            "status_code": 0,
        },
    )

    assert api.is_room_alive("123") is True


def test_is_room_alive_accepts_paused_stream_room():
    api = build_api(
        {"data": [{"alive": True, "room_id": 123}], "status_code": 0},
        {
            "data": {
                "status": 3,
                "stream_url": {
                    "live_core_sdk_data": {"pull_data": {"stream_data": '{"data": {}}'}}
                },
            },
            "status_code": 0,
        },
    )

    assert api.is_room_alive("123") is True


def test_is_room_alive_rejects_unknown_room_status():
    api = build_api(
        {"data": [{"alive": True, "room_id": 123}], "status_code": 0},
        {
            "data": {
                "status": 5,
                "stream_url": {"flv_pull_url": {"HD1": "https://cdn/live.flv"}},
            },
            "status_code": 0,
        },
    )

    assert api.is_room_alive("123") is False


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


def test_is_room_alive_rejects_null_check_alive_data():
    api = build_api({"data": None, "status_code": 0})

    assert api.is_room_alive("123") is False
    assert len(api.http_client.urls) == 1


def test_is_room_alive_rejects_null_room_info_data():
    api = build_api(
        {"data": [{"alive": True, "room_id": 123}], "status_code": 0},
        {"data": None, "status_code": 0},
    )

    assert api.is_room_alive("123") is False


def test_is_room_alive_rejects_ended_room_with_stale_stream_urls():
    api = build_api(
        {"data": [{"alive": True, "room_id": 123}], "status_code": 0},
        {
            "data": {
                "status": 4,
                "finish_time": 1784118433,
                "stream_url": {
                    "live_core_sdk_data": {
                        "pull_data": {"stream_data": '{"data": {}}'}
                    },
                    "flv_pull_url": {"HD1": "https://example.com/stale.flv"},
                },
            },
            "status_code": 0,
        },
    )

    assert api.is_room_alive("123") is False


def test_get_live_url_rejects_ended_room_with_stale_stream_urls():
    api = build_api(
        {
            "data": {
                "status": 4,
                "finish_time": 1784118433,
                "stream_url": {
                    "live_core_sdk_data": {
                        "pull_data": {"stream_data": '{"data": {}}'}
                    },
                    "flv_pull_url": {"HD1": "https://example.com/stale.flv"},
                },
            },
            "status_code": 0,
        },
    )

    with pytest.raises(UserLiveError, match="not hosting a live stream"):
        api.get_live_url("123", user="creator")


def test_get_live_url_accepts_paused_room():
    api = build_api(
        {
            "data": {
                "status": 3,
                "stream_url": {"flv_pull_url": {"HD1": "https://cdn/paused.flv"}},
            },
            "status_code": 0,
        },
    )

    assert api.get_live_url("123", user="creator") == "https://cdn/paused.flv"


def test_tikrec_retries_with_exponential_backoff(monkeypatch):
    api = build_room_id_api(
        FakeResponse({}, status_code=522),
        FakeResponse({}, status_code=503),
        FakeResponse({"signed_path": "/signed-room"}),
    )
    delays = []
    monkeypatch.setattr("core.tiktok_api.time.sleep", delays.append)

    signed_url = api._tikrec_get_room_id_signed_url("creator")

    assert signed_url == "https://www.tiktok.com/signed-room"
    assert delays == [1, 2]
    assert api.http_client.urls == [
        "https://tikrec.com/tiktok/room/api/sign",
        "https://tikrec.com/tiktok/room/api/sign",
        "https://tikrec.com/tiktok/room/api/sign",
    ]


def test_tikrec_failure_suggests_manual_room_id(monkeypatch):
    api = build_room_id_api(
        FakeResponse({}, status_code=522),
        FakeResponse({}, status_code=522),
        FakeResponse({}, status_code=522),
    )
    monkeypatch.setattr("core.tiktok_api.time.sleep", lambda _: None)

    with pytest.raises(TikRecUnavailableError, match=r"-room_id <ROOM_ID>"):
        api.get_room_id_from_user("creator")

    assert all("eulerstream" not in url for url in api.http_client.urls)


def test_get_live_url_candidates_returns_ordered_unique_streams():
    api = build_api(
        {
            "data": {
                "status": 2,
                "stream_url": {
                    "live_core_sdk_data": {
                        "pull_data": {
                            "stream_data": (
                                '{"data": {'
                                '"hd": {"main": {"flv": "https://cdn/hd.flv"}},'
                                '"ld": {"main": {"flv": "https://cdn/ld.flv"}},'
                                '"ao": {"main": {"flv": "https://cdn/audio.flv"}}'
                                "}}"
                            ),
                            "options": {
                                "qualities": [
                                    {"sdk_key": "hd", "level": 3},
                                    {"sdk_key": "ld", "level": 1},
                                ]
                            },
                        }
                    },
                    "flv_pull_url": {
                        "HD1": "https://cdn/hd.flv",
                        "SD1": "https://cdn/sd.flv",
                    },
                },
            },
            "status_code": 0,
        },
    )

    assert api.get_live_url_candidates("123", user="creator") == [
        "https://cdn/hd.flv",
        "https://cdn/ld.flv",
        "https://cdn/audio.flv",
        "https://cdn/sd.flv",
    ]
