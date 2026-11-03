import sys
from pathlib import Path

import ffmpeg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils import video_management  # noqa: E402
from utils.video_management import VideoManagement  # noqa: E402


class FakeStream:
    def __init__(self, recorder, error=None):
        self.recorder = recorder
        self.error = error

    def output(self, *args, **kwargs):
        return self

    def run(self, quiet=True, cmd="ffmpeg"):
        self.recorder["cmd"] = cmd
        if self.error:
            raise self.error


class FakeFFmpeg:
    Error = ffmpeg.Error

    def __init__(self, error=None):
        self.recorder = {}
        self.error = error

    def input(self, file):
        return FakeStream(self.recorder, self.error)


def test_convert_uses_custom_ffmpeg_path(monkeypatch, tmp_path):
    source = tmp_path / "TK_user_2024.01.01_00-00-00_flv.mp4"
    source.write_bytes(b"stream data")
    fake = FakeFFmpeg()
    monkeypatch.setattr(video_management, "ffmpeg", fake)

    VideoManagement.convert_flv_to_mp4(str(source), None, "/custom/bin/ffmpeg")

    assert fake.recorder["cmd"] == "/custom/bin/ffmpeg"
    assert not source.exists()


def test_convert_defaults_to_ffmpeg_from_path(monkeypatch, tmp_path):
    source = tmp_path / "TK_user_2024.01.01_00-00-00_flv.mp4"
    source.write_bytes(b"stream data")
    fake = FakeFFmpeg()
    monkeypatch.setattr(video_management, "ffmpeg", fake)

    VideoManagement.convert_flv_to_mp4(str(source))

    assert fake.recorder["cmd"] == "ffmpeg"


def test_convert_handles_ffmpeg_execution_failure(monkeypatch, tmp_path):
    source = tmp_path / "TK_user_2024.01.01_00-00-00_flv.mp4"
    source.write_bytes(b"stream data")
    fake = FakeFFmpeg(error=FileNotFoundError("ffmpeg not found"))
    monkeypatch.setattr(video_management, "ffmpeg", fake)

    VideoManagement.convert_flv_to_mp4(str(source), None, "/missing/ffmpeg")

    assert fake.recorder["cmd"] == "/missing/ffmpeg"
    assert source.exists()
