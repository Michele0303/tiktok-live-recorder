from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from config.settings import Settings
from core.tiktok_api import TikTokAPI
from core.tiktok_recorder import RecordingResult
from delivery.telegram import TelegramDeliveryService
from storage.database import Database
from storage.models import WatchStatus
from watch.manager import WatchManager
from watch.recording_worker import RecordingWorker


@pytest.fixture
def test_setup(tmp_path: Path):
    db_file = tmp_path / "test_watch.db"
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        telegram_bot_token="fake_token",
        telegram_allowed_user_id=123,
        telegram_allowed_chat_id=456,
        recording_path=str(rec_dir),
        database_path=str(db_file),
        max_concurrent_recordings=2,
        watch_interval_seconds=10,
    )

    db = Database(str(db_file))
    delivery = MagicMock(spec=TelegramDeliveryService)
    delivery.deliver_recording = AsyncMock(return_value=[1001, 1002])
    delivery.send_message = AsyncMock(return_value=1001)

    api = MagicMock(spec=TikTokAPI)
    api.get_room_id_from_user.return_value = "room_123"
    api.is_room_alive.return_value = False

    worker = MagicMock(spec=RecordingWorker)
    worker.execute_recording_job = AsyncMock(
        return_value=RecordingResult(
            username="testuser",
            room_id="room_123",
            started_at="2026-08-24T00:00:00Z",
            ended_at="2026-08-24T00:02:00Z",
            duration_seconds=120.0,
            raw_path=None,
            final_path=str(rec_dir / "test.mp4"),
            size_bytes=1000,
            status="COMPLETE",
        )
    )

    manager = WatchManager(settings, db, delivery, api=api, worker=worker)
    return manager, db, api, worker


def test_username_normalization_and_validation(test_setup):
    manager, _, _, _ = test_setup

    assert manager.normalize_username("@Creator.Name-123_") == "creator.name-123_"
    assert manager.validate_username_syntax("@valid_user") is True
    assert manager.validate_username_syntax("invalid user spaces") is False
    assert manager.validate_username_syntax("bad/user/path") is False
    assert manager.validate_username_syntax("") is False


@pytest.mark.asyncio
async def test_watch_offline_target(test_setup):
    manager, db, api, worker = test_setup
    api.is_room_alive.return_value = False

    success, msg, is_live = await manager.watch("offline_creator")
    assert success is True
    assert is_live is False
    assert "Offline" in msg
    assert "I'll automatically record their next LIVE." in msg

    target = db.get_watch_target("offline_creator")
    assert target is not None
    assert target.enabled is True
    assert target.status == WatchStatus.OFFLINE


@pytest.mark.asyncio
async def test_watch_live_target_triggers_recording(test_setup):
    manager, db, api, worker = test_setup
    api.is_room_alive.return_value = True

    success, msg, is_live = await manager.watch("live_creator")
    assert success is True
    assert is_live is True
    assert "already LIVE" in msg
    assert "Recording is starting now" in msg

    # Allow spawned task to run
    await asyncio.sleep(0.05)
    worker.execute_recording_job.assert_called_once()


@pytest.mark.asyncio
async def test_unwatch(test_setup):
    manager, db, api, worker = test_setup
    await manager.watch("some_user")

    success, msg = await manager.unwatch("some_user")
    assert success is True
    assert "Stopped watching" in msg

    target = db.get_watch_target("some_user")
    assert target.enabled is False


@pytest.mark.asyncio
async def test_record_once_live(test_setup):
    manager, db, api, worker = test_setup
    api.is_room_alive.return_value = True

    success, msg = await manager.record_once("live_user")
    assert success is True
    assert "Started recording" in msg

    # Target should not be added to persistent watch list
    target = db.get_watch_target("live_user")
    assert target is None


@pytest.mark.asyncio
async def test_record_once_offline(test_setup):
    manager, db, api, worker = test_setup
    api.is_room_alive.return_value = False

    success, msg = await manager.record_once("offline_user")
    assert success is False
    assert "currently offline" in msg


@pytest.mark.asyncio
async def test_concurrency_limit(test_setup):
    manager, db, api, worker = test_setup
    api.is_room_alive.return_value = True

    # Simulate ongoing recording jobs that don't finish immediately
    hold_event = asyncio.Event()

    async def mock_record(*args, **kwargs):
        await hold_event.wait()
        return RecordingResult(
            username="u",
            room_id="r",
            started_at="2026-08-24T00:00:00Z",
            ended_at="2026-08-24T00:01:00Z",
            duration_seconds=60.0,
            raw_path=None,
            final_path=None,
            size_bytes=100,
            status="COMPLETE",
        )

    worker.execute_recording_job = AsyncMock(side_effect=mock_record)

    # Max concurrent recordings is 2
    await manager.watch("u1")
    await manager.watch("u2")
    success, msg, _ = await manager.watch("u3")

    assert success is True
    assert "maximum concurrent recordings" in msg

    hold_event.set()
    await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_stop_recording(test_setup):
    manager, db, api, worker = test_setup
    api.is_room_alive.return_value = True

    await manager.watch("live_target")
    assert "live_target" in manager.active_jobs

    success, msg = await manager.stop_recording("live_target")
    assert success is True
    assert "Stopping recording for @live_target" in msg


@pytest.mark.asyncio
async def test_get_watching_and_status(test_setup):
    manager, db, api, worker = test_setup
    api.is_room_alive.return_value = False

    await manager.watch("user_a")
    await manager.watch("user_b")

    watching = manager.get_watching()
    assert len(watching) == 2
    usernames = [w["username"] for w in watching]
    assert "user_a" in usernames
    assert "user_b" in usernames

    status_data = manager.get_status("user_a")
    assert status_data is not None
    assert status_data["username"] == "user_a"
    assert status_data["is_watched"] is True
