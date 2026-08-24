# AGENTS.md

## Project Overview
This repository is a production-grade fork of the open-source **TikTok Live Recorder**, extended to provide a persistent, self-hosted **Telegram Watch Service** alongside the original standalone CLI recorder.

The service runs continuously on a VPS (via Dokploy & Docker Compose) and allows authorized users to control persistent 24/7 account monitoring, automatic live detection, MP4 recording, large-file segmentation, and Telegram video delivery via a private Telegram bot.

---

## Architectural Boundaries & Domain Structure

```text
src/
├── bot/               # Telegram bot layer (python-telegram-bot >= 22.8)
│   ├── application.py # Bot app builder & handler registration
│   ├── auth.py        # Centralized user/chat ID authorization decorator
│   ├── commands.py    # Telegram command handlers (/watch, /unwatch, etc.)
│   └── messages.py    # Formatted Telegram HTML response templates
├── watch/             # Watch management & background worker orchestrator
│   ├── manager.py     # Central WatchManager (polling, concurrency, lifecycle)
│   ├── models.py      # ActiveJob dataclasses
│   └── recording_worker.py # Background recording, path partitioning, metadata
├── storage/           # SQLite persistence layer (/data/watch.db)
│   ├── database.py    # Thread-safe SQLite abstraction & state transitions
│   └── models.py      # WatchTarget, Recording, and StorageStats models
├── delivery/          # Video delivery layer
│   └── telegram.py    # Multi-part/single video uploader & Bot API client
├── config/            # Typed configuration
│   └── settings.py    # Environment variables & .env validation
├── core/              # TikTok stream capture & API client
│   ├── tiktok_api.py  # Webcast API and room status checks
│   └── tiktok_recorder.py # Stream downloader & RecordingResult generator
├── utils/             # Helpers & FFmpeg tools
│   ├── video_management.py # Conversion, probing, and segmentation (< 1.8GB)
│   └── recorder_config.py  # Recorder options dataclass
├── bot_main.py        # Service-mode entrypoint (Docker / Dokploy)
└── main.py            # CLI-mode entrypoint (Manual / CLI scripts)
```

---

## Critical Invariants

1. **SQLite is the Source of Truth**: Watch targets and recording states are persisted in SQLite (`/data/watch.db`). The filesystem is the source of truth for media files.
2. **Never Delete on Upload Failure**: If Telegram upload fails due to network issues or file size, the local video file and metadata **must never be deleted**.
3. **Async / Sync Boundary**: TikTok streaming and FFmpeg processing are synchronous/blocking and must always be executed in background worker threads (`asyncio.to_thread`) to prevent blocking the Telegram bot's asyncio event loop.
4. **Strict Authorization**: Every Telegram command handler must enforce `TELEGRAM_ALLOWED_USER_ID` and `TELEGRAM_ALLOWED_CHAT_ID` through `@authorized_only`.
5. **Backwards Compatibility**: The CLI entrypoint `python src/main.py` and its arguments (`-user`, `-mode`, etc.) must remain fully functional.
6. **No Committed Secrets**: Never commit `.env`, bot tokens, API hashes, or real TikTok cookies (`cookies.json` contains only templates).

---

## Development & Test Commands

```bash
# Sync dependencies
uv sync --extra dev

# Run full test suite
uv run --extra dev pytest

# Run linter and formatting checks
uv run --extra dev ruff check

# Run service locally
python src/bot_main.py
```

---

## Deeper Documentation Pointers
- System Architecture & Mermaid Diagrams: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Telegram Bot Setup & Commands: [`docs/TELEGRAM.md`](docs/TELEGRAM.md)
- Dokploy Deployment Guide: [`docs/DEPLOYMENT_DOKPLOY.md`](docs/DEPLOYMENT_DOKPLOY.md)
- Operations, Storage & Maintenance: [`docs/OPERATIONS.md`](docs/OPERATIONS.md)
- Local Development & Testing Guide: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
