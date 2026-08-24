from __future__ import annotations

from typing import Any

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from telegram.request import HTTPXRequest

from bot.commands import (
    help_command,
    latest_command,
    record_command,
    recordings_command,
    start_command,
    status_command,
    stop_command,
    storage_command,
    unwatch_command,
    watch_command,
    watching_command,
)
from config.settings import Settings
from utils.logger_manager import logger
from watch.manager import WatchManager


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log uncaught exceptions in bot handlers."""
    logger.error(
        f"Exception while handling Telegram update {update}: {context.error}",
        exc_info=context.error,
    )
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ An unexpected error occurred while processing your command."
            )
        except Exception:
            pass


def build_bot_application(
    settings: Settings, watch_manager: WatchManager
) -> Application[Any, Any, Any, Any, Any, Any]:
    """Construct and configure python-telegram-bot Application."""
    request = HTTPXRequest(
        connection_pool_size=16,
        read_timeout=60.0,
        write_timeout=60.0,
        connect_timeout=30.0,
        pool_timeout=30.0,
    )

    builder = ApplicationBuilder().token(settings.telegram_bot_token).request(request)

    if settings.telegram_bot_api_base_url:
        builder = builder.base_url(settings.telegram_bot_api_base_url)
    if settings.telegram_bot_api_file_base_url:
        builder = builder.base_file_url(settings.telegram_bot_api_file_base_url)

    app = builder.build()

    # Store references in bot_data for handlers
    app.bot_data["settings"] = settings
    app.bot_data["watch_manager"] = watch_manager

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("watch", watch_command))
    app.add_handler(CommandHandler("unwatch", unwatch_command))
    app.add_handler(CommandHandler("watching", watching_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("record", record_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("latest", latest_command))
    app.add_handler(CommandHandler("recordings", recordings_command))
    app.add_handler(CommandHandler("storage", storage_command))

    app.add_error_handler(error_handler)

    return app
