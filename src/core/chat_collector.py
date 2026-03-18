import asyncio
import time
from pathlib import Path
from threading import Thread, Event

from utils.logger_manager import logger


class ChatCollector:
    """
    Collects live chat messages from a TikTok livestream using the
    TikTokLive library and writes them to a text file.

    Runs in a background thread so it does not block video recording.
    """

    def __init__(self, user: str, output_path: str):
        self.user = user
        self.output_path = output_path
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._client = None

    def start(self):
        """Start collecting chat messages in a background thread."""
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Chat collection started -> {Path(self.output_path).resolve()}")

    def stop(self):
        """Signal the collector to stop and wait for the thread to finish."""
        self._stop_event.set()

        if self._client is not None:
            try:
                # disconnect the TikTokLive client
                asyncio.run_coroutine_threadsafe(
                    self._client.disconnect(), self._loop
                )
            except Exception:
                pass

        if self._thread is not None:
            self._thread.join(timeout=10)
            logger.info("Chat collection stopped.")

    def _run(self):
        """Entry point executed inside the background thread."""
        try:
            from TikTokLive import TikTokLiveClient
            from TikTokLive.events import CommentEvent, ConnectEvent
        except ImportError:
            logger.error(
                "TikTokLive package is required for chat collection. "
                "Install it with: pip install TikTokLive"
            )
            return

        client = TikTokLiveClient(unique_id=f"@{self.user}")
        self._client = client

        chat_file = open(self.output_path, "a", encoding="utf-8")

        @client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            logger.info(
                f"Connected to chat for @{self.user} "
                f"(room_id: {client.room_id})"
            )

        @client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            line = f"[{timestamp}] {event.user.nickname}: {event.comment}\n"
            chat_file.write(line)
            chat_file.flush()

        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(client.connect())
        except Exception as e:
            if not self._stop_event.is_set():
                logger.warning(f"Chat collection ended: {e}")
        finally:
            chat_file.close()
            try:
                self._loop.close()
            except Exception:
                pass
