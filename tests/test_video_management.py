import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.video_management import VideoManagement  # noqa: E402


class FakeProcess:
    def __init__(self, content):
        self.stdout = io.BytesIO(content)
        self.return_code = None
        self.terminated = False

    def wait(self, timeout=None):
        if self.return_code is None:
            self.return_code = 0
        return self.return_code

    def poll(self):
        return self.return_code

    def terminate(self):
        self.terminated = True
        self.return_code = -15

    def kill(self):
        self.return_code = -9


class FakeFFmpegGraph:
    def __init__(self, process, calls):
        self.process = process
        self.calls = calls

    def output(self, target, **kwargs):
        self.calls["output"] = (target, kwargs)
        return self

    def global_args(self, *args):
        self.calls["global_args"] = args
        return self

    def run_async(self, **kwargs):
        self.calls["run_async"] = kwargs
        return self.process


def install_fake_ffmpeg(monkeypatch, content):
    calls = {}
    process = FakeProcess(content)
    graph = FakeFFmpegGraph(process, calls)

    def fake_input(live_url, **kwargs):
        calls["input"] = (live_url, kwargs)
        return graph

    monkeypatch.setattr("utils.video_management.ffmpeg.input", fake_input)
    return process, calls


def test_download_hls_stream_uses_ffmpeg_mpegts_pipe(monkeypatch):
    process, calls = install_fake_ffmpeg(monkeypatch, b"A" * 8192)

    chunks = list(
        VideoManagement.download_hls_stream(
            "https://cdn.example/live/index.m3u8",
            duration=30,
            ffmpeg_path="custom-ffmpeg",
            headers={
                "User-Agent": "test-agent",
                "Referer": "https://www.tiktok.com/",
            },
        )
    )

    assert chunks == [b"A" * 4096, b"A" * 4096]
    assert calls["input"] == (
        "https://cdn.example/live/index.m3u8",
        {
            "rw_timeout": 15_000_000,
            "user_agent": "test-agent",
            "headers": "Referer: https://www.tiktok.com/\r\n",
        },
    )
    assert calls["output"] == (
        "pipe:1",
        {"c": "copy", "f": "mpegts", "t": 30},
    )
    assert calls["run_async"] == {
        "cmd": "custom-ffmpeg",
        "pipe_stdout": True,
    }
    assert process.return_code == 0


def test_download_hls_stream_stops_ffmpeg_when_consumer_closes(monkeypatch):
    process, _ = install_fake_ffmpeg(monkeypatch, b"A" * 8192)
    stream = VideoManagement.download_hls_stream("https://cdn.example/live/index.m3u8")

    assert next(stream) == b"A" * 4096
    stream.close()

    assert process.terminated is True


def test_convert_hls_temp_file_to_mp4(monkeypatch, tmp_path):
    source = tmp_path / "TK_creator_2026.08.12_12-00-00_hls.ts"
    source.write_bytes(b"mpeg-ts")
    calls = {}

    class FakeConversionGraph:
        def output(self, output_file, **kwargs):
            calls["output"] = (output_file, kwargs)
            Path(output_file).write_bytes(b"mp4")
            return self

        def run(self, **kwargs):
            calls["run"] = kwargs

    monkeypatch.setattr(
        "utils.video_management.ffmpeg.input",
        lambda file: FakeConversionGraph(),
    )

    VideoManagement.convert_to_mp4(str(source), ffmpeg_path="custom-ffmpeg")

    output = tmp_path / "TK_creator_2026.08.12_12-00-00.mp4"
    assert calls["output"] == (str(output), {"c": "copy", "y": "-y"})
    assert calls["run"] == {
        "quiet": True,
        "cmd": "custom-ffmpeg",
    }
    assert output.read_bytes() == b"mp4"
    assert not source.exists()
