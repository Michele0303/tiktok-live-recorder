import time
from http.client import HTTPException
from pathlib import Path
from threading import Thread

from requests import RequestException

from core.tiktok_api import TikTokAPI
from utils.logger_manager import logger
from utils.recorder_config import RecorderConfig
from utils.video_management import VideoManagement
from utils.custom_exceptions import LiveNotFound, UserLiveError, TikTokRecorderError
from utils.enums import Mode, Error, TimeOut, TikTokError


class TikTokRecorder:
    def __init__(self, config: RecorderConfig):
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
        self.exit_on_interrupt = config.exit_on_interrupt
        self.shutdown_event = config.shutdown_event
        self.use_telegram = config.use_telegram
        self._proxy = config.proxy
        self._cookies = config.cookies
        self._stop_requested = False

    def _shutdown_requested(self):
        return self.shutdown_event is not None and self.shutdown_event.is_set()

    def _wait_or_shutdown(self, timeout):
        if self.shutdown_event is not None:
            return self.shutdown_event.wait(timeout)

        time.sleep(timeout)
        return False

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

        If the mode is MANUAL, it checks if the user is currently live and
        if so, starts recording.

        If the mode is AUTOMATIC, it continuously checks if the user is live
        and if not, waits for the specified timeout before rechecking.
        If the user is live, it starts recording.

        if the mode is FOLLOWERS, it continuously checks the followers of
        the authenticated user. If any follower is live, it starts recording
        their live stream in a separate process.
        """
        self._setup()

        if self.mode == Mode.MANUAL:
            self.manual_mode()

        elif self.mode == Mode.AUTOMATIC:
            self.automatic_mode()

        elif self.mode == Mode.FOLLOWERS:
            self.followers_mode()

    def manual_mode(self):
        if not self.tiktok.is_room_alive(self.room_id):
            raise UserLiveError(f"@{self.user}: {TikTokError.USER_NOT_CURRENTLY_LIVE}")

        self.start_recording(self.user, self.room_id)

    def automatic_mode(self):
        while not self._shutdown_requested():
            try:
                try:
                    self.room_id = self.tiktok.get_room_id_from_user(self.user)
                    self.manual_mode()
                    if self._stop_requested or self._shutdown_requested():
                        return

                except (UserLiveError, LiveNotFound) as ex:
                    logger.info(ex)
                    logger.info(
                        f"Waiting {self.automatic_interval} minutes before recheck\n"
                    )
                    if self._wait_or_shutdown(
                        self.automatic_interval * TimeOut.ONE_MINUTE
                    ):
                        return

                except (ConnectionError, RequestException, HTTPException):
                    logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                    if self._wait_or_shutdown(
                        TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE
                    ):
                        return

            except KeyboardInterrupt:
                logger.info("Recording stopped by user.")
                self._stop_requested = True
                return

    def followers_mode(self):
        active_recordings = {}  # follower -> Thread

        while True:
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
            return str(Path(self.output) / filename)
        return filename

    def start_recording(self, user, room_id):
        """
        Start recording live
        """
        live_urls = self.tiktok.get_live_url_candidates(room_id, user=user)
        if not live_urls:
            raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

        output = self._build_output_path(user)

        min_stream_bytes = 4096
        recording_started_at = time.monotonic()
        interrupted_by_user = False
        duration_expired = False
        for index, live_url in enumerate(live_urls, start=1):
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
                try:
                    while not stop_recording:
                        try:
                            if self._shutdown_requested():
                                stop_recording = True
                                break

                            if (
                                self.duration
                                and time.monotonic() - recording_started_at
                                >= self.duration
                            ):
                                duration_expired = True
                                stop_recording = True
                                break

                            if not self.tiktok.is_room_alive(room_id):
                                logger.info(
                                    "User is no longer live. Stopping recording."
                                )
                                break

                            for chunk in self.tiktok.download_live_stream(live_url):
                                if self._shutdown_requested():
                                    stop_recording = True
                                    break

                                buffer.extend(chunk)
                                bytes_written += len(chunk)
                                if len(buffer) >= buffer_size:
                                    out_file.write(buffer)
                                    buffer.clear()

                                elapsed_time = time.monotonic() - recording_started_at
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
                                stop_recording = self._wait_or_shutdown(
                                    TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE
                                )
                            else:
                                logger.warning(
                                    "Connection closed. Retrying in 2 seconds."
                                )
                                stop_recording = self._wait_or_shutdown(2)

                        except (RequestException, HTTPException) as ex:
                            logger.warning(f"Network hiccup, retrying: {ex}")
                            stop_recording = self._wait_or_shutdown(2)

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
                except KeyboardInterrupt:
                    logger.info("Recording stopped by user.")
                    interrupted_by_user = True
                    stop_recording = True

            if interrupted_by_user:
                self._stop_requested = (
                    self.exit_on_interrupt or self._shutdown_requested()
                )
                if bytes_written < min_stream_bytes:
                    Path(output).unlink(missing_ok=True)
                else:
                    logger.info(f"Recording finished: {Path(output).resolve()}\n")
                    VideoManagement.convert_flv_to_mp4(
                        output, self.bitrate, self.ffmpeg_path
                    )
                return

            if self._shutdown_requested():
                if bytes_written < min_stream_bytes:
                    Path(output).unlink(missing_ok=True)
                    return
                break

            if duration_expired and bytes_written < min_stream_bytes:
                Path(output).unlink(missing_ok=True)
                logger.info(
                    "Recording duration elapsed before stream data was received."
                )
                return

            if bytes_written >= min_stream_bytes:
                break

            logger.warning(
                f"Stream {index}/{len(live_urls)} returned only {bytes_written} bytes. "
                "Trying another CDN/quality..."
            )
        else:
            Path(output).unlink(missing_ok=True)
            raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

        logger.info(f"Recording finished: {Path(output).resolve()}\n")
        VideoManagement.convert_flv_to_mp4(output, self.bitrate, self.ffmpeg_path)

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
