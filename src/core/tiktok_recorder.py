import os
import time
from http.client import HTTPException
from threading import Thread


from requests import RequestException

from core.tiktok_api import TikTokAPI

from utils.video_management import VideoManagement
from upload.telegram import Telegram
from utils.custom_exceptions import LiveNotFound, UserLiveError, TikTokRecorderError
from utils.enums import Mode, Error, TimeOut, TikTokError


class TikTokRecorder:
    def __init__(
        self,
        url,
        user,
        room_id,
        mode,
        automatic_interval,
        cookies,
        proxy,
        output,
        duration,
        use_telegram,
        ffmpeg_encode,
        app_logger,  # New argument
        keep_flv,
    ):
        self.logger = app_logger  # Store the logger
        self.keep_flv = keep_flv
        # Setup TikTok API client
        self.tiktok = TikTokAPI(proxy=proxy, cookies=cookies)

        # TikTok Data
        self.url = url
        self.user = user
        self.room_id = room_id

        # Tool Settings
        self.mode = mode
        self.automatic_interval = automatic_interval
        self.duration = duration
        self.output = output
        self.ffmpeg_encode = ffmpeg_encode

        # Upload Settings
        self.use_telegram = use_telegram

        # Check if the user's country is blacklisted
        self.check_country_blacklisted()

        # Retrieve sec_uid if the mode is FOLLOWERS
        if self.mode == Mode.FOLLOWERS:
            self.sec_uid = self.tiktok.get_sec_uid()
            if self.sec_uid is None:
                raise TikTokRecorderError("Failed to retrieve sec_uid.")

            self.logger.info("Followers mode activated\n")
        else:
            # Get live information based on the provided user data
            if self.url:
                self.user, self.room_id = self.tiktok.get_room_and_user_from_url(
                    self.url
                )

            if not self.user:
                self.user = self.tiktok.get_user_from_room_id(self.room_id)

            if not self.room_id:
                self.room_id = self.tiktok.get_room_id_from_user(self.user)

            self.logger.info(
                f"USERNAME: {self.user}" + ("\n" if not self.room_id else ""))
            if self.room_id:
                self.logger.info(
                    f"ROOM_ID:  {self.room_id}"
                    + ("\n" if not self.tiktok.is_room_alive(self.room_id) else "")
                )

        # If proxy is provided, set up the HTTP client without the proxy
        if proxy:
            self.tiktok = TikTokAPI(proxy=None, cookies=cookies)

    def run(self) -> bool:  # Added return type annotation
        """
        runs the program in the selected mode.

        Returns:
            bool: True if the program should exit entirely (e.g., user interruption), False otherwise.
        """
        if self.mode == Mode.MANUAL:
            return self.manual_mode()

        elif self.mode == Mode.AUTOMATIC:
            return self.automatic_mode()

        elif self.mode == Mode.FOLLOWERS:
            return self.followers_mode()

        return False  # Should not be reached

    def manual_mode(self) -> bool:  # Added return type annotation
        if not self.tiktok.is_room_alive(self.room_id):
            raise UserLiveError(
                f"@{self.user}: {TikTokError.USER_NOT_CURRENTLY_LIVE}")

        # Return the stopped_by_user status
        return self.start_recording(self.user, self.room_id)

    def automatic_mode(self) -> bool:  # Added return type annotation
        while True:
            try:
                self.room_id = self.tiktok.get_room_id_from_user(self.user)
                if not self.room_id:
                    raise UserLiveError(TikTokError.ROOM_ID_ERROR)

                if self.tiktok.is_room_alive(self.room_id):
                    stopped_by_user = self.start_recording(
                        self.user, self.room_id)
                    if stopped_by_user:
                        self.logger.info(
                            "Stopping automatic mode (User Request).")
                        return True  # Signal main to exit
                else:
                    raise UserLiveError(
                        f"@{self.user}: {TikTokError.USER_NOT_CURRENTLY_LIVE}")

            except UserLiveError as ex:
                self.logger.info(ex)
                self.logger.info(f"Waiting {self.automatic_interval} minutes before recheck\n")
                time.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except LiveNotFound as ex:
                self.logger.error(f"Live not found: {ex}")
                self.logger.info(f"Waiting {self.automatic_interval} minutes before recheck\n")
                time.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except ConnectionError:
                self.logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

            except KeyboardInterrupt:
                self.logger.info(
                    "Stopping automatic mode (KeyboardInterrupt).")
                return True  # Signal main to exit

            except Exception as ex:
                self.logger.error(f"Unexpected error: {ex}\n")

        # Should not be reached (loop is infinite unless broken/returned)
        return False

    def followers_mode(self) -> bool:  # Added return type annotation
        active_recordings = {}  # follower -> Process

        while True:
            try:
                followers = self.tiktok.get_followers_list(self.sec_uid)
                # ... (rest of followers logic, simplistic change here might be tricky due to threading)
                # For followers mode, the threading logic makes returning values harder.
                # However, KeyboardInterrupt in the main loop should catch it.

                for follower in followers:
                    # ... existing logic ...
                    if follower in active_recordings:
                        if not active_recordings[follower].is_alive():
                            self.logger.info(
                                f"Recording of @{follower} finished.")
                            del active_recordings[follower]
                        else:
                            continue

                    try:
                        room_id = self.tiktok.get_room_id_from_user(follower)

                        if not room_id or not self.tiktok.is_room_alive(
                                room_id):
                            # self.logger.info(f"@{follower} is not live. Skipping...")
                            continue

                        self.logger.info(
                            f"@{follower} is live. Starting recording...")

                        thread = Thread(
                            target=self.start_recording,
                            # start_recording is now returning a value, which
                            # will be lost in a thread.
                            args=(follower, room_id),
                            # The main thread needs to handle its own
                            # KeyboardInterrupt.
                            daemon=True,
                        )
                        thread.start()
                        active_recordings[follower] = thread

                        time.sleep(2.5)

                    except Exception as e:
                        self.logger.error(
                            f"Error while processing @{follower}: {e}")
                        continue

                print()
                delay = self.automatic_interval * TimeOut.ONE_MINUTE
                self.logger.info(
                    f"Waiting {delay} minutes for the next check...")
                time.sleep(delay)

            except UserLiveError as ex:
                self.logger.info(ex)
                self.logger.info(f"Waiting {self.automatic_interval} minutes before recheck\n")
                time.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except ConnectionError:
                self.logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

            except KeyboardInterrupt:
                self.logger.info(
                    "Stopping followers mode (KeyboardInterrupt).")
                return True  # Signal main to exit

            except Exception as ex:
                self.logger.error(f"Unexpected error: {ex}\n")

        # Should not be reached (loop is infinite unless broken/returned)
        return False

    def start_recording(self, user, room_id):
        """
        Start recording live
        """
        live_url = self.tiktok.get_live_url(room_id)
        if not live_url:
            raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

        current_date = time.strftime("%Y.%m.%d_%H-%M-%S", time.localtime())

        if isinstance(self.output, str) and self.output != "":
            if not (self.output.endswith("/") or self.output.endswith("\\")):
                if os.name == "nt":
                    self.output = self.output + "\\"
                else:
                    self.output = self.output + "/"

        output = f"{self.output if self.output else ''}TK_{user}_{current_date}_flv.mp4"

        if self.duration:
            self.logger.info(f"Started recording for {self.duration} seconds ")
        else:
            self.logger.info("Started recording...")

        buffer_size = 512 * 1024  # 512 KB buffer
        buffer = bytearray()

        self.logger.info("[PRESS CTRL + C TO STOP]")

        # Initialize stopped_by_user to False by default
        stopped_by_user = False

        with open(output, "wb") as out_file:
            stop_recording = False
            self.logger.debug("Starting video download loop...")
            while not stop_recording:
                try:
                    if not self.tiktok.is_room_alive(room_id):
                        self.logger.info(
                            "User is no longer live. Stopping recording.")
                        break

                    start_time = time.time()
                    for chunk in self.tiktok.download_live_stream(live_url):
                        buffer.extend(chunk)
                        if len(buffer) >= buffer_size:
                            self.logger.debug(f"Flushing buffer to disk: {len(buffer)} bytes")
                            out_file.write(buffer)
                            buffer.clear()

                        elapsed_time = time.time() - start_time
                        if self.duration and elapsed_time >= self.duration:
                            stop_recording = True
                            break

                    # If download_live_stream generator ends (e.g. stream cut),
                    # break loop
                    if not stop_recording:
                        self.logger.debug("Stream generator ended.")
                        break

                except ConnectionError:
                    if self.mode == Mode.AUTOMATIC:
                        self.logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                        time.sleep(
                            TimeOut.CONNECTION_CLOSED *
                            TimeOut.ONE_MINUTE)

                except (RequestException, HTTPException):
                    time.sleep(2)

                except KeyboardInterrupt:
                    self.logger.info("Recording stopped by user.")
                    stop_recording = True
                    stopped_by_user = True

                except Exception as ex:
                    self.logger.error(
                        f"Unexpected error: {ex}\n", exc_info=True)
                    stop_recording = True

                finally:
                    if buffer:
                        out_file.write(buffer)
                        buffer.clear()
                    out_file.flush()

        self.logger.info(f"Recording finished: {output}\n")

        # Verify the integrity of the raw recording immediately
        if not VideoManagement.validate_video(output):
            self.logger.error(
                f"WARNING: The recorded file '{output}' appears to be corrupt or invalid.")

        final_file = output

        if stopped_by_user:
            # Interactive Conversion Prompt (Only if stopped manually)
            print()

            # Ask about re-encoding strategy ONLY if not already enforced by
            # flag
            if self.ffmpeg_encode:
                should_encode = True
                self.logger.info(
                    "Re-encoding enforced by -ffmpeg-encode flag.")
            else:
                encode_choice = ""
                while encode_choice not in ["y", "yes", "n", "no"]:
                    encode_choice = input(
                        "Do you want to re-encode the video (slower, fixes glitches)? [y/n]: ").lower()
                should_encode = encode_choice in ["y", "yes"]

            converted_path = VideoManagement.convert_flv_to_mp4(
                output, should_encode)

            if converted_path:
                final_file = converted_path

                # Interactive Deletion Prompt ONLY if not enforced by
                # --keep-flv
                if self.keep_flv:
                    self.logger.info(
                        f"Original file '{output}' kept (per --keep-flv flag).")
                else:
                    delete_choice = ""
                    while delete_choice not in ["y", "yes", "n", "no"]:
                        delete_choice = input(
                            "Do you want to delete the original file? [y/n]: ").lower()

                    if delete_choice in ["y", "yes"]:
                        try:
                            os.remove(output)
                            self.logger.info(
                                f"Original file deleted: {output}")
                        except OSError as e:
                            self.logger.error(
                                f"Error deleting file {output}: {e}")
        else:
            # Automatic Conversion (Stream ended naturally/Automatically)
            # Non-blocking conversion
            self.logger.info(
                "Stream ended. Performing automatic conversion...")
            converted_path = VideoManagement.convert_flv_to_mp4(
                output, self.ffmpeg_encode)
            if converted_path:
                final_file = converted_path
                # Automatically delete the original FLV file if conversion was successful and validated
                # AND if keep_flv is False
                if not self.keep_flv:
                    try:
                        os.remove(output)
                        self.logger.info(
                            f"Original FLV file '{output}' deleted automatically after successful conversion.")
                    except OSError as e:
                        self.logger.error(
                            f"Error deleting original FLV file '{output}': {e}")
                else:
                    self.logger.info(
                        f"Original FLV file '{output}' kept (per --keep-flv flag).")

        if self.use_telegram:
            Telegram().upload(final_file)

        return stopped_by_user

    def check_country_blacklisted(self):
        is_blacklisted = self.tiktok.is_country_blacklisted()
        if not is_blacklisted:
            return False

        if self.room_id is None:
            raise TikTokRecorderError(TikTokError.COUNTRY_BLACKLISTED)

        if self.mode == Mode.AUTOMATIC:
            raise TikTokRecorderError(
                TikTokError.COUNTRY_BLACKLISTED_AUTO_MODE)

        elif self.mode == Mode.FOLLOWERS:
            raise TikTokRecorderError(
                TikTokError.COUNTRY_BLACKLISTED_FOLLOWERS_MODE)

        return is_blacklisted
