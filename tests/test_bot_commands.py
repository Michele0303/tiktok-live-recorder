from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from bot.commands import (
    help_command,
    latest_command,
    record_command,
    recordings_command,
    start_command,
    status_command,
    stop_command,
    storage_command,
    unwatch_command,
    watch_command,
    watching_command,
)
from config.settings import Settings
from storage.models import Recording, RecordingStatus, StorageStats
from watch.manager import WatchManager


@pytest.fixture
def mock_context(tmp_path: Path):
    settings = Settings(
        telegram_bot_token="tok",
        telegram_allowed_user_id=100,
        telegram_allowed_chat_id=200,
    )
    wm = MagicMock(spec=WatchManager)
    wm.normalize_username.side_effect = lambda u: u.strip().lower().lstrip("@")
    wm.active_jobs = {}
    wm.get_watching.return_value = [{"username": "target1", "status": "OFFLINE"}]
    wm.get_status.return_value = {
        "username": "target1",
        "is_watched": True,
        "status": "OFFLINE",
        "last_checked_at": "2026-08-24T00:00:00Z",
    }
    wm.get_storage_summary.return_value = StorageStats(
        total_recordings=5,
        total_size_bytes=1024 * 1024 * 500,
        recordings_path="/data/recordings",
        disk_total_bytes=100_000_000_000,
        disk_used_bytes=20_000_000_000,
        disk_free_bytes=80_000_000_000,
        retention_days=0,
    )
    wm.watch = AsyncMock(return_value=(True, "👁 Watching @target1", False))
    wm.unwatch = AsyncMock(return_value=(True, "✅ Stopped watching @target1."))
    wm.record_once = AsyncMock(return_value=(True, "🔴 Started recording @target1."))
    wm.stop_recording = AsyncMock(return_value=(True, "⏹ Stopping recording for @target1."))
    wm.get_recordings.return_value = [
        Recording(
            id=1,
            username="target1",
            room_id="123",
            started_at="2026-08-24T00:00:00Z",
            ended_at="2026-08-24T01:00:00Z",
            duration_seconds=3600.0,
            status=RecordingStatus.COMPLETE,
            path="/data/rec.mp4",
            size_bytes=1_000_000,
            telegram_message_id=None,
            error=None,
            created_at="2026-08-24T00:00:00Z",
        )
    ]
    wm.get_latest.return_value = None

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot_data = {"settings": settings, "watch_manager": wm}
    context.args = []
    return context, wm


def _make_update():
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User, id=100)
    update.effective_chat = MagicMock(spec=Chat, id=200)
    update.effective_message = MagicMock(spec=Message)
    update.effective_message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_start_command(mock_context):
    context, wm = mock_context
    update = _make_update()

    await start_command(update, context)
    update.effective_message.reply_text.assert_called_once()
    assert "TikTok Live Recorder Service" in update.effective_message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_help_command(mock_context):
    context, wm = mock_context
    update = _make_update()

    await help_command(update, context)
    update.effective_message.reply_text.assert_called_once()
    assert "Available Commands" in update.effective_message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_watch_command(mock_context):
    context, wm = mock_context
    update = _make_update()
    context.args = ["@target1"]

    await watch_command(update, context)
    wm.watch.assert_called_once_with("@target1")
    update.effective_message.reply_text.assert_called_once_with(
        "👁 Watching @target1", parse_mode="HTML"
    )


@pytest.mark.asyncio
async def test_unwatch_command(mock_context):
    context, wm = mock_context
    update = _make_update()
    context.args = ["@target1"]

    await unwatch_command(update, context)
    wm.unwatch.assert_called_once_with("@target1")
    update.effective_message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_watching_command(mock_context):
    context, wm = mock_context
    update = _make_update()

    await watching_command(update, context)
    update.effective_message.reply_text.assert_called_once()
    assert "Watching 1 account" in update.effective_message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_status_command(mock_context):
    context, wm = mock_context
    update = _make_update()
    context.args = ["target1"]

    await status_command(update, context)
    update.effective_message.reply_text.assert_called_once()
    assert "Status for @target1" in update.effective_message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_record_command(mock_context):
    context, wm = mock_context
    update = _make_update()
    context.args = ["target1"]

    await record_command(update, context)
    wm.record_once.assert_called_once_with("target1")


@pytest.mark.asyncio
async def test_stop_command(mock_context):
    context, wm = mock_context
    update = _make_update()
    context.args = ["target1"]

    await stop_command(update, context)
    wm.stop_recording.assert_called_once_with("target1")


@pytest.mark.asyncio
async def test_latest_command(mock_context):
    context, wm = mock_context
    update = _make_update()
    context.args = ["target1"]

    await latest_command(update, context)
    wm.get_latest.assert_called_once_with("target1")


@pytest.mark.asyncio
async def test_recordings_command(mock_context):
    context, wm = mock_context
    update = _make_update()
    context.args = ["target1"]

    await recordings_command(update, context)
    update.effective_message.reply_text.assert_called_once()
    assert "Recent recordings for @target1" in update.effective_message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_storage_command(mock_context):
    context, wm = mock_context
    update = _make_update()

    await storage_command(update, context)
    update.effective_message.reply_text.assert_called_once()
    assert "Storage & System Statistics" in update.effective_message.reply_text.call_args[0][0]
