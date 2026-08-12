import subprocess
from pathlib import Path
from utils.logger_manager import logger


class VideoManagement:
    @staticmethod
    def convert_flv_to_mp4(
        input_path: str,
        bitrate: str = None,
        ffmpeg_path: str = None,
        audio_only: bool = False,
    ):
        """
        Converts/Remuxes raw recorded stream to formatted MP4 or Audio (M4A/MP3).
        """
        if not Path(input_path).exists():
            logger.error(f"File not found: {input_path}")
            return

        ffmpeg_bin = ffmpeg_path if ffmpeg_path else "ffmpeg"

        # अस्थायी या आउटपुट फ़ाइल पथ तैयार करें
        input_file = Path(input_path)

        # ⚡ Audio-Only के लिए एक्सटेंशन चुनें
        if audio_only:
            output_file = input_file.with_suffix(".m4a")
        else:
            output_file = input_file.with_suffix(".mp4")

        # यदि इनपुट और आउटपुट फ़ाइल का नाम समान है तो टेम्परेरी नाम इस्तेमाल करें
        temp_output = input_file.with_name(f"temp_{output_file.name}")

        # FFmpeg Base Command
        cmd = [ffmpeg_bin, "-y", "-i", str(input_file)]

        # ⚡ यदि audio_only ट्रु है तो -vn फ्लैग जोड़ें (No Video)
        if audio_only:
            cmd.extend(["-vn", "-c:a", "copy"])
        else:
            cmd.extend(["-c:v", "copy", "-c:a", "copy"])

            # यदि यूज़र ने कस्टम बिटरेट सेट किया है
            if bitrate:
                cmd.extend(["-b:v", bitrate])

        cmd.append(str(temp_output))

        try:
            logger.info(
                f"Converting recording ({'Audio-only' if audio_only else 'Video'})..."
            )
            subprocess.run(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
            )

            # ओरिजिनल रॉ फ़ाइल को रीप्लेस / डिलीट करें
            input_file.unlink(missing_ok=True)
            temp_output.rename(output_file)

            logger.info(f"Conversion completed successfully: {output_file.resolve()}")

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e}")
            if temp_output.exists():
                temp_output.unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"Error during video/audio management: {e}")