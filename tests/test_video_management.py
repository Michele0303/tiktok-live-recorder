from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from utils.video_management import VideoManagement


def test_wait_for_file_release(tmp_path: Path):
    test_file = tmp_path / "test.mp4"
    test_file.write_text("sample")
    assert VideoManagement.wait_for_file_release(test_file, timeout=1) is True


def test_convert_flv_to_mp4_success(tmp_path: Path):
    raw_file = tmp_path / "stream_flv.mp4"
    raw_file.write_text("flv content")

    with patch("ffmpeg.input") as mock_input, patch("os.remove") as mock_remove:
        mock_output = MagicMock()
        mock_input.return_value.output.return_value = mock_output
        mock_output.run.return_value = None

        result_path = VideoManagement.convert_flv_to_mp4(str(raw_file))
        assert result_path == str(tmp_path / "stream.mp4")
        mock_remove.assert_called_once_with(str(raw_file))


def test_get_video_info(tmp_path: Path):
    test_file = tmp_path / "sample.mp4"
    test_file.write_bytes(b"0" * 2048)

    with patch("ffmpeg.probe") as mock_probe:
        mock_probe.return_value = {
            "format": {"duration": "125.5"},
            "streams": [{"codec_type": "video", "width": 1920, "height": 1080}],
        }
        info = VideoManagement.get_video_info(str(test_file))
        assert info["duration"] == 125.5
        assert info["width"] == 1920
        assert info["height"] == 1080
        assert info["size_bytes"] == 2048


def test_segment_video_small_file_no_segmentation(tmp_path: Path):
    test_file = tmp_path / "small.mp4"
    test_file.write_bytes(b"0" * 1000)

    parts = VideoManagement.segment_video(str(test_file), max_part_bytes=2000)
    assert len(parts) == 1
    assert parts[0] == str(test_file.resolve())
