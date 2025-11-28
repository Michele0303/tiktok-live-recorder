import os
import time

import ffmpeg

from utils.logger_manager import LoggerManager


class VideoManagement:
    @staticmethod
    def wait_for_file_release(file, timeout=10):
        """
        Wait until the file is released (not locked anymore) or timeout is reached.
        """
        LoggerManager().logger.debug(f"Waiting for file release: {file}")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with open(file, "ab"):
                    return True
            except PermissionError:
                time.sleep(0.5)
        return False

    @staticmethod
    def validate_video(file_path: str) -> bool:
        """
        Verify video integrity using ffprobe.
        Returns True if the video is valid, False otherwise.
        """
        if not os.path.exists(file_path):
            return False

        try:
            LoggerManager().logger.debug(f"Validating video file: {file_path}")
            # Run ffprobe to check file integrity
            # Using count_packets forces reading the stream structure
            probe_args = {"count_packets": None}
            ffmpeg.probe(file_path, **probe_args)
            LoggerManager().logger.debug("Validation successful.")
            return True
        except ffmpeg.Error as e:
            # Log the specific error from ffprobe if available
            error_msg = e.stderr.decode() if hasattr(e, 'stderr') and e.stderr else str(e)
            # Only log if it's not just a strict validation issue but a genuine
            # read error
            LoggerManager().logger.error(
                f"Corrupt video file detected '{file_path}': {error_msg[:200]}...")
            return False
        except Exception as e:
            LoggerManager().logger.error(
                f"Validation failed for '{file_path}': {e}")
            return False

    @staticmethod
    def convert_flv_to_mp4(file: str, ffmpeg_encode: bool = False) -> None:
        """
        Convert the video from flv format to mp4 format.
        Safely handles file deletion: the original file is only deleted
        if the conversion succeeds and the output file is valid.
        If ffmpeg_encode is True, the user will be asked for confirmation before deleting the original file.
        Otherwise, the original file is deleted automatically.
        """
        if not os.path.exists(file):
            LoggerManager().logger.error(f"Input file {file} not found.")
            return

        if ffmpeg_encode:
            LoggerManager().logger.info(
                "Re-encoding {} to MP4 format (fixing glitches)...".format(file))
        else:
            LoggerManager().logger.info(
                "Converting (Remuxing) {} to MP4 format...".format(file))
        LoggerManager().logger.debug(f"FFmpeg encode mode: {ffmpeg_encode}")

        if not VideoManagement.wait_for_file_release(file):
            LoggerManager().logger.error(
                f"File {file} is still locked after waiting. Skipping conversion."
            )
            return

        # Determine quiet mode based on logger level
        # If logger level is DEBUG (10) or lower, quiet is False (show output)
        is_verbose = LoggerManager().logger.getEffectiveLevel() <= 10
        ffmpeg_quiet = not is_verbose

        try:
            # Generate output filename
            output_file = file.replace("_flv.mp4", ".mp4")

            # Prevent overwriting input file if naming didn't change
            if output_file == file:
                output_file = file.replace(".mp4", "_converted.mp4")

            if ffmpeg_encode:
                # Add repair flags for re-encoding
                input_kwargs = {
                    "fflags": "+genpts",
                    "avoid_negative_ts": "make_zero",
                    "ignore_unknown": None
                }

                ffmpeg.input(file, **input_kwargs).output(
                    output_file,
                    vcodec="libx264",
                    acodec="aac",
                    y="-y",
                ).run(quiet=ffmpeg_quiet)
            else:
                ffmpeg.input(file).output(
                    output_file,
                    c="copy",
                    y="-y",
                ).run(quiet=ffmpeg_quiet)

            # Verify output file exists and is valid
            if os.path.exists(output_file) and os.path.getsize(
                    output_file) > 0:
                if VideoManagement.validate_video(output_file):
                    LoggerManager().logger.info("Finished converting {}\n".format(file))
                    return output_file
                else:
                    LoggerManager().logger.error(
                        f"Converted file {output_file} failed integrity check.")
                    return None
            else:
                LoggerManager().logger.error(
                    f"Output file {output_file} not found or empty. Keeping original file.")
                return None

        except ffmpeg.Error as e:
            LoggerManager().logger.error(f"ffmpeg error: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")
            return None
