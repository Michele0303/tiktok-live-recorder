from __future__ import annotations

from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.auth import authorized_only
from bot.messages import (
    format_help_message,
    format_recordings_list,
    format_start_message,
    format_status_message,
    format_storage_message,
    format_watching_list,
)
from watch.manager import WatchManager


def _get_watch_manager(context: ContextTypes.DEFAULT_TYPE) -> WatchManager:
    return context.bot_data["watch_manager"]


@authorized_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    wm = _get_watch_manager(context)
    watching_count = len(wm.get_watching())
    active_rec_count = len(wm.active_jobs)

    msg = format_start_message(watching_count, active_rec_count)
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    msg = format_help_message()
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


@authorized_only
async def watch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /watch <username> command."""
    if not context.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "ℹ️ Usage: <code>/watch &lt;username&gt;</code>\nExample: <code>/watch tiktokuser</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    raw_user = context.args[0]
    wm = _get_watch_manager(context)
    success, msg, _ = await wm.watch(raw_user)
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


@authorized_only
async def unwatch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unwatch <username> command."""
    if not context.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "ℹ️ Usage: <code>/unwatch &lt;username&gt;</code>\nExample: <code>/unwatch tiktokuser</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    raw_user = context.args[0]
    wm = _get_watch_manager(context)
    _, msg = await wm.unwatch(raw_user)
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


@authorized_only
async def watching_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /watching command."""
    wm = _get_watch_manager(context)
    targets = wm.get_watching()
    msg = format_watching_list(targets)
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


@authorized_only
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status <username> command."""
    if not context.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "ℹ️ Usage: <code>/status &lt;username&gt;</code>\nExample: <code>/status tiktokuser</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    raw_user = context.args[0]
    wm = _get_watch_manager(context)
    data = wm.get_status(raw_user)
    if not data:
        if update.effective_message:
            await update.effective_message.reply_text(
                f"❌ Invalid or unknown creator: <code>{raw_user}</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    msg = format_status_message(data)
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


@authorized_only
async def record_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /record <username> one-time recording command."""
    if not context.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "ℹ️ Usage: <code>/record &lt;username&gt;</code>\nExample: <code>/record tiktokuser</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    raw_user = context.args[0]
    wm = _get_watch_manager(context)
    _, msg = await wm.record_once(raw_user)
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


@authorized_only
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stop <username> command."""
    if not context.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "ℹ️ Usage: <code>/stop &lt;username&gt;</code>\nExample: <code>/stop tiktokuser</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    raw_user = context.args[0]
    wm = _get_watch_manager(context)
    _, msg = await wm.stop_recording(raw_user)
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


@authorized_only
async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /latest <username> command."""
    if not context.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "ℹ️ Usage: <code>/latest &lt;username&gt;</code>\nExample: <code>/latest tiktokuser</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    raw_user = context.args[0]
    wm = _get_watch_manager(context)
    rec = wm.get_latest(raw_user)

    if not rec:
        if update.effective_message:
            await update.effective_message.reply_text(
                f"ℹ️ No recordings found for @{wm.normalize_username(raw_user)}.",
                parse_mode=ParseMode.HTML,
            )
        return

    if not rec.path:
        if update.effective_message:
            await update.effective_message.reply_text(
                f"ℹ️ Recording metadata exists for @{rec.username}, but no file path is recorded.",
                parse_mode=ParseMode.HTML,
            )
        return

    path = Path(rec.path)
    # Find mp4 files inside recording directory or check if path is an mp4
    mp4_files: list[Path] = []
    if path.is_file() and path.suffix.lower() == ".mp4":
        mp4_files.append(path)
    elif path.is_dir():
        mp4_files = sorted(list(path.glob("*.mp4")))
        # Filter out _flv.mp4 if a converted .mp4 exists
        if len(mp4_files) > 1:
            clean_mp4s = [p for p in mp4_files if not p.name.endswith("_flv.mp4")]
            if clean_mp4s:
                mp4_files = clean_mp4s

    if not mp4_files:
        if update.effective_message:
            await update.effective_message.reply_text(
                f"⚠️ Recording file for @{rec.username} is no longer available on disk ({path}).",
                parse_mode=ParseMode.HTML,
            )
        return

    if update.effective_message:
        await update.effective_message.reply_text(
            f"📤 Sending latest recording for @{rec.username}...",
            parse_mode=ParseMode.HTML,
        )

    for p in mp4_files:
        await wm.delivery.send_recording_video(
            file_path=str(p.resolve()),
            caption=f"🎬 Latest recording for @{rec.username} ({rec.started_at[:10]})",
        )


@authorized_only
async def recordings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recordings <username> command."""
    if not context.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "ℹ️ Usage: <code>/recordings &lt;username&gt;</code>\nExample: <code>/recordings tiktokuser</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    raw_user = context.args[0]
    wm = _get_watch_manager(context)
    username = wm.normalize_username(raw_user)
    recordings = wm.get_recordings(username, limit=10)

    msg = format_recordings_list(username, recordings)
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


@authorized_only
async def storage_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /storage command."""
    wm = _get_watch_manager(context)
    stats = wm.get_storage_summary()
    msg = format_storage_message(stats)
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)
