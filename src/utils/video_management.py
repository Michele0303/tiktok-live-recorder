import os
import ffmpeg

from utils.logger_manager import logger


class VideoManagement:

    @staticmethod
    def convert_flv_to_mp4(file):
        """
        Convert the video from flv format to mp4 format
        """
        logger.info("Converting {} to MP4 format...".format(file))

        try:
            ffmpeg.input(file).output(
                file.replace('_flv.mp4', '.mp4'),
                c='copy',
                y='-y',
            ).run(quiet=True)
        except ffmpeg.Error as e:
            logger.error(f"ffmpeg error: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")

        os.remove(file)

        logger.info("Finished converting {}\n".format(file))
