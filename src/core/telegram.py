from pathlib import Path

from utils.logger_manager import logger
from utils.utils import read_telegram_config

telegram_config = read_telegram_config()
session_string = telegram_config.get("session_string")
FREE_USER_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
PREMIUM_USER_MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024


class Telegram:
    def __init__(self):
        self.session_string = session_string
        self.file = None
        self.app = None
        self.me = None
        self.username = None

    def validate_size_file(self):
        """
        Check if the file size is less than 2GB or 4GB if the user is a premium user.
        """
        is_premium = self.me.is_premium
        self.username = self.me.username
        id = self.me.id

        if not self.username:
            self.username = id

        if is_premium:
            logger.info(f"{self.username} is a premium user.")
            return Path(self.file).stat().st_size <= PREMIUM_USER_MAX_FILE_SIZE

        return Path(self.file).stat().st_size <= FREE_USER_MAX_FILE_SIZE

    def upload(self, file):
        """
        Upload the video to Telegram.
        """
        from pyrogram import Client

        self.file = file
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

            if not self.validate_size_file():
                logger.error("The file is too large to be uploaded.")
                return

            try:
                logger.info(f"Uploading video to {self.username}...")
                file_size = Path(self.file).stat().st_size
                logger.info(f"File size: {round(file_size / (1024 * 1024))} MB")
                logger.info("This may take a while depending on the file size.")
                self.app.send_document(
                    chat_id=self.me.id,
                    document=self.file,
                    caption=f"{Path(self.file).name}",
                    force_document=True,
                )
                logger.info(f"Video uploaded successfully to {self.username}")
            except Exception as e:
                logger.error(f"Error uploading the video: {e}")
