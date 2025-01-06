from pyrogram import Client
from utils.utils import read_telegram_config
from utils.logger_manager import logger
from pathlib import Path

telegram_config = read_telegram_config()
session_string = telegram_config.get("session_string")


class UploadToTelegram:
    def __init__(self, session_string, file):
        self.session_string = session_string
        self.file = file
        self.app = None
        self.me = None

    def _validate_size_file(self):
        """
        Check if the file size is less than 2GB or 4GB if the user is a premium user.
        """
        if self.me.premium():
            logger.info(f"{self.me.username} is a premium user.")
            return Path(self.file).stat().st_size < 4 * 1024 * 1024 * 1024
        return Path(self.file).stat().st_size < 2 * 1024 * 1024 * 1024

    def upload(self):
        """
        Upload the video to Telegram.
        """
        if not self.session_string:
            logger.error("Telegram session string not found.")
            return

        self.app = Client(
            "my_account",
            session_string=self.session_string,
        )

        with self.app:
            self.me = self.app.get_me()
            logger.info(f"Logged in as {self.me.username}")

            if not self._validate_size_file():
                logger.error("The file is too large to be uploaded.")
                return

            try:
                self.app.send_file(
                    chat_id=self.me.id,
                    file=self.file,
                    progress=UploadToTelegram.progress,
                )
                logger.info(f"Video uploaded successfully to {self.me.username}")
            except Exception as e:
                logger.error(f"Error uploading the video: {e}")
