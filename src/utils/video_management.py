import os
import time
from pathlib import Path

import ffmpeg

from utils.logger_manager import logger


class VideoManagement:
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
    def convert_flv_to_mp4(file, bitrate=None, ffmpeg_path=None, audio_only=False):
        """
        Convert the video from flv format to mp4 (or opus) format
        """
        logger.info(f"Converting {file}...")

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

            if audio_only:
                output_file = file.replace("_flv.mp4", ".opus")
                output_args = {
                    "y": "-y",
                    "vn": None,
                    "ac": 1,
                    "c:a": "libopus",
                    "vbr": "on",
                    "compression_level": 10,
                    "application": "voip",
                    "b:a": "24k",
                }
            elif bitrate:
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
        logger.info(f"Finished converting {Path(output_file).resolve()}\n")
