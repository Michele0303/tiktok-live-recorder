import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.tiktok_recorder import TikTokRecorder  # noqa: E402
from utils.video_management import VideoManagement  # noqa: E402
from utils.custom_exceptions import TikTokRecorderError  # noqa: E402
from utils.enums import Mode  # noqa: E402
from utils.recorder_config import RecorderConfig  # noqa: E402


class FakeTikTokAPI:
    def __init__(self, blacklisted=True):
        self.blacklisted = blacklisted
        self.calls = []

    def is_country_blacklisted(self):
        self.calls.append("is_country_blacklisted")
        return self.blacklisted

    def get_room_id_from_user(self, user):
        self.calls.append(f"get_room_id_from_user:{user}")
        return "1234567890"

    def get_user_from_room_id(self, room_id):
        self.calls.append(f"get_user_from_room_id:{room_id}")
        return "creator"

    def get_sec_uid(self):
        self.calls.append("get_sec_uid")
        return "sec_uid"

    def is_room_alive(self, room_id):
        self.calls.append(f"is_room_alive:{room_id}")
        return True


class FakeRecordingTikTokAPI:
    def __init__(self, live_urls, alive_results):
        self.live_urls = live_urls
        self.alive_results = iter(alive_results)
        self.flv_downloads = []

    def get_live_url_candidates(self, room_id, user=None):
        return self.live_urls

    def is_room_alive(self, room_id):
        return next(self.alive_results)

    @staticmethod
    def is_hls_url(live_url):
        return ".m3u8" in live_url

    def get_stream_headers(self):
        return {"User-Agent": "test-agent", "Referer": "https://www.tiktok.com/"}

    def download_flv_stream(self, live_url):
        self.flv_downloads.append(live_url)
        yield b"F" * 4096


def test_setup_resolves_room_id_before_country_check_for_manual_user():
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.MANUAL, user="creator", cookies={})
    )
    fake_api = FakeTikTokAPI(blacklisted=True)
    recorder.tiktok = fake_api

    recorder._setup()

    assert recorder.room_id == "1234567890"
    assert fake_api.calls == [
        "get_room_id_from_user:creator",
        "is_country_blacklisted",
        "is_room_alive:1234567890",
    ]


def test_setup_keeps_followers_country_check_before_sec_uid():
    recorder = TikTokRecorder(RecorderConfig(mode=Mode.FOLLOWERS, cookies={}))
    fake_api = FakeTikTokAPI(blacklisted=True)
    recorder.tiktok = fake_api

    with pytest.raises(TikTokRecorderError, match="Captcha required"):
        recorder._setup()

    assert fake_api.calls == ["is_country_blacklisted"]


def test_setup_keeps_automatic_mode_blocked_after_room_resolution():
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.AUTOMATIC, user="creator", cookies={})
    )
    fake_api = FakeTikTokAPI(blacklisted=True)
    recorder.tiktok = fake_api

    with pytest.raises(TikTokRecorderError, match="Automatic mode is available"):
        recorder._setup()

    assert recorder.room_id == "1234567890"
    assert fake_api.calls == [
        "get_room_id_from_user:creator",
        "is_country_blacklisted",
    ]


def test_setup_keeps_manual_room_id_allowed_when_country_check_is_blocked():
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.MANUAL, room_id="1234567890", cookies={})
    )
    fake_api = FakeTikTokAPI(blacklisted=True)
    recorder.tiktok = fake_api

    recorder._setup()

    assert recorder.room_id == "1234567890"
    assert fake_api.calls == [
        "get_user_from_room_id:1234567890",
        "is_country_blacklisted",
        "is_room_alive:1234567890",
    ]


def test_start_recording_uses_flv_downloader(monkeypatch, tmp_path):
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.MANUAL, cookies={}, output=str(tmp_path))
    )
    fake_api = FakeRecordingTikTokAPI(
        ["https://cdn.example/live.flv"],
        [True, False],
    )
    recorder.tiktok = fake_api
    converted = []
    monkeypatch.setattr(
        VideoManagement,
        "convert_to_mp4",
        lambda file, bitrate, ffmpeg_path: converted.append(file),
    )
    monkeypatch.setattr(
        VideoManagement,
        "download_hls_stream",
        lambda *args, **kwargs: pytest.fail("HLS downloader was used for FLV"),
    )

    recorder.start_recording("creator", "123")

    assert fake_api.flv_downloads == ["https://cdn.example/live.flv"]
    assert len(converted) == 1
    assert converted[0].endswith("_flv.mp4")
    assert Path(converted[0]).stat().st_size == 4096


def test_start_recording_uses_ffmpeg_hls_downloader(monkeypatch, tmp_path):
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.MANUAL, cookies={}, output=str(tmp_path))
    )
    fake_api = FakeRecordingTikTokAPI(
        ["https://cdn.example/live/index.m3u8"],
        [True, False],
    )
    recorder.tiktok = fake_api
    hls_calls = []
    converted = []

    def fake_hls_download(live_url, **kwargs):
        hls_calls.append((live_url, kwargs))
        yield b"H" * 4096

    monkeypatch.setattr(VideoManagement, "download_hls_stream", fake_hls_download)
    monkeypatch.setattr(
        VideoManagement,
        "convert_to_mp4",
        lambda file, bitrate, ffmpeg_path: converted.append(file),
    )

    recorder.start_recording("creator", "123")

    assert fake_api.flv_downloads == []
    assert hls_calls == [
        (
            "https://cdn.example/live/index.m3u8",
            {
                "duration": None,
                "ffmpeg_path": None,
                "headers": {
                    "User-Agent": "test-agent",
                    "Referer": "https://www.tiktok.com/",
                },
            },
        )
    ]
    assert len(converted) == 1
    assert converted[0].endswith("_hls.ts")
    assert Path(converted[0]).stat().st_size == 4096


def test_start_recording_removes_failed_hls_before_flv_fallback(
    monkeypatch,
    tmp_path,
):
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.MANUAL, cookies={}, output=str(tmp_path))
    )
    fake_api = FakeRecordingTikTokAPI(
        [
            "https://cdn.example/live/index.m3u8",
            "https://cdn.example/live.flv",
        ],
        [True, True, False],
    )
    recorder.tiktok = fake_api
    converted = []
    monkeypatch.setattr(
        VideoManagement,
        "download_hls_stream",
        lambda *args, **kwargs: iter([b"short"]),
    )
    monkeypatch.setattr(
        VideoManagement,
        "convert_to_mp4",
        lambda file, bitrate, ffmpeg_path: converted.append(file),
    )

    recorder.start_recording("creator", "123")

    assert len(converted) == 1
    assert converted[0].endswith("_flv.mp4")
    assert not list(tmp_path.glob("*_hls.ts"))
