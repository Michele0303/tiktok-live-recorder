from __future__ import annotations

import datetime
import shutil
import sqlite3
import threading
from pathlib import Path
from typing import Any

from storage.models import (
    Recording,
    RecordingStatus,
    StorageStats,
    WatchStatus,
    WatchTarget,
)
from utils.logger_manager import logger


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: str = "/data/watch.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False,
            isolation_level=None,  # autocommit mode
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> None:
        """Create tables and indexes idempotently."""
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS watch_targets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        last_checked_at TEXT,
                        last_live_at TEXT,
                        status TEXT NOT NULL DEFAULT 'OFFLINE',
                        last_error TEXT
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_watch_targets_username ON watch_targets(username)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_watch_targets_enabled ON watch_targets(enabled)"
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS recordings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        room_id TEXT,
                        started_at TEXT NOT NULL,
                        ended_at TEXT,
                        duration_seconds REAL,
                        status TEXT NOT NULL,
                        path TEXT,
                        size_bytes INTEGER,
                        telegram_message_id TEXT,
                        error TEXT,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_recordings_username ON recordings(username)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_recordings_status ON recordings(status)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_recordings_created_at ON recordings(created_at)"
                )
            finally:
                conn.close()

    def reconcile_stale_recordings(self) -> int:
        """Reconcile unfinalized recordings from previous application crashes."""
        now = _utc_now_iso()
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    """
                    UPDATE recordings
                    SET status = ?, ended_at = coalesce(ended_at, ?), error = ?
                    WHERE status IN (?, ?, ?, ?)
                    """,
                    (
                        RecordingStatus.STOPPED.value,
                        now,
                        "Interrupted by service restart",
                        RecordingStatus.STARTING.value,
                        RecordingStatus.RECORDING.value,
                        RecordingStatus.PROCESSING.value,
                        RecordingStatus.UPLOADING.value,
                    ),
                )
                updated_count = cursor.rowcount
                if updated_count > 0:
                    logger.warning(
                        f"Reconciled {updated_count} interrupted recording records to STOPPED."
                    )
                return updated_count
            finally:
                conn.close()

    def add_or_enable_watch(self, username: str) -> WatchTarget:
        """Add a new watch target or re-enable an existing disabled target."""
        normalized = username.strip().lower().lstrip("@")
        now = _utc_now_iso()
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO watch_targets (username, enabled, created_at, updated_at, status)
                    VALUES (?, 1, ?, ?, ?)
                    ON CONFLICT(username) DO UPDATE SET
                        enabled = 1,
                        updated_at = excluded.updated_at
                    """,
                    (normalized, now, now, WatchStatus.OFFLINE.value),
                )
                row = conn.execute(
                    "SELECT * FROM watch_targets WHERE username = ?", (normalized,)
                ).fetchone()
                return self._row_to_watch_target(row)
            finally:
                conn.close()

    def disable_watch(self, username: str) -> bool:
        """Disable watching a target."""
        normalized = username.strip().lower().lstrip("@")
        now = _utc_now_iso()
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    """
                    UPDATE watch_targets
                    SET enabled = 0, updated_at = ?
                    WHERE username = ? AND enabled = 1
                    """,
                    (now, normalized),
                )
                return cursor.rowcount > 0
            finally:
                conn.close()

    def get_watch_target(self, username: str) -> WatchTarget | None:
        """Get a watch target by username."""
        normalized = username.strip().lower().lstrip("@")
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    "SELECT * FROM watch_targets WHERE username = ?", (normalized,)
                ).fetchone()
                if not row:
                    return None
                return self._row_to_watch_target(row)
            finally:
                conn.close()

    def get_all_watches(self, enabled_only: bool = True) -> list[WatchTarget]:
        """List watch targets."""
        with self._lock:
            conn = self._get_connection()
            try:
                if enabled_only:
                    rows = conn.execute(
                        "SELECT * FROM watch_targets WHERE enabled = 1 ORDER BY username ASC"
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM watch_targets ORDER BY username ASC"
                    ).fetchall()
                return [self._row_to_watch_target(r) for r in rows]
            finally:
                conn.close()

    def update_watch_status(
        self,
        username: str,
        status: WatchStatus,
        last_checked_at: str | None = None,
        last_live_at: str | None = None,
        last_error: str | None = None,
    ) -> None:
        """Update live status and check timestamps for a target."""
        normalized = username.strip().lower().lstrip("@")
        now = _utc_now_iso()
        with self._lock:
            conn = self._get_connection()
            try:
                query = """
                    UPDATE watch_targets
                    SET status = ?,
                        updated_at = ?,
                        last_checked_at = coalesce(?, last_checked_at),
                        last_live_at = coalesce(?, last_live_at),
                        last_error = ?
                    WHERE username = ?
                """
                conn.execute(
                    query,
                    (
                        status.value,
                        now,
                        last_checked_at or now,
                        last_live_at,
                        last_error,
                        normalized,
                    ),
                )
            finally:
                conn.close()

    def create_recording(
        self,
        username: str,
        room_id: str | None,
        started_at: str,
        path: str | None = None,
        status: RecordingStatus = RecordingStatus.STARTING,
    ) -> int:
        """Create a new recording log entry."""
        normalized = username.strip().lower().lstrip("@")
        now = _utc_now_iso()
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO recordings (
                        username, room_id, started_at, status, path, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (normalized, room_id, started_at, status.value, path, now),
                )
                return int(cursor.lastrowid)
            finally:
                conn.close()

    def update_recording(
        self,
        recording_id: int,
        status: RecordingStatus | None = None,
        ended_at: str | None = None,
        duration_seconds: float | None = None,
        size_bytes: int | None = None,
        path: str | None = None,
        telegram_message_id: str | None = None,
        error: str | None = None,
    ) -> None:
        """Update recording status and metadata."""
        fields: list[str] = []
        values: list[Any] = []

        if status is not None:
            fields.append("status = ?")
            values.append(status.value)
        if ended_at is not None:
            fields.append("ended_at = ?")
            values.append(ended_at)
        if duration_seconds is not None:
            fields.append("duration_seconds = ?")
            values.append(duration_seconds)
        if size_bytes is not None:
            fields.append("size_bytes = ?")
            values.append(size_bytes)
        if path is not None:
            fields.append("path = ?")
            values.append(path)
        if telegram_message_id is not None:
            fields.append("telegram_message_id = ?")
            values.append(telegram_message_id)
        if error is not None:
            fields.append("error = ?")
            values.append(error)

        if not fields:
            return

        values.append(recording_id)
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    f"UPDATE recordings SET {', '.join(fields)} WHERE id = ?",
                    values,
                )
            finally:
                conn.close()

    def get_recording(self, recording_id: int) -> Recording | None:
        """Fetch a single recording record by ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    "SELECT * FROM recordings WHERE id = ?", (recording_id,)
                ).fetchone()
                if not row:
                    return None
                return self._row_to_recording(row)
            finally:
                conn.close()

    def get_latest_recording(self, username: str) -> Recording | None:
        """Get latest complete or stopped recording for a username."""
        normalized = username.strip().lower().lstrip("@")
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    """
                    SELECT * FROM recordings
                    WHERE username = ? AND status IN (?, ?) AND path IS NOT NULL
                    ORDER BY id DESC LIMIT 1
                    """,
                    (
                        normalized,
                        RecordingStatus.COMPLETE.value,
                        RecordingStatus.STOPPED.value,
                    ),
                ).fetchone()
                if not row:
                    # Fallback to any latest recording for user
                    row = conn.execute(
                        "SELECT * FROM recordings WHERE username = ? ORDER BY id DESC LIMIT 1",
                        (normalized,),
                    ).fetchone()
                if not row:
                    return None
                return self._row_to_recording(row)
            finally:
                conn.close()

    def get_recordings_for_user(
        self, username: str, limit: int = 10
    ) -> list[Recording]:
        """Fetch latest N recordings for a username."""
        normalized = username.strip().lower().lstrip("@")
        with self._lock:
            conn = self._get_connection()
            try:
                rows = conn.execute(
                    """
                    SELECT * FROM recordings
                    WHERE username = ?
                    ORDER BY id DESC LIMIT ?
                    """,
                    (normalized, limit),
                ).fetchall()
                return [self._row_to_recording(r) for r in rows]
            finally:
                conn.close()

    def get_storage_stats(
        self, recording_dir: str, retention_days: int = 0
    ) -> StorageStats:
        """Calculate storage utilization and DB recording totals."""
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    "SELECT COUNT(*) as total_count, coalesce(SUM(size_bytes), 0) as total_size FROM recordings"
                ).fetchone()
                total_recordings = int(row["total_count"]) if row else 0
                total_size_bytes = int(row["total_size"]) if row else 0
            finally:
                conn.close()

        rec_path = Path(recording_dir)
        rec_path.mkdir(parents=True, exist_ok=True)
        stat = shutil.disk_usage(str(rec_path))

        return StorageStats(
            total_recordings=total_recordings,
            total_size_bytes=total_size_bytes,
            recordings_path=str(rec_path.resolve()),
            disk_total_bytes=stat.total,
            disk_used_bytes=stat.used,
            disk_free_bytes=stat.free,
            retention_days=retention_days,
        )

    def get_expired_recordings(self, days: int) -> list[Recording]:
        """Find completed or stopped recordings older than N days."""
        if days <= 0:
            return []
        cutoff = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=days)
        ).isoformat()
        with self._lock:
            conn = self._get_connection()
            try:
                rows = conn.execute(
                    """
                    SELECT * FROM recordings
                    WHERE status IN (?, ?)
                      AND created_at < ?
                      AND path IS NOT NULL
                    ORDER BY id ASC
                    """,
                    (
                        RecordingStatus.COMPLETE.value,
                        RecordingStatus.STOPPED.value,
                        cutoff,
                    ),
                ).fetchall()
                return [self._row_to_recording(r) for r in rows]
            finally:
                conn.close()

    @staticmethod
    def _row_to_watch_target(row: sqlite3.Row) -> WatchTarget:
        return WatchTarget(
            id=row["id"],
            username=row["username"],
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_checked_at=row["last_checked_at"],
            last_live_at=row["last_live_at"],
            status=WatchStatus(row["status"]),
            last_error=row["last_error"],
        )

    @staticmethod
    def _row_to_recording(row: sqlite3.Row) -> Recording:
        return Recording(
            id=row["id"],
            username=row["username"],
            room_id=row["room_id"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            duration_seconds=row["duration_seconds"],
            status=RecordingStatus(row["status"]),
            path=row["path"],
            size_bytes=row["size_bytes"],
            telegram_message_id=row["telegram_message_id"],
            error=row["error"],
            created_at=row["created_at"],
        )
