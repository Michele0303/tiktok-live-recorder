from __future__ import annotations

import math
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import ffmpeg

from utils.logger_manager import logger


class VideoManagement:
    @staticmethod
    def wait_for_file_release(file: str | Path, timeout: float = 10.0) -> bool:
        """
        Wait until the file is released (not locked anymore) or timeout is reached.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with open(file, "ab"):
                    return True
            except (PermissionError, OSError):
                time.sleep(0.5)
        return False

    @staticmethod
    def convert_flv_to_mp4(
        file: str, bitrate: str | None = None, ffmpeg_path: str | None = None
    ) -> str | None:
        """
        Convert the video from flv format to mp4 format and return the output path.
        """
        logger.info(f"Converting {file} to MP4 format...")

        if not VideoManagement.wait_for_file_release(file):
            logger.error(
                f"File {file} is still locked after waiting. Skipping conversion."
            )
            return None

        try:
            output_args: dict[str, Any] = {
                "c": "copy",
                "y": "-y",
            }
            if file.endswith("_flv.mp4"):
                output_file = file.replace("_flv.mp4", ".mp4")
            elif file.endswith(".flv"):
                output_file = file[:-4] + ".mp4"
            else:
                output_file = f"{file}.mp4"

            if bitrate:
                output_args["b:v"] = bitrate
                if "c" in output_args:
                    del output_args["c"]
                output_args["c:v"] = "libx264"
                output_args["c:a"] = "copy"

            ffmpeg.input(file).output(output_file, **output_args).run(
                quiet=True, cmd=ffmpeg_path or "ffmpeg"
            )

        except ffmpeg.Error as e:
            err_msg = (
                e.stderr.decode(errors="replace")
                if hasattr(e, "stderr") and e.stderr
                else str(e)
            )
            logger.error(f"ffmpeg conversion failed: {err_msg}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during ffmpeg conversion: {e}")
            return None

        try:
            os.remove(file)
        except OSError:
            pass

        logger.info(f"Finished converting {Path(output_file).resolve()}\n")
        return output_file

    @staticmethod
    def get_video_info(
        file_path: str, ffmpeg_path: str | None = None
    ) -> dict[str, Any]:
        """
        Retrieve video duration, size, and metadata using ffprobe.
        """
        path = Path(file_path)
        size_bytes = path.stat().st_size if path.is_file() else 0
        info: dict[str, Any] = {
            "path": str(path.resolve()),
            "size_bytes": size_bytes,
            "duration": 0.0,
            "width": None,
            "height": None,
        }

        if not path.is_file() or size_bytes == 0:
            return info

        probe_cmd = "ffprobe"
        if ffmpeg_path and ffmpeg_path != "ffmpeg":
            candidate = Path(ffmpeg_path).parent / "ffprobe"
            if candidate.exists():
                probe_cmd = str(candidate)

        try:
            probe_data = ffmpeg.probe(str(path), cmd=probe_cmd)
            format_info = probe_data.get("format", {})
            duration_raw = format_info.get("duration")
            if duration_raw:
                info["duration"] = float(duration_raw)

            for stream in probe_data.get("streams", []):
                if stream.get("codec_type") == "video":
                    info["width"] = stream.get("width")
                    info["height"] = stream.get("height")
                    break
        except Exception as e:
            logger.debug(f"ffprobe failed for {file_path}: {e}")

        return info

    @staticmethod
    def segment_video(
        file_path: str,
        max_part_bytes: int = 1_932_735_283,
        ffmpeg_path: str | None = None,
    ) -> list[str]:
        """
        Split an MP4 file into sequential parts if it exceeds max_part_bytes using FFmpeg stream copy.
        """
        path = Path(file_path)
        if not path.is_file():
            return []

        file_size = path.stat().st_size
        if file_size <= max_part_bytes:
            return [str(path.resolve())]

        # Calculate number of segments with safety margin
        safe_target_bytes = max_part_bytes * 0.90
        num_parts = max(2, math.ceil(file_size / safe_target_bytes))

        video_info = VideoManagement.get_video_info(
            file_path, ffmpeg_path=ffmpeg_path
        )
        total_duration = video_info.get("duration", 0.0)

        if total_duration <= 0:
            # Fallback estimation if duration is unknown: assume 1MB/sec
            total_duration = file_size / (1024 * 1024)

        segment_time = max(10.0, total_duration / num_parts)
        parent_dir = path.parent
        stem = path.stem
        output_pattern = str(parent_dir / f"{stem}_part_%03d.mp4")

        cmd = [
            ffmpeg_path or "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-c",
            "copy",
            "-map",
            "0",
            "-f",
            "segment",
            "-segment_time",
            f"{segment_time:.2f}",
            "-reset_timestamps",
            "1",
            output_pattern,
        ]

        logger.info(
            f"Segmenting {path.name} ({file_size / (1024**3):.2f} GB) into parts with segment_time={segment_time:.1f}s..."
        )
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except Exception as e:
            logger.error(f"FFmpeg segmentation failed: {e}")
            return [str(path.resolve())]

        parts = sorted(
            [str(p.resolve()) for p in parent_dir.glob(f"{stem}_part_*.mp4")]
        )
        if parts:
            logger.info(f"Successfully segmented into {len(parts)} parts.")
            return parts

        return [str(path.resolve())]
