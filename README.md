<div align="center">

# TikTok Live Recorder & Telegram Watch Service 🎥🤖

_A self-hosted personal TikTok LIVE recording service with private Telegram bot control, 24/7 persistent monitoring, and standalone CLI recorder._

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](./docker-compose.yml)
[![Dokploy Ready](https://img.shields.io/badge/Dokploy-Ready-purple.svg)](./docs/DEPLOYMENT_DOKPLOY.md)

</div>

---

## 🌟 Overview

This repository is a production-quality fork of [Michele0303/tiktok-live-recorder](https://github.com/Michele0303/tiktok-live-recorder), extended to provide a persistent, self-hosted **Telegram Watch Service** designed to run 24/7 on a VPS via **Dokploy** or **Docker Compose**.

It supports two distinct execution modes:
1. **🤖 Telegram Watch Service Mode (`src/bot_main.py`)**: A persistent background service controlled via a private Telegram bot. Monitors creators, auto-detects when they go LIVE, records streams, remuxes to MP4, segments large files (< 1.8 GB), and delivers completed recordings to your private Telegram chat.
2. **💻 Standalone CLI Mode (`src/main.py`)**: The original manual/batch command-line recording tool.

---

## 🚀 Telegram Watch Service

Deploy this repository on your VPS using Dokploy or Docker Compose, configure your private Telegram Bot token, and control recording directly from Telegram!

### 📱 Bot Commands

| Command | Description |
|---|---|
| `/watch <username>` | Add creator to persistent auto-record watch list. Immediately starts recording if user is already LIVE. |
| `/unwatch <username>` | Remove creator from persistent watch list (running recordings finish naturally). |
| `/watching` | List all monitored creators with live status indicators (🔴 LIVE, ⚪ Offline). |
| `/status <username>` | View creator state, last checked time, and active recording info. |
| `/record <username>` | One-time instant recording if the creator is currently LIVE. |
| `/stop <username>` | Gracefully stop an active recording and upload the captured video. |
| `/latest <username>` | Resend the latest recorded video file to your chat. |
| `/recordings <username>` | View list of 10 most recent recordings for a creator. |
| `/storage` | Check disk space, total recording count, and retention policy. |
| `/help` | Show command documentation and usage guide. |
| `/start` | Service health status and summary. |

### 🛠 Quick Start (Docker Compose / Dokploy)

1. Clone the repository and configure `.env`:
   ```bash
   cp .env.example .env
   # Edit .env and set your TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_ID, and TELEGRAM_ALLOWED_CHAT_ID
   ```
2. Start the services:
   ```bash
   docker compose up -d
   ```
3. Open your Telegram bot and send `/start`.

For complete step-by-step Dokploy deployment instructions, see [Dokploy Deployment Guide](docs/DEPLOYMENT_DOKPLOY.md).

---

## 💻 Standalone CLI Mode

The original command-line interface remains fully functional:

```bash
# Install dependencies
uv sync

# Run manual recording
uv run python src/main.py -user username

# Run automatic polling mode
uv run python src/main.py -user username -mode automatic -automatic_interval 5

# Record multiple creators
uv run python src/main.py -user creator1,creator2 -mode automatic
```

### CLI Flags

| Flag | Description |
|---|---|
| `-user <USERNAME>` | Username(s) to record (comma-separated). |
| `-url <URL>` | TikTok live stream URL. |
| `-room_id <ROOM_ID>` | TikTok room ID to record. |
| `-mode <MODE>` | `manual`, `automatic`, `followers`. |
| `-automatic_interval <MIN>` | Check interval in minutes for automatic mode. |
| `-output <DIR>` | Destination directory for recordings. |
| `-duration <SECONDS>` | Stop recording after N seconds. |
| `-proxy <URL>` | HTTP/SOCKS proxy for geo-restricted regions. |
| `-bitrate <BITRATE>` | Output video bitrate (e.g. `1M`, `1000k`). |
| `-ffmpeg-path <PATH>` | Custom FFmpeg binary path. |
| `-telegram` | Upload to Telegram via Telethon user account (`telegram.json`). |
| `-no-update-check` | Disable startup update check. |

---

## 📚 Documentation

- 📐 [Architecture & Mermaid Diagrams](docs/ARCHITECTURE.md)
- 🤖 [Telegram Bot Setup & Commands](docs/TELEGRAM.md)
- 🚀 [Dokploy Deployment Guide](docs/DEPLOYMENT_DOKPLOY.md)
- 🔧 [Operations, Storage & Retention](docs/OPERATIONS.md)
- 💻 [Local Development & Testing](docs/DEVELOPMENT.md)
- 🤖 [Agent Reference (AGENTS.md)](AGENTS.md)

---

## 📜 Upstream Attribution & License

This project is a fork of [TikTok Live Recorder](https://github.com/Michele0303/tiktok-live-recorder) originally created by Michele0303.
The project is licensed under the [MIT License](./LICENSE).

---

## ⚖️ Legal Disclaimer

This tool is in no way affiliated with, authorized, maintained, sponsored, or endorsed by TikTok or any of its affiliates. Use responsibly and in accordance with local regulations.
