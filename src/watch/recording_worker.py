from __future__ import annotations

import asyncio
import datetime
import json
import threading
from pathlib import Path

from config.settings import Settings
from core.tiktok_recorder import RecordingResult, TikTokRecorder
from delivery.telegram import TelegramDeliveryService
from storage.database import Database
from storage.models import RecordingStatus, WatchStatus
from utils.enums import Mode
from utils.logger_manager import logger
from utils.recorder_config import RecorderConfig
from utils.video_management import VideoManagement


class RecordingWorker:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        delivery: TelegramDeliveryService,
    ):
        self.settings = settings
        self.db = db
        self.delivery = delivery

    def _prepare_storage_layout(self, username: str) -> tuple[Path, str]:
        """
        Create a partitioned storage directory:
        /data/recordings/<username>/<YYYY>/<MM>/<DD>/<username>_<YYYY-MM-DD_HH-MM-SS>/
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        year_str = now.strftime("%Y")
        month_str = now.strftime("%m")
        day_str = now.strftime("%d")
        ts_str = now.strftime("%Y-%m-%d_%H-%M-%S")

        base_rec_dir = Path(self.settings.recording_path)
        job_dir = base_rec_dir / username / year_str / month_str / day_str / f"{username}_{ts_str}"
        job_dir.mkdir(parents=True, exist_ok=True)

        raw_flv_path = str(job_dir / f"{username}_{ts_str}_flv.mp4")
        return job_dir, raw_flv_path

    async def execute_recording_job(
        self,
        username: str,
        room_id: str | None,
        recording_id: int,
        stop_event: threading.Event,
        recorder: TikTokRecorder | None = None,
    ) -> RecordingResult:
        """
        Execute full recording lifecycle asynchronously:
        Record -> Remux -> Metadata -> Segment -> Deliver -> Update DB.
        """
        job_dir, raw_flv_path = self._prepare_storage_layout(username)
        started_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if recorder is None:
            config = RecorderConfig(
                mode=Mode.MANUAL,
                user=username,
                room_id=room_id,
                bitrate=None,
                ffmpeg_path=self.settings.ffmpeg_path,
                proxy=self.settings.tiktok_proxy,
                cookies=self.settings.cookies,
                output=str(job_dir),
            )
            recorder = TikTokRecorder(config, stop_event=stop_event)

        # 1. Update DB to RECORDING
        self.db.update_recording(
            recording_id=recording_id,
            status=RecordingStatus.RECORDING,
            path=str(job_dir),
        )
        self.db.update_watch_status(
            username=username,
            status=WatchStatus.RECORDING,
            last_live_at=started_iso,
        )

        logger.info(f"Worker started recording stream for @{username} into {job_dir}")

        result: RecordingResult
        try:
            # Run blocking recording loop in a separate thread
            result = await asyncio.to_thread(
                recorder.start_recording,
                user=username,
                room_id=room_id,
                custom_raw_path=raw_flv_path,
            )
        except Exception as e:
            logger.error(f"Recording execution failed for @{username}: {e}", exc_info=True)
            ended_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.db.update_recording(
                recording_id=recording_id,
                status=RecordingStatus.FAILED,
                ended_at=ended_iso,
                error=str(e),
            )
            self.db.update_watch_status(
                username=username,
                status=WatchStatus.OFFLINE,
                last_error=str(e),
            )
            return RecordingResult(
                username=username,
                room_id=room_id,
                started_at=started_iso,
                ended_at=ended_iso,
                duration_seconds=0.0,
                raw_path=raw_flv_path,
                final_path=None,
                size_bytes=0,
                status="FAILED",
                error=str(e),
            )

        # 2. Mark PROCESSING
        self.db.update_recording(
            recording_id=recording_id,
            status=RecordingStatus.PROCESSING,
            duration_seconds=result.duration_seconds,
            size_bytes=result.size_bytes,
            ended_at=result.ended_at,
        )

        # 3. Write metadata.json
        metadata = {
            "recording_id": recording_id,
            "username": username,
            "room_id": room_id,
            "started_at": result.started_at,
            "ended_at": result.ended_at,
            "duration_seconds": result.duration_seconds,
            "size_bytes": result.size_bytes,
            "status": result.status,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        metadata_path = job_dir / "metadata.json"
        try:
            with open(metadata_path, "w", encoding="utf-8") as mf:
                json.dump(metadata, mf, indent=2)
        except Exception as meta_err:
            logger.warning(f"Failed to write metadata.json for @{username}: {meta_err}")

        # 4. Check for video segmentation if MP4 exists and exceeds max part size
        video_parts: list[str] = []
        if result.final_path and Path(result.final_path).is_file():
            try:
                video_parts = await asyncio.to_thread(
                    VideoManagement.segment_video,
                    file_path=result.final_path,
                    max_part_bytes=self.settings.max_recording_part_bytes,
                    ffmpeg_path=self.settings.ffmpeg_path,
                )
            except Exception as seg_err:
                logger.error(f"Segmentation failed for {result.final_path}: {seg_err}")
                video_parts = [result.final_path]
        elif result.raw_path and Path(result.raw_path).is_file():
            video_parts = [result.raw_path]

        # 5. Mark UPLOADING and deliver to Telegram
        final_status = (
            RecordingStatus.STOPPED
            if result.status == "STOPPED"
            else RecordingStatus.COMPLETE
        )
        telegram_msg_ids: list[int] = []

        if video_parts:
            self.db.update_recording(
                recording_id=recording_id,
                status=RecordingStatus.UPLOADING,
            )
            try:
                telegram_msg_ids = await self.delivery.deliver_recording(
                    username=username,
                    duration_seconds=result.duration_seconds,
                    total_size_bytes=result.size_bytes,
                    video_paths=video_parts,
                )
            except Exception as del_err:
                logger.error(
                    f"Delivery error for @{username}: {del_err}. Local file safely preserved at {job_dir}"
                )

        msg_ids_str = ",".join(str(m) for m in telegram_msg_ids) if telegram_msg_ids else None

        # 6. Finalize DB entry
        self.db.update_recording(
            recording_id=recording_id,
            status=final_status,
            path=str(job_dir.resolve()),
            telegram_message_id=msg_ids_str,
        )
        self.db.update_watch_status(
            username=username,
            status=WatchStatus.OFFLINE,
            last_live_at=result.started_at,
        )

        logger.info(
            f"Finished processing recording {recording_id} for @{username} (status: {final_status.value})"
        )
        return result
