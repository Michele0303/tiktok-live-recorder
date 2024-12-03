import os
import ffmpeg

from utils.logger_manager import logger


class VideoManagement:

    @staticmethod
    def convert_flv_to_mp4(file):
        """
        Convert the video from flv format to mp4 format
        """
        try:
            logger.info("Converting {} to MP4 format...".format(file))

            ffmpeg.input(file).output(
                file.replace('_flv.mp4', '.mp4'), y='-y'
            ).run(quiet=True)
            os.remove(file)

            logger.info("Finished converting {}".format(file))
        except FileNotFoundError:
            logger.error("FFmpeg is not installed.")
