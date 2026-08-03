import re
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

# Characters that are unsafe/invalid in filenames on common filesystems
# (Windows reserves <>:"/\|?* and control chars; POSIX just needs / and NUL,
# but we sanitize for the superset so recordings are portable).
_FILENAME_UNSAFE_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _sanitize_filename_part(value: str) -> str:
    """Strip characters that are unsafe in filenames on common OSes."""
    cleaned = _FILENAME_UNSAFE_RE.sub("_", str(value)).strip(" .")
    return cleaned or "unknown"


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
        self.use_telegram = config.use_telegram
        self.extract_audio = config.extract_audio

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

        # Note: TikTokAPI already keeps the proxy on its metadata/API client
        # (http_client) while the stream-download client (_http_client_stream)
        # stays direct. We deliberately do NOT swap self.tiktok for a fresh,
        # proxy-less instance here: doing so used to also strip the proxy from
        # every later metadata call (room checks, URL resolution, automatic
        # mode rechecks), which breaks recording in regions where the proxy
        # is required to reach TikTok at all.

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
        while True:
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
        safe_user = _sanitize_filename_part(user)
        filename = f"TK_{safe_user}_{time.strftime('%Y.%m.%d_%H-%M-%S', time.localtime())}_flv.mp4"
        # Base folder is whatever -output points to (defaulting to a local
        # "Downloads" folder when it isn't set), with one subfolder per
        # profile so each user's video + audio files stay together.
        base_dir = Path(self.output) if self.output else Path("Downloads")
        user_dir = base_dir / safe_user
        user_dir.mkdir(parents=True, exist_ok=True)
        return str(user_dir / filename)

    def start_recording(self, user, room_id):
        """
        Start recording live
        """
        live_urls = self.tiktok.get_live_url_candidates(room_id, user=user)
        if not live_urls:
            raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

        output = self._build_output_path(user)

        # Computed once, before any attempt/reconnect/CDN-switch, so
        # `-duration` bounds the total wall-clock recording time rather than
        # resetting every time the stream reconnects.
        recording_deadline = time.time() + self.duration if self.duration else None

        min_stream_bytes = 4096
        for index, live_url in enumerate(live_urls, start=1):
            if recording_deadline and time.time() >= recording_deadline:
                logger.info("Requested duration already reached; stopping.")
                break

            if self.duration:
                remaining = max(0, int(recording_deadline - time.time()))
                logger.info(
                    f"Started recording for up to {remaining} more second(s) "
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
                    try:
                        if not self.tiktok.is_room_alive(room_id):
                            logger.info("User is no longer live. Stopping recording.")
                            break

                        if recording_deadline and time.time() >= recording_deadline:
                            stop_recording = True
                            break

                        for chunk in self.tiktok.download_live_stream(live_url):
                            buffer.extend(chunk)
                            bytes_written += len(chunk)
                            if len(buffer) >= buffer_size:
                                out_file.write(buffer)
                                buffer.clear()

                            if recording_deadline and time.time() >= recording_deadline:
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
                        logger.info("Recording stopped by user.")
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
        final_path = VideoManagement.convert_flv_to_mp4(
            output, self.bitrate, self.ffmpeg_path
        )

        if self.extract_audio and final_path:
            VideoManagement.extract_audio(final_path, self.ffmpeg_path)

        if self.use_telegram:
            if not final_path:
                logger.warning(
                    "Skipping Telegram upload: MP4 conversion did not complete."
                )
            else:
                try:
                    from upload.telegram import Telegram

                    Telegram().upload(final_path)
                except Exception as ex:
                    logger.error(f"Telegram upload failed: {ex}", exc_info=True)

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
