from __future__ import annotations

import asyncio
from pathlib import Path

from telegram import Bot
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest

from config.settings import Settings
from utils.logger_manager import logger
from utils.video_management import VideoManagement


def format_duration(seconds: float) -> str:
    """Format duration into human readable string like '1h 42m' or '25m 10s'."""
    sec = int(round(seconds))
    if sec < 60:
        return f"{sec}s"
    minutes = sec // 60
    rem_sec = sec % 60
    if minutes < 60:
        return f"{minutes}m {rem_sec}s" if rem_sec > 0 else f"{minutes}m"
    hours = minutes // 60
    rem_min = minutes % 60
    return f"{hours}h {rem_min}m"


def format_size(bytes_num: int) -> str:
    """Format bytes into human readable string like '1.7 GB' or '450 MB'."""
    if bytes_num < 1024:
        return f"{bytes_num} B"
    kb = bytes_num / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f} MB"
    gb = mb / 1024
    return f"{gb:.2f} GB"


class TelegramDeliveryService:
    def __init__(self, settings: Settings, bot: Bot | None = None):
        self.settings = settings
        self.chat_id = settings.telegram_allowed_chat_id
        if bot is not None:
            self.bot = bot
        else:
            request = HTTPXRequest(
                connection_pool_size=8,
                read_timeout=600.0,
                write_timeout=600.0,
                connect_timeout=60.0,
                pool_timeout=60.0,
            )
            bot_kwargs = {
                "token": settings.telegram_bot_token,
                "request": request,
            }
            if settings.telegram_bot_api_base_url:
                bot_kwargs["base_url"] = settings.telegram_bot_api_base_url
            if settings.telegram_bot_api_file_base_url:
                bot_kwargs["base_file_url"] = settings.telegram_bot_api_file_base_url
            self.bot = Bot(**bot_kwargs)

    async def send_message(
        self,
        text: str,
        parse_mode: str = ParseMode.HTML,
        reply_to_message_id: int | None = None,
    ) -> int | None:
        """Send a formatted notification message to the configured chat."""
        try:
            msg = await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id,
            )
            return msg.message_id
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return None

    async def send_recording_video(
        self,
        file_path: str,
        caption: str | None = None,
        duration: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> int | None:
        """Upload a video file to the configured Telegram chat."""
        path = Path(file_path)
        if not path.is_file():
            logger.error(f"Cannot upload non-existent video: {file_path}")
            return None

        # Probe video parameters if missing
        if duration is None or width is None or height is None:
            info = VideoManagement.get_video_info(
                file_path, ffmpeg_path=self.settings.ffmpeg_path
            )
            duration = int(round(info.get("duration", 0.0))) or None
            width = info.get("width")
            height = info.get("height")

        logger.info(
            f"Uploading video {path.name} ({format_size(path.stat().st_size)}) to Telegram chat {self.chat_id}..."
        )

        try:
            with open(path, "rb") as video_file:
                msg = await self.bot.send_video(
                    chat_id=self.chat_id,
                    video=video_file,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    duration=duration,
                    width=width,
                    height=height,
                    supports_streaming=True,
                    read_timeout=900.0,
                    write_timeout=900.0,
                )
                logger.info(f"Video {path.name} uploaded successfully (msg ID: {msg.message_id}).")
                return msg.message_id
        except Exception as e:
            logger.warning(
                f"send_video failed ({e}), attempting fallback as document for {path.name}..."
            )
            try:
                with open(path, "rb") as doc_file:
                    msg = await self.bot.send_document(
                        chat_id=self.chat_id,
                        document=doc_file,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        read_timeout=900.0,
                        write_timeout=900.0,
                    )
                    logger.info(
                        f"Video {path.name} uploaded as document successfully (msg ID: {msg.message_id})."
                    )
                    return msg.message_id
            except Exception as doc_err:
                logger.error(
                    f"Telegram video upload completely failed for {path.name}: {doc_err}. Local file retained."
                )
                return None

    async def deliver_recording(
        self,
        username: str,
        duration_seconds: float,
        total_size_bytes: int,
        video_paths: list[str],
    ) -> list[int]:
        """Deliver recording completion summary and all video part(s) to Telegram."""
        sent_message_ids: list[int] = []
        parts_count = len(video_paths)
        dur_str = format_duration(duration_seconds)
        size_str = format_size(total_size_bytes)

        if parts_count > 1:
            summary = (
                f"✅ <b>Recording complete</b>\n\n"
                f"👤 @{username}\n"
                f"⏱ Duration: {dur_str}\n"
                f"📦 Total Size: {size_str}\n"
                f"🧩 Parts: {parts_count}"
            )
        else:
            summary = (
                f"✅ <b>Recording complete</b>\n\n"
                f"👤 @{username}\n"
                f"⏱ Duration: {dur_str}\n"
                f"📦 Size: {size_str}"
            )

        summary_msg_id = await self.send_message(summary)
        if summary_msg_id:
            sent_message_ids.append(summary_msg_id)

        for idx, part_path in enumerate(video_paths, start=1):
            part_caption = None
            if parts_count > 1:
                part_caption = (
                    f"🎬 @{username} — Part {idx}/{parts_count}\n"
                    f"📦 {format_size(Path(part_path).stat().st_size)}"
                )
            else:
                part_caption = f"🎬 @{username}\n⏱ {dur_str} • 📦 {size_str}"

            msg_id = await self.send_recording_video(
                file_path=part_path,
                caption=part_caption,
            )
            if msg_id:
                sent_message_ids.append(msg_id)

            if idx < parts_count:
                await asyncio.sleep(2)

        return sent_message_ids
