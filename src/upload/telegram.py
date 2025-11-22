import asyncio
from pathlib import Path

from telethon import TelegramClient

from utils.logger_manager import logger
from utils.utils import read_telegram_config


FREE_USER_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
PREMIUM_USER_MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024


class Telegram:
    def __init__(self):
        config = read_telegram_config()

        self.api_id = config["api_id"]
        self.api_hash = config["api_hash"]
        self.chat_id = config["chat_id"]

        self.client = TelegramClient(
            "tiktok_live_recorder_session",
            api_id=self.api_id,
            api_hash=self.api_hash,
        )

    def upload(self, file_path: str):
        """
        Upload a file to the user's Saved Messages via Telethon.
        """

        async def _upload():
            try:
                await self.client.connect()

                if not await self.client.is_user_authorized():
                    await self.client.start()

                me = await self.client.get_me()
                is_premium = me.premium
                max_size = (
                    PREMIUM_USER_MAX_FILE_SIZE
                    if is_premium
                    else FREE_USER_MAX_FILE_SIZE
                )

                file_size = Path(file_path).stat().st_size
                logger.info(
                    f"File to upload: {Path(file_path).name} "
                    f"({round(file_size / (1024 * 1024))} MB)"
                )

                if file_size > max_size:
                    logger.warning(
                        "The file is too large to be uploaded "
                        "with this type of account."
                    )
                    return

                logger.info(
                    "Uploading video on Telegram... "
                    "This may take a while depending on file size."
                )

                await self.client.send_file(
                    entity=self.chat_id,
                    file=file_path,
                    caption=(
                        "🎥 <b>Video recorded via "
                        '<a href="https://github.com/Michele0303/'
                        'tiktok-live-recorder">'
                        "TikTok Live Recorder</a></b>"
                    ),
                    parse_mode="html",
                    force_document=True,
                )

                logger.info("File successfully uploaded to Telegram.\n")

            except Exception as e:
                logger.error(f"Error during Telegram upload: {e}\n")

            finally:
                await self.client.disconnect()

        asyncio.run(_upload())
