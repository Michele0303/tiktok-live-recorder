from __future__ import annotations

import asyncio
import os
import signal
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.application import build_bot_application
from config.settings import load_settings
from delivery.telegram import TelegramDeliveryService
from storage.database import Database
from utils.dependencies import check_ffmpeg
from utils.logger_manager import logger
from utils.utils import banner
from watch.manager import WatchManager


async def run_service() -> None:
    banner()
    logger.info("Initializing TikTok Live Recorder - Telegram Watch Service...")

    try:
        settings = load_settings()
    except Exception as e:
        logger.critical(f"Configuration Error: {e}")
        sys.exit(1)

    # Validate FFmpeg
    try:
        check_ffmpeg(settings.ffmpeg_path)
    except Exception as e:
        logger.warning(f"FFmpeg check warning: {e}")

    settings.ensure_directories()

    db = Database(settings.database_path)
    delivery = TelegramDeliveryService(settings)
    watch_manager = WatchManager(settings, db, delivery)

    app = build_bot_application(settings, watch_manager)

    stop_event = asyncio.Event()

    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}. Initiating graceful shutdown...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Start Watch Manager background tasks
    await watch_manager.start()

    # Initialize Telegram bot
    await app.initialize()
    await app.start()
    if app.updater:
        await app.updater.start_polling(drop_pending_updates=False)

    logger.info("Telegram Watch Service is now running (long-polling active).")

    # Wait for shutdown signal
    await stop_event.wait()

    logger.info("Shutting down Telegram bot and workers...")
    if app.updater and app.updater.running:
        await app.updater.stop()
    if app.running:
        await app.stop()
    await app.shutdown()

    await watch_manager.stop()
    logger.info("Service shutdown completed cleanly.")


def main() -> None:
    try:
        asyncio.run(run_service())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Service terminated.")


if __name__ == "__main__":
    main()
