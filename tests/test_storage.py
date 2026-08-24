from __future__ import annotations

import datetime
from pathlib import Path

from storage.database import Database
from storage.models import RecordingStatus, WatchStatus


def test_init_db_is_idempotent(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db1 = Database(str(db_file))
    db2 = Database(str(db_file))
    assert db1.db_path == str(db_file)
    assert db2.db_path == str(db_file)
    assert db_file.is_file()


def test_watch_targets_crud(tmp_path: Path):
    db = Database(str(tmp_path / "test.db"))

    # Add watch
    target = db.add_or_enable_watch("@TestUser")
    assert target.username == "testuser"
    assert target.enabled is True
    assert target.status == WatchStatus.OFFLINE

    # Fetch
    fetched = db.get_watch_target("testuser")
    assert fetched is not None
    assert fetched.username == "testuser"

    # Fetch with @
    fetched_at = db.get_watch_target("@testuser")
    assert fetched_at is not None
    assert fetched_at.username == "testuser"

    # List
    watches = db.get_all_watches(enabled_only=True)
    assert len(watches) == 1
    assert watches[0].username == "testuser"

    # Update status
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.update_watch_status(
        "testuser",
        status=WatchStatus.LIVE,
        last_checked_at=now_iso,
        last_live_at=now_iso,
    )
    updated = db.get_watch_target("testuser")
    assert updated.status == WatchStatus.LIVE
    assert updated.last_live_at == now_iso

    # Disable watch
    assert db.disable_watch("testuser") is True
    assert len(db.get_all_watches(enabled_only=True)) == 0
    assert len(db.get_all_watches(enabled_only=False)) == 1

    # Re-enable watch
    re_enabled = db.add_or_enable_watch("testuser")
    assert re_enabled.enabled is True
    assert len(db.get_all_watches(enabled_only=True)) == 1


def test_recordings_crud(tmp_path: Path):
    db = Database(str(tmp_path / "test.db"))
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    rec_id = db.create_recording(
        username="creator1",
        room_id="999888",
        started_at=now_iso,
        status=RecordingStatus.STARTING,
    )
    assert rec_id > 0

    rec = db.get_recording(rec_id)
    assert rec is not None
    assert rec.username == "creator1"
    assert rec.status == RecordingStatus.STARTING

    # Update recording to COMPLETE
    ended_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.update_recording(
        recording_id=rec_id,
        status=RecordingStatus.COMPLETE,
        ended_at=ended_iso,
        duration_seconds=120.5,
        size_bytes=5_000_000,
        path="/data/recordings/creator1/2026/08/24/rec.mp4",
        telegram_message_id="12345",
    )

    updated_rec = db.get_recording(rec_id)
    assert updated_rec.status == RecordingStatus.COMPLETE
    assert updated_rec.duration_seconds == 120.5
    assert updated_rec.size_bytes == 5_000_000
    assert updated_rec.telegram_message_id == "12345"

    # Get latest
    latest = db.get_latest_recording("creator1")
    assert latest is not None
    assert latest.id == rec_id

    # List recordings for user
    user_recs = db.get_recordings_for_user("creator1", limit=10)
    assert len(user_recs) == 1


def test_reconcile_stale_recordings(tmp_path: Path):
    db = Database(str(tmp_path / "test.db"))
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    r1 = db.create_recording("u1", "1", now_iso, status=RecordingStatus.RECORDING)
    r2 = db.create_recording("u2", "2", now_iso, status=RecordingStatus.PROCESSING)
    r3 = db.create_recording("u3", "3", now_iso, status=RecordingStatus.COMPLETE)

    reconciled_count = db.reconcile_stale_recordings()
    assert reconciled_count == 2

    assert db.get_recording(r1).status == RecordingStatus.STOPPED
    assert db.get_recording(r1).error == "Interrupted by service restart"
    assert db.get_recording(r2).status == RecordingStatus.STOPPED
    assert db.get_recording(r3).status == RecordingStatus.COMPLETE


def test_storage_stats(tmp_path: Path):
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir(parents=True, exist_ok=True)
    db = Database(str(tmp_path / "test.db"))

    db.create_recording("u1", "1", "2026-08-24T00:00:00Z")
    db.update_recording(1, size_bytes=1024 * 1024 * 10, status=RecordingStatus.COMPLETE)

    stats = db.get_storage_stats(str(rec_dir), retention_days=14)
    assert stats.total_recordings == 1
    assert stats.total_size_bytes == 1024 * 1024 * 10
    assert stats.retention_days == 14
    assert stats.disk_total_bytes > 0
