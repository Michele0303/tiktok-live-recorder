import os
import time

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
    def convert_flv_to_mp4(file):
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
            ffmpeg.input(file).output(
                file.replace("_flv.mp4", ".mp4"),
                c="copy",
                y="-y",
            ).run(quiet=True)
        except ffmpeg.Error as e:
            logger.error(
                f"ffmpeg error: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}"
            )

        os.remove(file)

        logger.info("Finished converting {}\n".format(file))
