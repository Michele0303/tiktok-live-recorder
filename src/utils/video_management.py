import json
import os

# subprocess is required to enforce a timeout on ffprobe.
import subprocess  # nosec B404
import time
from pathlib import Path

import ffmpeg

from utils.logger_manager import logger


class VideoManagement:
    FFPROBE_TIMEOUT_SECONDS = 10

    @staticmethod
    def wait_for_file_release(file, timeout=10):
        """
        Wait until the file is released (not locked anymore) or timeout is reached.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with open(file, "ab"):
                    return True
            except PermissionError:
                time.sleep(0.5)
        return False

    @staticmethod
    def log_media_properties(file, ffmpeg_path=None):
        """Log the recorded file's video properties without failing conversion."""
        ffprobe_path = "ffprobe"
        if ffmpeg_path and os.path.dirname(ffmpeg_path):
            ffprobe_path = str(
                Path(ffmpeg_path).with_name(f"ffprobe{Path(ffmpeg_path).suffix}")
            )

        try:
            # Arguments are passed as a list and never through a shell.
            result = subprocess.run(  # nosec B603
                [
                    ffprobe_path,
                    "-show_format",
                    "-show_streams",
                    "-of",
                    "json",
                    file,
                ],
                capture_output=True,
                check=True,
                text=True,
                timeout=VideoManagement.FFPROBE_TIMEOUT_SECONDS,
            )
            probe_data = json.loads(result.stdout)
        except (
            OSError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            ValueError,
        ) as error:
            logger.warning("Unable to inspect recorded media: %s", error)
            return

        video_stream = next(
            (
                stream
                for stream in probe_data.get("streams", [])
                if stream.get("codec_type") == "video"
            ),
            None,
        )
        if not video_stream:
            logger.warning("Recorded media does not contain a video stream.")
            return

        bitrate = probe_data.get("format", {}).get("bit_rate")
        try:
            bitrate_kbps = f"{int(bitrate) // 1000} kbps" if bitrate else "unknown"
        except (TypeError, ValueError):
            bitrate_kbps = "unknown"
        logger.info(
            "Recorded media properties: codec=%s, resolution=%sx%s, bitrate=%s",
            video_stream.get("codec_name", "unknown"),
            video_stream.get("width", "unknown"),
            video_stream.get("height", "unknown"),
            bitrate_kbps,
        )

    @staticmethod
    def convert_flv_to_mp4(file, bitrate=None, ffmpeg_path=None):
        """
        Convert the video from flv format to mp4 format
        """
        logger.info("Converting {} to MP4 format...".format(file))

        if not VideoManagement.wait_for_file_release(file):
            logger.error(
                f"File {file} is still locked after waiting. Skipping conversion."
            )
            return

        try:
            output_args = {
                "c": "copy",
                "y": "-y",
            }
            output_file = file.replace("_flv.mp4", ".mp4")

            if bitrate:
                logger.warning(
                    "The -bitrate option re-encodes video with libx264 and may reduce "
                    "source quality. Omit it to preserve the original stream."
                )
                output_args["b:v"] = bitrate
                del output_args["c"]
                output_args["c:v"] = "libx264"
                output_args["c:a"] = "copy"

            ffmpeg.input(file).output(output_file, **output_args).run(
                quiet=True, cmd=ffmpeg_path or "ffmpeg"
            )

        except ffmpeg.Error as e:
            logger.error(
                f"ffmpeg conversion failed: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}"
            )
            return

        os.remove(file)
        VideoManagement.log_media_properties(output_file, ffmpeg_path)
        logger.info(f"Finished converting {Path(output_file).resolve()}\n")
