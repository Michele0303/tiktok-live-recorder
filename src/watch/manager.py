from __future__ import annotations

import asyncio
import datetime
import random
import re
import shutil
import threading
from pathlib import Path
from typing import Any

from config.settings import Settings
from core.tiktok_api import TikTokAPI
from core.tiktok_recorder import TikTokRecorder
from delivery.telegram import TelegramDeliveryService
from storage.database import Database
from storage.models import Recording, RecordingStatus, StorageStats, WatchStatus
from utils.custom_exceptions import LiveNotFound, UserLiveError
from utils.enums import Mode
from utils.logger_manager import logger
from utils.recorder_config import RecorderConfig
from watch.models import ActiveJob
from watch.recording_worker import RecordingWorker

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.\-]+$")


class WatchManager:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        delivery: TelegramDeliveryService,
        api: TikTokAPI | None = None,
        worker: RecordingWorker | None = None,
    ):
        self.settings = settings
        self.db = db
        self.delivery = delivery
        self.api = api or TikTokAPI(proxy=settings.tiktok_proxy, cookies=settings.cookies)
        self.worker = worker or RecordingWorker(settings, db, delivery)

        self.active_jobs: dict[str, ActiveJob] = {}
        self._lock = asyncio.Lock()
        self._is_running = False
        self._polling_task: asyncio.Task[None] | None = None
        self._retention_task: asyncio.Task[None] | None = None

    @staticmethod
    def normalize_username(username: str) -> str:
        """Strip leading @, trim whitespace, and convert to lowercase."""
        return username.strip().lower().lstrip("@")

    @staticmethod
    def validate_username_syntax(username: str) -> bool:
        """Check if username syntax matches TikTok constraints."""
        norm = WatchManager.normalize_username(username)
        if not norm or len(norm) > 64:
            return False
        return bool(USERNAME_REGEX.match(norm))

    async def start(self) -> None:
        """Start the background watch polling loop and reconcile previous crashes."""
        self._is_running = True
        reconciled = self.db.reconcile_stale_recordings()
        if reconciled > 0:
            logger.info(f"Startup: Reconciled {reconciled} stale recording entries.")

        self._polling_task = asyncio.create_task(self._polling_loop())
        if self.settings.delete_after_days > 0:
            self._retention_task = asyncio.create_task(self._retention_loop())
        logger.info("WatchManager started successfully.")

    async def stop(self) -> None:
        """Gracefully stop polling and all active recording workers."""
        logger.info("Stopping WatchManager...")
        self._is_running = False

        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
        if self._retention_task and not self._retention_task.done():
            self._retention_task.cancel()

        # Signal all active recording jobs to stop
        async with self._lock:
            for username, job in list(self.active_jobs.items()):
                logger.info(f"Signaling active recording for @{username} to stop...")
                job.stop_event.set()
                job.recorder.stop()

        # Wait for workers to finalize
        tasks = [job.task for job in self.active_jobs.values() if job.task and not job.task.done()]
        if tasks:
            logger.info(f"Waiting for {len(tasks)} recording worker(s) to finalize...")
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("WatchManager stopped cleanly.")

    async def check_live_status(self, username: str) -> tuple[bool, str | None, str | None]:
        """
        Check if a TikTok creator is currently live.
        Returns: (is_live: bool, room_id: str | None, error: str | None)
        """
        norm = self.normalize_username(username)
        try:
            room_id = await asyncio.to_thread(self.api.get_room_id_from_user, norm)
            if not room_id:
                return False, None, None

            is_alive = await asyncio.to_thread(self.api.is_room_alive, room_id)
            return is_alive, room_id, None
        except (UserLiveError, LiveNotFound) as e:
            return False, None, str(e)
        except Exception as e:
            logger.warning(f"TikTok live check failed for @{norm}: {e}")
            return False, None, str(e)

    async def watch(self, raw_username: str) -> tuple[bool, str, bool]:
        """
        Add or re-enable a creator in the watch list and immediately inspect LIVE status.
        Returns: (success: bool, user_message: str, is_live: bool)
        """
        if not self.validate_username_syntax(raw_username):
            return (
                False,
                f"❌ Invalid TikTok username: <code>{raw_username}</code>\n"
                "Usernames may only contain letters, numbers, underscores, dashes, and periods.",
                False,
            )

        username = self.normalize_username(raw_username)
        self.db.add_or_enable_watch(username)
        logger.info(f"Watch target enabled for @{username}")

        # Check if already recording
        if username in self.active_jobs:
            return (
                True,
                f"👁 Watching @{username}\n\nStatus: 🔴 LIVE (Recording currently in progress)",
                True,
            )

        # Check current live status
        is_live, room_id, err = await self.check_live_status(username)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if is_live:
            self.db.update_watch_status(
                username=username,
                status=WatchStatus.LIVE,
                last_checked_at=now_iso,
                last_live_at=now_iso,
            )
            # Start recording if within concurrency limit
            if len(self.active_jobs) < self.settings.max_concurrent_recordings:
                await self._start_recording_job(username, room_id)
                return (
                    True,
                    f"🔴 @{username} is already LIVE.\n\nRecording is starting now.",
                    True,
                )
            else:
                return (
                    True,
                    f"🔴 @{username} is LIVE, but maximum concurrent recordings "
                    f"({self.settings.max_concurrent_recordings}) are active. Monitoring will retry shortly.",
                    True,
                )
        else:
            self.db.update_watch_status(
                username=username,
                status=WatchStatus.OFFLINE,
                last_checked_at=now_iso,
                last_error=err,
            )
            return (
                True,
                f"👁 Watching @{username}\n\nStatus: Offline\nI'll automatically record their next LIVE.",
                False,
            )

    async def unwatch(self, raw_username: str) -> tuple[bool, str]:
        """Disable persistent watching for a creator."""
        if not self.validate_username_syntax(raw_username):
            return False, f"❌ Invalid TikTok username: <code>{raw_username}</code>"

        username = self.normalize_username(raw_username)
        disabled = self.db.disable_watch(username)

        if username in self.active_jobs:
            return (
                True,
                f"👁 Disrupted watch for @{username}.\n\n"
                "ℹ️ An active recording is currently running and will finish naturally. "
                f"Use <code>/stop {username}</code> if you want to abort the recording immediately.",
            )

        if disabled:
            return True, f"✅ Stopped watching @{username}."
        else:
            return False, f"ℹ️ @{username} was not in your active watch list."

    async def record_once(self, raw_username: str) -> tuple[bool, str]:
        """Trigger an immediate one-time recording without persisting to the watch list."""
        if not self.validate_username_syntax(raw_username):
            return False, f"❌ Invalid TikTok username: <code>{raw_username}</code>"

        username = self.normalize_username(raw_username)

        if username in self.active_jobs:
            return False, f"⚠️ Already recording @{username}."

        if len(self.active_jobs) >= self.settings.max_concurrent_recordings:
            return (
                False,
                f"⚠️ Concurrency limit reached ({self.settings.max_concurrent_recordings} active recordings). "
                "Wait for an active recording to finish or use /stop.",
            )

        is_live, room_id, err = await self.check_live_status(username)
        if not is_live:
            return False, f"⚪ @{username} is currently offline."

        await self._start_recording_job(username, room_id, is_one_off=True)
        return True, f"🔴 Started recording @{username}'s LIVE session."

    async def stop_recording(self, raw_username: str) -> tuple[bool, str]:
        """Gracefully terminate an active recording job."""
        if not self.validate_username_syntax(raw_username):
            return False, f"❌ Invalid TikTok username: <code>{raw_username}</code>"

        username = self.normalize_username(raw_username)

        async with self._lock:
            job = self.active_jobs.get(username)
            if not job:
                return False, f"ℹ️ No active recording found for @{username}."

            logger.info(f"Gracefully stopping recording for @{username}...")
            job.stop_event.set()
            job.recorder.stop()

        return (
            True,
            f"⏹ Stopping recording for @{username}.\n\n"
            "The partial stream is being converted to MP4 and will be uploaded shortly.",
        )

    def get_watching(self) -> list[dict[str, Any]]:
        """Return all enabled targets with live runtime statuses."""
        targets = self.db.get_all_watches(enabled_only=True)
        results = []
        for t in targets:
            status_str = "OFFLINE"
            if t.username in self.active_jobs:
                status_str = "RECORDING"
            elif t.status == WatchStatus.LIVE:
                status_str = "LIVE"

            results.append({
                "username": t.username,
                "status": status_str,
                "last_checked_at": t.last_checked_at,
                "last_live_at": t.last_live_at,
            })
        return results

    def get_status(self, raw_username: str) -> dict[str, Any] | None:
        """Return comprehensive status information for a creator."""
        if not self.validate_username_syntax(raw_username):
            return None

        username = self.normalize_username(raw_username)
        target = self.db.get_watch_target(username)
        active_job = self.active_jobs.get(username)

        return {
            "username": username,
            "is_watched": target.enabled if target else False,
            "status": "RECORDING" if active_job else (target.status.value if target else "NOT_WATCHED"),
            "last_checked_at": target.last_checked_at if target else None,
            "last_live_at": target.last_live_at if target else None,
            "active_recording_started_at": active_job.started_at if active_job else None,
            "last_error": target.last_error if target else None,
        }

    def get_latest(self, raw_username: str) -> Recording | None:
        """Fetch the latest recording record for a user."""
        if not self.validate_username_syntax(raw_username):
            return None
        username = self.normalize_username(raw_username)
        return self.db.get_latest_recording(username)

    def get_recordings(self, raw_username: str, limit: int = 10) -> list[Recording]:
        """Fetch recent recordings for a user."""
        if not self.validate_username_syntax(raw_username):
            return []
        username = self.normalize_username(raw_username)
        return self.db.get_recordings_for_user(username, limit=limit)

    def get_storage_summary(self) -> StorageStats:
        """Fetch storage metrics."""
        return self.db.get_storage_stats(
            recording_dir=self.settings.recording_path,
            retention_days=self.settings.delete_after_days,
        )

    async def _start_recording_job(
        self, username: str, room_id: str | None, is_one_off: bool = False
    ) -> ActiveJob:
        """Initialize and spawn an active recording job."""
        started_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        recording_id = self.db.create_recording(
            username=username,
            room_id=room_id,
            started_at=started_iso,
            status=RecordingStatus.STARTING,
        )

        stop_event = threading.Event()
        config = RecorderConfig(
            mode=Mode.MANUAL,
            user=username,
            room_id=room_id,
            ffmpeg_path=self.settings.ffmpeg_path,
            proxy=self.settings.tiktok_proxy,
            cookies=self.settings.cookies,
        )
        recorder = TikTokRecorder(config, stop_event=stop_event)

        job = ActiveJob(
            username=username,
            room_id=room_id,
            recording_id=recording_id,
            recorder=recorder,
            stop_event=stop_event,
            started_at=started_iso,
            is_one_off=is_one_off,
        )

        job.task = asyncio.create_task(
            self._job_lifecycle_wrapper(job)
        )

        async with self._lock:
            self.active_jobs[username] = job

        return job

    async def _job_lifecycle_wrapper(self, job: ActiveJob) -> None:
        """Run worker and remove job from active dict upon completion."""
        try:
            await self.worker.execute_recording_job(
                username=job.username,
                room_id=job.room_id,
                recording_id=job.recording_id,
                stop_event=job.stop_event,
                recorder=job.recorder,
            )
        except Exception as e:
            logger.error(f"Uncaught error in recording worker for @{job.username}: {e}", exc_info=True)
        finally:
            async with self._lock:
                self.active_jobs.pop(job.username, None)
            logger.info(f"Active job cleaned up for @{job.username}")

    async def _polling_loop(self) -> None:
        """Centralized async polling loop for monitored TikTok creators."""
        logger.info(
            f"Watch polling loop started (interval: {self.settings.watch_interval_seconds}s)"
        )
        while self._is_running:
            try:
                targets = self.db.get_all_watches(enabled_only=True)
                for target in targets:
                    if not self._is_running:
                        break

                    username = target.username
                    # Skip targets currently being recorded
                    if username in self.active_jobs:
                        continue

                    # Check global concurrency limit
                    if len(self.active_jobs) >= self.settings.max_concurrent_recordings:
                        logger.debug("Max concurrent recordings reached; skipping checks this cycle.")
                        break

                    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    is_live, room_id, err = await self.check_live_status(username)

                    if is_live:
                        logger.info(f"🔴 Detected LIVE for watched user @{username}! Starting recording...")
                        self.db.update_watch_status(
                            username=username,
                            status=WatchStatus.LIVE,
                            last_checked_at=now_iso,
                            last_live_at=now_iso,
                        )
                        await self._start_recording_job(username, room_id)
                    else:
                        self.db.update_watch_status(
                            username=username,
                            status=WatchStatus.OFFLINE,
                            last_checked_at=now_iso,
                            last_error=err,
                        )

                    # Slight jitter between creators to avoid burst traffic
                    await asyncio.sleep(random.uniform(1.0, 3.0))

            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                logger.error(f"Error in watch polling loop: {loop_err}", exc_info=True)

            try:
                await asyncio.sleep(self.settings.watch_interval_seconds)
            except asyncio.CancelledError:
                break

    async def _retention_loop(self) -> None:
        """Periodic cleanup task for recordings older than DELETE_AFTER_DAYS."""
        logger.info(f"Retention manager active (retention: {self.settings.delete_after_days} days)")
        while self._is_running:
            try:
                expired = self.db.get_expired_recordings(self.settings.delete_after_days)
                for rec in expired:
                    if not rec.path:
                        continue
                    p = Path(rec.path)
                    if p.exists():
                        logger.info(f"Retention policy: Deleting expired recording {rec.id} at {p}")
                        try:
                            if p.is_dir():
                                shutil.rmtree(p)
                            else:
                                p.unlink(missing_ok=True)
                            self.db.update_recording(
                                recording_id=rec.id,
                                error=f"Cleaned up by {self.settings.delete_after_days}-day retention policy",
                            )
                        except Exception as e:
                            logger.error(f"Failed to delete expired recording at {p}: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retention loop: {e}")

            try:
                # Check retention once every 6 hours
                await asyncio.sleep(6 * 3600)
            except asyncio.CancelledError:
                break
