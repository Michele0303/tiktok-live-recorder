from pathlib import Path

from pyrogram import Client
from pyrogram.enums import ParseMode

from utils.logger_manager import logger
from utils.utils import read_telegram_config


FREE_USER_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
PREMIUM_USER_MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024


class Telegram:

    def __init__(self):
        config = read_telegram_config()

        self.api_id = config["api_id"]
        self.api_hash = config["api_hash"]
        self.bot_token = config["bot_token"]
        self.chat_id = config["chat_id"]

        self.app = Client(
            'telegram_session',
            api_id=self.api_id,
            api_hash=self.api_hash,
            bot_token=self.bot_token
        )

    def upload(self, file_path: str):
        """
        Upload a file to the bot's own chat (saved messages).
        """
        try:
            self.app.start()

            me = self.app.get_me()
            is_premium = me.is_premium
            max_size = (
                PREMIUM_USER_MAX_FILE_SIZE
                if is_premium else FREE_USER_MAX_FILE_SIZE
            )

            file_size = Path(file_path).stat().st_size
            logger.info(f"File to upload: {Path(file_path).name} "
                        f"({round(file_size / (1024 * 1024))} MB)")

            if file_size > max_size:
                logger.warning("The file is too large to be "
                               "uploaded with this type of account.")
                return

            logger.info(f"Uploading video on Telegram...")
            logger.info("This may take a while depending on the file size.")
            self.app.send_document(
                chat_id=self.chat_id,
                document=file_path,
                caption=(
                    '🎥 <b>Video recorded via <a href="https://github.com/Michele0303/tiktok-live-recorder">'
                    'TikTok Live Recorder</a></b>'
                ),
                parse_mode=ParseMode.HTML,
                force_document=True,
            )
            logger.info("File successfully uploaded to Telegram.")

        except Exception as e:
            logger.error(f"Error during Telegram upload: {e}")

        finally:
            self.app.stop()
