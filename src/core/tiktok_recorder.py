from __future__ import annotations

import datetime
import threading
import time
from dataclasses import dataclass
from http.client import HTTPException
from pathlib import Path
from threading import Thread

from requests import RequestException

from core.tiktok_api import TikTokAPI
from utils.custom_exceptions import LiveNotFound, TikTokRecorderError, UserLiveError
from utils.enums import Error, Mode, TikTokError, TimeOut
from utils.logger_manager import logger
from utils.recorder_config import RecorderConfig
from utils.video_management import VideoManagement


@dataclass
class RecordingResult:
    username: str
    room_id: str | None
    started_at: str
    ended_at: str
    duration_seconds: float
    raw_path: str | None
    final_path: str | None
    size_bytes: int
    status: str
    error: str | None = None


class TikTokRecorder:
    def __init__(
        self,
        config: RecorderConfig,
        stop_event: threading.Event | None = None,
    ):
        self.tiktok = TikTokAPI(proxy=config.proxy, cookies=config.cookies)

        self.url = config.url
        self.user = config.user
        self.room_id = config.room_id
        self.mode = config.mode
        self.automatic_interval = config.automatic_interval
        self.duration = config.duration
        self.output = config.output
        self.bitrate = config.bitrate
        self.ffmpeg_path = config.ffmpeg_path
        self.use_telegram = config.use_telegram
        self._proxy = config.proxy
        self._cookies = config.cookies

        self._stop_event = stop_event or threading.Event()
        self._is_stopped = False
        self.last_result: RecordingResult | None = None

    def stop(self) -> None:
        """Signal the recorder to stop recording gracefully."""
        self._is_stopped = True
        self._stop_event.set()

    def _setup(self):
        """Resolve user/room data and validate prerequisites via network calls."""
        if self.mode == Mode.FOLLOWERS:
            self.check_country_blacklisted()

            self.sec_uid = self.tiktok.get_sec_uid()
            if self.sec_uid is None:
                raise TikTokRecorderError("Failed to retrieve sec_uid.")

            logger.info("Followers mode activated\n")
        else:
            if self.url:
                self.user, self.room_id = self.tiktok.get_room_and_user_from_url(
                    self.url
                )

            if not self.user:
                self.user = self.tiktok.get_user_from_room_id(self.room_id)

            if not self.room_id:
                self.room_id = self.tiktok.get_room_id_from_user(self.user)

            self.check_country_blacklisted()

            logger.info(f"USERNAME: {self.user}" + ("\n" if not self.room_id else ""))
            if self.room_id:
                logger.info(
                    f"ROOM_ID:  {self.room_id}"
                    + ("\n" if not self.tiktok.is_room_alive(self.room_id) else "")
                )

        # If proxy was used for the initial checks, switch to a direct connection
        # for the actual stream download to avoid proxy bottlenecks
        if self._proxy:
            self.tiktok = TikTokAPI(proxy=None, cookies=self._cookies)

    def run(self):
        """
        Resolves prerequisites and runs the recorder in the selected mode.
        """
        self._setup()

        if self.mode == Mode.MANUAL:
            return self.manual_mode()

        elif self.mode == Mode.AUTOMATIC:
            self.automatic_mode()

        elif self.mode == Mode.FOLLOWERS:
            self.followers_mode()

    def manual_mode(self) -> RecordingResult | None:
        if not self.tiktok.is_room_alive(self.room_id):
            raise UserLiveError(f"@{self.user}: {TikTokError.USER_NOT_CURRENTLY_LIVE}")

        return self.start_recording(self.user, self.room_id)

    def automatic_mode(self):
        while not self._is_stopped and not self._stop_event.is_set():
            try:
                self.room_id = self.tiktok.get_room_id_from_user(self.user)
                self.manual_mode()

            except (UserLiveError, LiveNotFound) as ex:
                logger.info(ex)
                logger.info(
                    f"Waiting {self.automatic_interval} minutes before recheck\n"
                )
                time.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except (ConnectionError, RequestException, HTTPException):
                logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

    def followers_mode(self):
        active_recordings = {}  # follower -> Thread

        while not self._is_stopped and not self._stop_event.is_set():
            try:
                followers = self.tiktok.get_followers_list(self.sec_uid)

                for follower in followers:
                    if follower in active_recordings:
                        if not active_recordings[follower].is_alive():
                            logger.info(f"Recording of @{follower} finished.")
                            del active_recordings[follower]
                        else:
                            continue

                    try:
                        room_id = self.tiktok.get_room_id_from_user(follower)

                        if not room_id or not self.tiktok.is_room_alive(room_id):
                            continue

                        logger.info(f"@{follower} is live. Starting recording...")

                        thread = Thread(
                            target=self.start_recording,
                            args=(follower, room_id),
                            daemon=True,
                        )
                        thread.start()
                        active_recordings[follower] = thread

                        time.sleep(2.5)

                    except TikTokRecorderError as e:
                        logger.error(f"Error while processing @{follower}: {e}")
                        continue

                    except Exception as e:
                        logger.error(
                            f"Unexpected error processing @{follower}: {e}",
                            exc_info=True,
                        )
                        continue

                print()
                logger.info(
                    f"Waiting {self.automatic_interval} minutes for the next check..."
                )
                time.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except (UserLiveError, LiveNotFound) as ex:
                logger.info(ex)
                logger.info(
                    f"Waiting {self.automatic_interval} minutes before recheck\n"
                )
                time.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except (ConnectionError, RequestException, HTTPException):
                logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

    def _build_output_path(self, user: str) -> str:
        filename = (
            f"TK_{user}_{time.strftime('%Y.%m.%d_%H-%M-%S', time.localtime())}_flv.mp4"
        )
        if self.output:
            out_dir = Path(self.output)
            out_dir.mkdir(parents=True, exist_ok=True)
            return str(out_dir / filename)
        return filename

    def start_recording(
        self, user: str, room_id: str, custom_raw_path: str | None = None
    ) -> RecordingResult:
        """
        Start recording a live stream and return structured RecordingResult.
        """
        live_urls = self.tiktok.get_live_url_candidates(room_id, user=user)
        if not live_urls:
            raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

        output = custom_raw_path or self._build_output_path(user)
        Path(output).parent.mkdir(parents=True, exist_ok=True)

        started_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        start_monotonic = time.time()
        was_stopped_early = False
        bytes_written = 0
        min_stream_bytes = 4096

        for index, live_url in enumerate(live_urls, start=1):
            if self._is_stopped or self._stop_event.is_set():
                was_stopped_early = True
                break

            if self.duration:
                logger.info(
                    f"Started recording for {self.duration} seconds "
                    f"(stream {index}/{len(live_urls)})"
                )
            else:
                logger.info(f"Started recording (stream {index}/{len(live_urls)})...")

            buffer_size = 512 * 1024  # 512 KB buffer
            buffer = bytearray()
            bytes_written = 0

            logger.info("[PRESS CTRL + C ONCE TO STOP]")
            with open(output, "wb") as out_file:
                stop_recording = False
                stream_ended = False
                while not stop_recording:
                    if self._is_stopped or self._stop_event.is_set():
                        logger.info("Stop event signaled. Stopping recording.")
                        was_stopped_early = True
                        break

                    try:
                        if not self.tiktok.is_room_alive(room_id):
                            logger.info("User is no longer live. Stopping recording.")
                            break

                        start_chunk_time = time.time()
                        for chunk in self.tiktok.download_live_stream(live_url):
                            if self._is_stopped or self._stop_event.is_set():
                                was_stopped_early = True
                                stop_recording = True
                                break

                            buffer.extend(chunk)
                            bytes_written += len(chunk)
                            if len(buffer) >= buffer_size:
                                out_file.write(buffer)
                                buffer.clear()

                            elapsed_time = time.time() - start_chunk_time
                            if self.duration and elapsed_time >= self.duration:
                                stop_recording = True
                                break
                        else:
                            stream_ended = True

                        if stream_ended and bytes_written < min_stream_bytes:
                            break

                    except ConnectionError:
                        if self.mode == Mode.AUTOMATIC:
                            logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                            time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

                    except (RequestException, HTTPException) as ex:
                        logger.warning(f"Network hiccup, retrying: {ex}")
                        time.sleep(2)

                    except KeyboardInterrupt:
                        logger.info("Recording stopped by user via keyboard interrupt.")
                        was_stopped_early = True
                        stop_recording = True

                    except Exception as ex:
                        logger.error(
                            f"Unexpected error during recording: {ex}",
                            exc_info=True,
                        )
                        stop_recording = True

                    finally:
                        if buffer:
                            out_file.write(buffer)
                            buffer.clear()
                        out_file.flush()

            if bytes_written >= min_stream_bytes or was_stopped_early:
                break

            logger.warning(
                f"Stream {index}/{len(live_urls)} returned only {bytes_written} bytes. "
                "Trying another CDN/quality..."
            )
        else:
            if not was_stopped_early:
                Path(output).unlink(missing_ok=True)
                raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

        ended_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        total_duration = max(0.0, time.time() - start_monotonic)
        logger.info(f"Recording stream finished: {Path(output).resolve()}\n")

        # Convert to MP4 format
        final_mp4 = VideoManagement.convert_flv_to_mp4(
            output, self.bitrate, self.ffmpeg_path
        )

        final_path = final_mp4 if (final_mp4 and Path(final_mp4).exists()) else output
        final_size = Path(final_path).stat().st_size if Path(final_path).exists() else 0

        # Legacy Telethon upload support for CLI mode
        if self.use_telegram and final_path:
            try:
                from upload.telegram import Telegram

                Telegram().upload(final_path)
            except Exception as e:
                logger.error(f"Legacy Telegram upload failed: {e}")

        result_status = "STOPPED" if was_stopped_early else "COMPLETE"
        result = RecordingResult(
            username=user,
            room_id=room_id,
            started_at=started_iso,
            ended_at=ended_iso,
            duration_seconds=total_duration,
            raw_path=output,
            final_path=final_path,
            size_bytes=final_size,
            status=result_status,
        )
        self.last_result = result
        return result

    def check_country_blacklisted(self):
        is_blacklisted = self.tiktok.is_country_blacklisted()
        if not is_blacklisted:
            return False

        if self.room_id is None:
            raise TikTokRecorderError(TikTokError.COUNTRY_BLACKLISTED)

        if self.mode == Mode.AUTOMATIC:
            raise TikTokRecorderError(TikTokError.COUNTRY_BLACKLISTED_AUTO_MODE)

        elif self.mode == Mode.FOLLOWERS:
            raise TikTokRecorderError(TikTokError.COUNTRY_BLACKLISTED_FOLLOWERS_MODE)

        return is_blacklisted
