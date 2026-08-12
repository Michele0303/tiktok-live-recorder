import os
import subprocess
import time
from pathlib import Path

import ffmpeg

from utils.logger_manager import logger


class VideoManagement:
    @staticmethod
    def download_hls_stream(
        live_url,
        duration=None,
        ffmpeg_path=None,
        headers=None,
    ):
        """Yield MPEG-TS bytes while FFmpeg follows an HLS playlist."""
        input_args = {"rw_timeout": 15_000_000}
        request_headers = dict(headers or {})
        user_agent = request_headers.pop("User-Agent", None)

        if user_agent:
            input_args["user_agent"] = user_agent
        if request_headers:
            input_args["headers"] = "".join(
                f"{name}: {value}\r\n" for name, value in request_headers.items()
            )

        output_args = {"c": "copy", "f": "mpegts"}
        if duration:
            output_args["t"] = duration

        process = (
            ffmpeg.input(live_url, **input_args)
            .output("pipe:1", **output_args)
            .global_args("-loglevel", "error", "-nostats")
            .run_async(
                cmd=ffmpeg_path or "ffmpeg",
                pipe_stdout=True,
            )
        )

        try:
            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                yield chunk

            return_code = process.wait()
            if return_code:
                raise RuntimeError(f"FFmpeg HLS reader exited with code {return_code}")
        finally:
            if process.stdout:
                process.stdout.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

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
    def convert_to_mp4(file, bitrate=None, ffmpeg_path=None):
        """
        Convert a temporary stream file to MP4.
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
            if file.endswith("_flv.mp4"):
                output_file = file.removesuffix("_flv.mp4") + ".mp4"
            elif file.endswith("_hls.ts"):
                output_file = file.removesuffix("_hls.ts") + ".mp4"
            else:
                output_file = str(Path(file).with_suffix(".mp4"))

            if bitrate:
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

    @staticmethod
    def convert_flv_to_mp4(file, bitrate=None, ffmpeg_path=None):
        """Backward-compatible wrapper for temporary FLV recordings."""
        return VideoManagement.convert_to_mp4(file, bitrate, ffmpeg_path)
