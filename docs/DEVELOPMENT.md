# Local Development & Testing Guide

This guide describes how to set up, test, and contribute to the TikTok Live Recorder repository.

---

## 1. Environment Setup

This project uses [`uv`](https://github.com/astral-sh/uv) for fast and deterministic Python dependency management.

```bash
# Clone the repository
git clone https://github.com/horacebramwell/tiktok-live-recorder.git
cd tiktok-live-recorder

# Install all dependencies including dev tools
uv sync --extra dev
```

---

## 2. Running Tests & Linters

### Run Automated Tests
```bash
uv run --extra dev pytest
```

### Run Linter & Formatter Checks
```bash
uv run --extra dev ruff check
```

---

## 3. Running Service Mode Locally

1. Create a local `.env` file from the template:
   ```bash
   cp .env.example .env
   ```
2. Configure your `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID`, and `TELEGRAM_ALLOWED_CHAT_ID`.
3. Start the service:
   ```bash
   uv run python src/bot_main.py
   ```
4. Send `/start` and `/watch <username>` in your Telegram bot to test interactive behavior.

---

## 4. Running CLI Mode Locally

The existing command-line interface remains fully functional:

```bash
# Manual single recording
uv run python src/main.py -user tiktokuser

# Automatic polling mode
uv run python src/main.py -user tiktokuser -mode automatic -automatic_interval 5

# Follower recording mode (requires authenticated cookies)
uv run python src/main.py -mode followers
```

---

## 5. Adding New Commands or Features

- **Bot Commands**: Add handler functions in [`src/bot/commands.py`](../src/bot/commands.py) decorated with `@authorized_only`, format response messages in [`src/bot/messages.py`](../src/bot/messages.py), and register in [`src/bot/application.py`](../src/bot/application.py).
- **Watch Manager**: Add core business logic in [`src/watch/manager.py`](../src/watch/manager.py).
- **Persistence**: Add SQLite queries and state mutations in [`src/storage/database.py`](../src/storage/database.py).
