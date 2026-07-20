import logging
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.video_management import VideoManagement


def test_log_media_properties_reports_probe_data(monkeypatch, caplog):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=(
                '{"format": {"bit_rate": "5120000"}, "streams": [{'
                '"codec_type": "video", "codec_name": "h264", '
                '"width": 1920, "height": 1080}]}'
            ),
        ),
    )

    with caplog.at_level(logging.INFO, logger="logger"):
        VideoManagement.log_media_properties("recording.mp4")

    assert "codec=h264, resolution=1920x1080, bitrate=5120 kbps" in caplog.text


def test_log_media_properties_uses_sibling_ffprobe(monkeypatch, caplog):
    commands = []
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **kwargs: (
            commands.append((args, kwargs))
            or subprocess.CompletedProcess(
                args=args, returncode=0, stdout='{"streams": []}'
            )
        ),
    )

    with caplog.at_level(logging.WARNING, logger="logger"):
        VideoManagement.log_media_properties(
            "recording.mp4", "C:/tools/ffmpeg/bin/ffmpeg.exe"
        )

    assert commands == [
        (
            [
                str(Path("C:/tools/ffmpeg/bin/ffprobe.exe")),
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                "recording.mp4",
            ],
            {
                "capture_output": True,
                "check": True,
                "text": True,
                "timeout": VideoManagement.FFPROBE_TIMEOUT_SECONDS,
            },
        )
    ]
    assert "does not contain a video stream" in caplog.text


def test_log_media_properties_handles_an_invalid_bitrate(monkeypatch, caplog):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=(
                '{"format": {"bit_rate": "not-a-number"}, "streams": [{'
                '"codec_type": "video", "codec_name": "h264", '
                '"width": 1280, "height": 720}]}'
            ),
        ),
    )

    with caplog.at_level(logging.INFO, logger="logger"):
        VideoManagement.log_media_properties("recording.mp4")

    assert "bitrate=unknown" in caplog.text


def test_log_media_properties_handles_a_probe_timeout(monkeypatch, caplog):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(cmd="ffprobe", timeout=10)
        ),
    )

    with caplog.at_level(logging.WARNING, logger="logger"):
        VideoManagement.log_media_properties("recording.mp4")

    assert "Unable to inspect recorded media" in caplog.text


def test_log_media_properties_handles_invalid_probe_output(monkeypatch, caplog):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args, returncode=0, stdout="not-json"
        ),
    )

    with caplog.at_level(logging.WARNING, logger="logger"):
        VideoManagement.log_media_properties("recording.mp4")

    assert "Unable to inspect recorded media" in caplog.text
