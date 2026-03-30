import os
import time
from pathlib import Path

import ffmpeg

from utils.enums import OutputFormat
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
    def _final_path_from_raw_capture(raw_path: str, extension: str) -> str:
        raw_path = os.fspath(raw_path)
        suffix = "_raw.flv"
        if raw_path.endswith(suffix):
            base = raw_path[: -len(suffix)]
        else:
            base = str(Path(raw_path).with_suffix(""))
        return f"{base}.{extension}"

    @staticmethod
    def finalize_recording(
        raw_path: str, output_format: str, bitrate: str | None = None
    ) -> None:
        """
        Turn the captured FLV stream into the requested container format.
        """
        allowed = {f.value for f in OutputFormat}
        if output_format not in allowed:
            logger.error(f"Unsupported output format: {output_format}")
            return

        if not VideoManagement.wait_for_file_release(raw_path):
            logger.error(
                f"File {raw_path} is still locked after waiting. Skipping conversion."
            )
            return

        output_file = VideoManagement._final_path_from_raw_capture(
            raw_path, output_format
        )

        if output_format == OutputFormat.FLV.value:
            if bitrate:
                try:
                    ffmpeg.input(raw_path).output(
                        output_file,
                        **{
                            "b:v": bitrate,
                            "c:v": "libx264",
                            "c:a": "aac",
                            "y": "-y",
                        },
                    ).run(quiet=True)
                    os.remove(raw_path)
                    logger.info(f"Finished encoding {Path(output_file).resolve()}\n")
                except ffmpeg.Error as e:
                    logger.error(
                        f"ffmpeg encoding failed: "
                        f"{e.stderr.decode() if hasattr(e, 'stderr') else str(e)}"
                    )
            else:
                os.replace(raw_path, output_file)
                logger.info(f"Recording saved: {Path(output_file).resolve()}\n")
            return

        logger.info(f"Converting {raw_path} to {output_format.upper()}...")

        try:
            output_args: dict = {"c": "copy", "y": "-y"}
            if bitrate:
                output_args.pop("c", None)
                output_args["b:v"] = bitrate
                output_args["c:v"] = "libx264"
                output_args["c:a"] = "copy"

            ffmpeg.input(raw_path).output(output_file, **output_args).run(quiet=True)

        except ffmpeg.Error as e:
            logger.error(
                f"ffmpeg conversion failed: "
                f"{e.stderr.decode() if hasattr(e, 'stderr') else str(e)}"
            )
            return

        os.remove(raw_path)
        logger.info(f"Finished converting {Path(output_file).resolve()}\n")
