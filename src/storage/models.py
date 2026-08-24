from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WatchStatus(str, Enum):
    OFFLINE = "OFFLINE"
    LIVE = "LIVE"
    RECORDING = "RECORDING"
    ERROR = "ERROR"


class RecordingStatus(str, Enum):
    WAITING = "WAITING"
    STARTING = "STARTING"
    RECORDING = "RECORDING"
    RECONNECTING = "RECONNECTING"
    PROCESSING = "PROCESSING"
    UPLOADING = "UPLOADING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


@dataclass
class WatchTarget:
    id: int | None
    username: str
    enabled: bool
    created_at: str
    updated_at: str
    last_checked_at: str | None = None
    last_live_at: str | None = None
    status: WatchStatus = WatchStatus.OFFLINE
    last_error: str | None = None


@dataclass
class Recording:
    id: int | None
    username: str
    room_id: str | None
    started_at: str
    ended_at: str | None
    duration_seconds: float | None
    status: RecordingStatus
    path: str | None
    size_bytes: int | None
    telegram_message_id: str | None
    error: str | None
    created_at: str


@dataclass
class StorageStats:
    total_recordings: int
    total_size_bytes: int
    recordings_path: str
    disk_total_bytes: int
    disk_used_bytes: int
    disk_free_bytes: int
    retention_days: int
