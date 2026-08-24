from __future__ import annotations

from typing import Any

from delivery.telegram import format_duration, format_size
from storage.models import Recording, StorageStats


def format_start_message(active_watches: int, active_recordings: int) -> str:
    return (
        "🤖 <b>TikTok Live Recorder Service</b>\n\n"
        "✅ Service is active and healthy.\n"
        f"👁 Watched creators: <b>{active_watches}</b>\n"
        f"🔴 Active recordings: <b>{active_recordings}</b>\n\n"
        "Use /help to see available commands."
    )


def format_help_message() -> str:
    return (
        "📖 <b>Available Commands</b>\n\n"
        "• <code>/watch &lt;username&gt;</code> — Add creator to persistent auto-record watch list\n"
        "• <code>/unwatch &lt;username&gt;</code> — Remove creator from watch list\n"
        "• <code>/watching</code> — List all watched accounts and their live status\n"
        "• <code>/status &lt;username&gt;</code> — Check target status and recording state\n"
        "• <code>/record &lt;username&gt;</code> — One-time instant recording if user is LIVE\n"
        "• <code>/stop &lt;username&gt;</code> — Gracefully stop an active recording\n"
        "• <code>/latest &lt;username&gt;</code> — Send latest recorded video file\n"
        "• <code>/recordings &lt;username&gt;</code> — Show recent 10 recordings for creator\n"
        "• <code>/storage</code> — View disk usage and retention stats\n"
        "• <code>/help</code> — Show this help message"
    )


def format_watching_list(targets: list[dict[str, Any]]) -> str:
    if not targets:
        return "👁 <b>Watching 0 accounts</b>\n\nUse <code>/watch username</code> to start monitoring creators."

    count = len(targets)
    lines = [f"👁 <b>Watching {count} account{'s' if count != 1 else ''}</b>\n"]

    for t in targets:
        status = t.get("status", "OFFLINE")
        username = t["username"]
        if status == "RECORDING":
            lines.append(f"🔴 @{username} — Recording")
        elif status == "LIVE":
            lines.append(f"🔴 @{username} — LIVE")
        elif status == "CHECKING":
            lines.append(f"🟡 @{username} — Checking")
        else:
            lines.append(f"⚪ @{username} — Offline")

    return "\n".join(lines)


def format_status_message(data: dict[str, Any]) -> str:
    username = data["username"]
    is_watched = "Yes" if data.get("is_watched") else "No"
    status = data.get("status", "UNKNOWN")

    status_icon = "⚪"
    if status in ("RECORDING", "LIVE"):
        status_icon = "🔴"
    elif status == "ERROR":
        status_icon = "⚠️"

    lines = [
        f"📊 <b>Status for @{username}</b>\n",
        f"• Watched: <b>{is_watched}</b>",
        f"• Current State: {status_icon} <b>{status}</b>",
    ]

    if data.get("active_recording_started_at"):
        lines.append(f"• Active Recording: <b>Started {data['active_recording_started_at']}</b>")
    if data.get("last_checked_at"):
        lines.append(f"• Last Checked: <code>{data['last_checked_at']}</code>")
    if data.get("last_live_at"):
        lines.append(f"• Last LIVE Detected: <code>{data['last_live_at']}</code>")
    if data.get("last_error"):
        lines.append(f"• Last Error: <i>{data['last_error']}</i>")

    return "\n".join(lines)


def format_recordings_list(username: str, recordings: list[Recording]) -> str:
    if not recordings:
        return f"📁 No recordings found for @{username}."

    lines = [f"📁 <b>Recent recordings for @{username} ({len(recordings)})</b>\n"]

    for idx, rec in enumerate(recordings, start=1):
        date_str = rec.started_at[:19].replace("T", " ")
        dur_str = format_duration(rec.duration_seconds or 0.0)
        size_str = format_size(rec.size_bytes or 0)
        status_str = rec.status.value

        lines.append(
            f"<b>{idx}.</b> {date_str}\n"
            f"   ⏱ {dur_str} • 📦 {size_str} • State: <code>{status_str}</code>"
        )

    return "\n".join(lines)


def format_storage_message(stats: StorageStats) -> str:
    used_str = format_size(stats.disk_used_bytes)
    total_str = format_size(stats.disk_total_bytes)
    free_str = format_size(stats.disk_free_bytes)
    rec_size_str = format_size(stats.total_size_bytes)
    retention_str = (
        f"{stats.retention_days} days"
        if stats.retention_days > 0
        else "Indefinite (Disabled)"
    )

    percent_used = (
        (stats.disk_used_bytes / stats.disk_total_bytes * 100)
        if stats.disk_total_bytes > 0
        else 0
    )

    return (
        "💾 <b>Storage & System Statistics</b>\n\n"
        f"• Total Recordings: <b>{stats.total_recordings}</b>\n"
        f"• Recordings Size: <b>{rec_size_str}</b>\n"
        f"• Storage Path: <code>{stats.recordings_path}</code>\n\n"
        f"• Disk Used: <b>{used_str}</b> / <b>{total_str}</b> ({percent_used:.1f}%)\n"
        f"• Free Space: <b>{free_str}</b>\n"
        f"• Auto-Retention: <b>{retention_str}</b>"
    )
