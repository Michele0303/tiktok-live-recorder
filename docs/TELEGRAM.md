# Telegram Bot Setup & Command Reference

This document explains how to create your personal Telegram bot using BotFather, configure authorization, and use the commands provided by the TikTok Live Recorder Watch Service.

---

## 1. Creating Your Telegram Bot with BotFather

1. Open Telegram and search for [`@BotFather`](https://t.me/BotFather).
2. Send `/newbot` to start the bot creation wizard.
3. Choose a display name (e.g. `My TikTok Recorder`).
4. Choose a unique username ending in `bot` (e.g. `my_tiktok_recorder_bot`).
5. BotFather will provide an HTTP API token (format: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).
6. Copy this token into your environment as `TELEGRAM_BOT_TOKEN`.

---

## 2. Setting Up Command Menu in BotFather

To enable Telegram's auto-complete command menu, send `/setcommands` to `@BotFather`, select your bot, and paste the following list:

```text
watch - Add creator to persistent auto-record watch list
unwatch - Remove creator from persistent watch list
watching - List all currently monitored creators
status - Check target status and recording progress
record - One-time instant recording if user is LIVE
stop - Gracefully stop an active recording
latest - Send latest recorded video file
recordings - Show recent 10 recordings for creator
storage - View disk space and retention stats
help - Show help and command documentation
start - Service health and status overview
```

---

## 3. Finding Your User ID and Chat ID

The service is strictly private and only accepts commands and delivers media to the authorized user/chat ID:

1. Open Telegram and search for [`@userinfobot`](https://t.me/userinfobot) or [`@RawDataBot`](https://t.me/RawDataBot).
2. Send `/start` to obtain your numeric `Id` (e.g. `123456789`).
3. Set `TELEGRAM_ALLOWED_USER_ID=123456789`.
4. If you are chatting with the bot directly in a private message, your `TELEGRAM_ALLOWED_CHAT_ID` is identical to your user ID (`123456789`). If you are using a private channel or group, provide that numeric chat ID instead.

---

## 4. Command Reference

### `/watch <username>`
Adds a creator to the persistent watch list in SQLite.
- Accepts both `username` and `@username`.
- Syntax is validated and normalized to lowercase.
- Checks live status immediately:
  - If **offline**: Confirms target is monitored and will automatically record when they start streaming.
  - If **already LIVE**: Immediately initiates recording.

### `/unwatch <username>`
Disables persistent monitoring for a creator.
- If an active recording is in progress, the current recording will complete naturally. Use `/stop <username>` if you wish to abort it immediately.

### `/watching`
Displays all currently enabled watch targets with live status indicators:
- 🔴 `@creator` — Recording / LIVE
- ⚪ `@creator` — Offline
- 🟡 `@creator` — Checking

### `/status <username>`
Returns detailed operational information for a creator:
- Watch status (Watched / Not Watched)
- Current state (OFFLINE / LIVE / RECORDING)
- Active recording start timestamp (if running)
- Last checked timestamp
- Last detected LIVE timestamp
- Last error message (if any)

### `/record <username>`
Performs a one-time recording attempt without adding the creator to persistent monitoring:
- If creator is LIVE: Begins recording immediately.
- If creator is offline: Informs the user and takes no further action.

### `/stop <username>`
Gracefully interrupts an ongoing live recording:
- Stops the stream download cleanly.
- Finalizes and remuxes the captured video to MP4.
- Segments the video if larger than `MAX_RECORDING_PART_BYTES`.
- Uploads the resulting video to your Telegram chat.

### `/latest <username>`
Finds the most recent recording for a creator and delivers the MP4 video directly to Telegram.

### `/recordings <username>`
Lists the 10 most recent recordings for a creator with:
- Timestamp (UTC)
- Duration
- File size
- Final status (`COMPLETE`, `STOPPED`, `FAILED`)

### `/storage`
Displays disk utilization metrics:
- Total recordings saved in SQLite
- Total recording storage consumed
- VPS disk space (Used / Free / Total)
- Configured retention policy (`DELETE_AFTER_DAYS`)

### `/help`
Displays concise command usage instructions.

### `/start`
Displays service health and summary of active watches.

---

## 5. Standard Bot API vs Local Bot API

- **Standard Telegram Bot API**: Default if `TELEGRAM_BOT_API_BASE_URL` is omitted. Supports file uploads up to 50 MB.
- **Telegram Local Bot API Server**: Run via Docker Compose (`aiogram/telegram-bot-api`). Supports file uploads up to **2 GB**. The service is configured by default with `MAX_RECORDING_PART_BYTES=1932735283` (~1.8 GB) to automatically segment large streams so they upload smoothly without hitting size limits.
