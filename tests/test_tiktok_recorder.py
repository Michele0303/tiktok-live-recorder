import sys
from pathlib import Path

import pytest
from requests import RequestException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.tiktok_recorder import TikTokRecorder  # noqa: E402
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


class RecordingTikTokAPI:
    def __init__(self, download_attempts):
        self.download_attempts = iter(download_attempts)
        self.download_calls = 0

    def get_live_url_candidates(self, room_id, user=None):
        return ["https://example.test/live.flv"]

    def is_room_alive(self, room_id):
        return True

    def download_live_stream(self, live_url):
        self.download_calls += 1
        attempt = next(self.download_attempts)
        if isinstance(attempt, BaseException):
            raise attempt
        for item in attempt:
            if isinstance(item, BaseException):
                raise item
            yield item


def test_start_recording_finalizes_after_keyboard_interrupt(monkeypatch, tmp_path):
    recorder = TikTokRecorder(RecorderConfig(mode=Mode.AUTOMATIC, cookies={}))
    recorder.tiktok = RecordingTikTokAPI([[b"x" * 4096, KeyboardInterrupt()]])
    output = tmp_path / "recording_flv.mp4"
    monkeypatch.setattr(recorder, "_build_output_path", lambda user: str(output))

    converted = []
    monkeypatch.setattr(
        "core.tiktok_recorder.VideoManagement.convert_flv_to_mp4",
        lambda *args: converted.append(args),
    )

    recorder.start_recording("creator", "123")

    assert output.exists()
    assert converted == [(str(output), None, None)]
    assert recorder._stop_requested is True


def test_automatic_mode_exits_after_a_user_stop_request(monkeypatch):
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.AUTOMATIC, user="creator", cookies={})
    )
    recorder.tiktok = FakeTikTokAPI(blacklisted=False)
    monkeypatch.setattr(
        recorder, "manual_mode", lambda: setattr(recorder, "_stop_requested", True)
    )

    recorder.automatic_mode()

    assert recorder.tiktok.calls == ["get_room_id_from_user:creator"]


def test_duration_is_not_reset_after_a_network_retry(monkeypatch, tmp_path):
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.AUTOMATIC, duration=5, cookies={})
    )
    api = RecordingTikTokAPI([RequestException("temporary error"), [b"x" * 4096]])
    recorder.tiktok = api
    output = tmp_path / "out_flv.mp4"
    monkeypatch.setattr(recorder, "_build_output_path", lambda user: str(output))
    monkeypatch.setattr("core.tiktok_recorder.time.sleep", lambda seconds: None)
    monotonic_times = iter([0, 6])
    monkeypatch.setattr(
        "core.tiktok_recorder.time.monotonic", lambda: next(monotonic_times)
    )
    monkeypatch.setattr(
        "core.tiktok_recorder.VideoManagement.convert_flv_to_mp4", lambda *args: None
    )

    recorder.start_recording("creator", "123")

    assert api.download_calls == 2
