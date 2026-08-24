from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import Settings
from utils.logger_manager import logger


def is_authorized(update: Update, settings: Settings) -> bool:
    """Check if the update originates from the configured Telegram user and chat."""
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return False

    return (
        user.id == settings.telegram_allowed_user_id
        and chat.id == settings.telegram_allowed_chat_id
    )


def authorized_only(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to enforce Telegram user and chat authorization."""
    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any
    ) -> Any:
        settings: Settings = context.bot_data.get("settings")
        if not settings:
            logger.error("Settings not found in bot_data.")
            return

        if not is_authorized(update, settings):
            uid = update.effective_user.id if update.effective_user else "unknown"
            cid = update.effective_chat.id if update.effective_chat else "unknown"
            logger.warning(
                f"Unauthorized command attempt blocked: user_id={uid}, chat_id={cid}"
            )
            # Silent drop or generic response without leaking internal state
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⛔ Unauthorized access."
                )
            return

        return await func(update, context, *args, **kwargs)

    return wrapper
