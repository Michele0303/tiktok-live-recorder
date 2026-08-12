import sys
from pathlib import Path

import pytest
from requests import RequestException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.tiktok_recorder import TikTokRecorder  # noqa: E402
from utils.custom_exceptions import TikTokRecorderError, UserLiveError  # noqa: E402
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


class FakeShutdownEvent:
    def __init__(self, is_set=False):
        self._is_set = is_set

    def is_set(self):
        return self._is_set

    def wait(self, timeout):
        return self._is_set


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


def interrupt_sleep(*args, **kwargs):
    raise KeyboardInterrupt


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
    assert recorder._stop_requested is False


def test_start_recording_exits_automatic_mode_when_requested(monkeypatch, tmp_path):
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.AUTOMATIC, exit_on_interrupt=True, cookies={})
    )
    recorder.tiktok = RecordingTikTokAPI([[b"x" * 4096, KeyboardInterrupt()]])
    monkeypatch.setattr(
        recorder, "_build_output_path", lambda user: str(tmp_path / "recording_flv.mp4")
    )
    monkeypatch.setattr(
        "core.tiktok_recorder.VideoManagement.convert_flv_to_mp4", lambda *args: None
    )

    recorder.start_recording("creator", "123")

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


def test_automatic_mode_exits_when_parent_requests_shutdown():
    recorder = TikTokRecorder(
        RecorderConfig(
            mode=Mode.AUTOMATIC,
            user="creator",
            cookies={},
            shutdown_event=FakeShutdownEvent(is_set=True),
        )
    )
    recorder.tiktok = FakeTikTokAPI(blacklisted=False)

    recorder.automatic_mode()

    assert recorder.tiktok.calls == []


def test_automatic_mode_exits_when_interrupted_while_waiting(monkeypatch):
    recorder = TikTokRecorder(
        RecorderConfig(
            mode=Mode.AUTOMATIC,
            user="creator",
            exit_on_interrupt=True,
            cookies={},
        )
    )
    recorder.tiktok = FakeTikTokAPI(blacklisted=False)

    def user_is_not_live():
        raise UserLiveError("not live")

    monkeypatch.setattr(recorder, "manual_mode", user_is_not_live)
    monkeypatch.setattr(
        "core.tiktok_recorder.time.sleep",
        interrupt_sleep,
    )

    recorder.automatic_mode()

    assert recorder._stop_requested is True


def test_automatic_mode_rechecks_after_an_idle_interrupt(monkeypatch):
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.AUTOMATIC, user="creator", cookies={})
    )
    recorder.tiktok = FakeTikTokAPI(blacklisted=False)
    manual_mode_calls = 0
    sleep_calls = 0

    def manual_mode():
        nonlocal manual_mode_calls
        manual_mode_calls += 1
        if manual_mode_calls == 1:
            raise UserLiveError("not live")
        recorder._stop_requested = True

    def interrupt_once(*args, **kwargs):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            raise KeyboardInterrupt

    monkeypatch.setattr(recorder, "manual_mode", manual_mode)
    monkeypatch.setattr("core.tiktok_recorder.time.sleep", interrupt_once)

    recorder.automatic_mode()

    assert manual_mode_calls == 2


def test_start_recording_finalizes_when_followers_mode_requests_stop(
    monkeypatch, tmp_path
):
    recorder = TikTokRecorder(RecorderConfig(mode=Mode.FOLLOWERS, cookies={}))

    class StopAwareRecordingAPI(RecordingTikTokAPI):
        def download_live_stream(self, live_url):
            self.download_calls += 1
            yield b"x" * 4096
            recorder._stop_requested = True
            yield b"x"

    recorder.tiktok = StopAwareRecordingAPI([])
    output = tmp_path / "recording_flv.mp4"
    monkeypatch.setattr(recorder, "_build_output_path", lambda user: str(output))
    converted = []
    monkeypatch.setattr(
        "core.tiktok_recorder.VideoManagement.convert_flv_to_mp4",
        lambda *args: converted.append(args),
    )

    recorder.start_recording("creator", "123")

    assert converted == [(str(output), None, None)]


def test_start_recording_finalizes_when_interrupted_during_retry_sleep(
    monkeypatch, tmp_path
):
    recorder = TikTokRecorder(RecorderConfig(mode=Mode.AUTOMATIC, cookies={}))
    recorder.tiktok = RecordingTikTokAPI(
        [[b"x" * 4096, RequestException("temporary error")]]
    )
    output = tmp_path / "recording_flv.mp4"
    monkeypatch.setattr(recorder, "_build_output_path", lambda user: str(output))
    monkeypatch.setattr(
        "core.tiktok_recorder.time.sleep",
        interrupt_sleep,
    )

    converted = []
    monkeypatch.setattr(
        "core.tiktok_recorder.VideoManagement.convert_flv_to_mp4",
        lambda *args: converted.append(args),
    )

    recorder.start_recording("creator", "123")

    assert output.exists()
    assert converted == [(str(output), None, None)]
    assert recorder._stop_requested is False


def test_duration_is_not_reset_after_a_network_retry(monkeypatch, tmp_path):
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.AUTOMATIC, duration=5, cookies={})
    )
    api = RecordingTikTokAPI([RequestException("temporary error"), [b"x" * 4096]])
    recorder.tiktok = api
    output = tmp_path / "out_flv.mp4"
    monkeypatch.setattr(recorder, "_build_output_path", lambda user: str(output))
    monkeypatch.setattr("core.tiktok_recorder.time.sleep", lambda seconds: None)
    monotonic_times = iter([0, 0, 6])
    monkeypatch.setattr(
        "core.tiktok_recorder.time.monotonic", lambda: next(monotonic_times)
    )
    monkeypatch.setattr(
        "core.tiktok_recorder.VideoManagement.convert_flv_to_mp4", lambda *args: None
    )

    recorder.start_recording("creator", "123")

    assert api.download_calls == 1
    assert not output.exists()


def test_duration_expiry_during_a_chunk_discards_short_recordings(
    monkeypatch, tmp_path
):
    recorder = TikTokRecorder(
        RecorderConfig(mode=Mode.AUTOMATIC, duration=5, cookies={})
    )
    recorder.tiktok = RecordingTikTokAPI([[b"x"]])
    output = tmp_path / "out_flv.mp4"
    monkeypatch.setattr(recorder, "_build_output_path", lambda user: str(output))
    monotonic_times = iter([0, 0, 6])
    monkeypatch.setattr(
        "core.tiktok_recorder.time.monotonic", lambda: next(monotonic_times)
    )

    recorder.start_recording("creator", "123")

    assert not output.exists()


def test_manual_mode_delays_after_a_connection_error(monkeypatch, tmp_path):
    recorder = TikTokRecorder(RecorderConfig(mode=Mode.MANUAL, cookies={}))
    recorder.tiktok = RecordingTikTokAPI([ConnectionError("temporary error")])
    monkeypatch.setattr(
        recorder, "_build_output_path", lambda user: str(tmp_path / "out_flv.mp4")
    )
    sleep_calls = []

    def interrupt_after_retry(seconds):
        sleep_calls.append(seconds)
        raise KeyboardInterrupt

    monkeypatch.setattr("core.tiktok_recorder.time.sleep", interrupt_after_retry)

    recorder.start_recording("creator", "123")

    assert sleep_calls == [2]
