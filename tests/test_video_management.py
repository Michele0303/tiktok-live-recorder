import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ffmpeg  # noqa: E402

from utils.video_management import VideoManagement  # noqa: E402


def test_log_media_properties_reports_probe_data(monkeypatch, caplog):
    monkeypatch.setattr(
        ffmpeg,
        "probe",
        lambda file, cmd: {
            "format": {"bit_rate": "5120000"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                }
            ],
        },
    )

    with caplog.at_level(logging.INFO, logger="logger"):
        VideoManagement.log_media_properties("recording.mp4")

    assert "codec=h264, resolution=1920x1080, bitrate=5120 kbps" in caplog.text


def test_log_media_properties_uses_sibling_ffprobe(monkeypatch, caplog):
    commands = []
    monkeypatch.setattr(
        ffmpeg,
        "probe",
        lambda file, cmd: commands.append(cmd) or {"streams": []},
    )

    with caplog.at_level(logging.WARNING, logger="logger"):
        VideoManagement.log_media_properties(
            "recording.mp4", "C:/tools/ffmpeg/bin/ffmpeg.exe"
        )

    assert commands == [str(Path("C:/tools/ffmpeg/bin/ffprobe.exe"))]
    assert "does not contain a video stream" in caplog.text


def test_log_media_properties_handles_an_invalid_bitrate(monkeypatch, caplog):
    monkeypatch.setattr(
        ffmpeg,
        "probe",
        lambda file, cmd: {
            "format": {"bit_rate": "not-a-number"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1280,
                    "height": 720,
                }
            ],
        },
    )

    with caplog.at_level(logging.INFO, logger="logger"):
        VideoManagement.log_media_properties("recording.mp4")

    assert "bitrate=unknown" in caplog.text
