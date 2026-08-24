# Dokploy Deployment Guide

This guide walks through deploying the TikTok Live Recorder Telegram Watch Service on your VPS using [Dokploy](https://dokploy.com) and Docker Compose.

---

## Prerequisites

1. A VPS running Dokploy (Ubuntu 22.04/24.04 or Debian 12 recommended).
2. Your GitHub repository fork: `horacebramwell/tiktok-live-recorder`.
3. Telegram credentials:
   - `TELEGRAM_BOT_TOKEN`: From [@BotFather](https://t.me/BotFather).
   - `TELEGRAM_ALLOWED_USER_ID`: Numeric user ID from [@userinfobot](https://t.me/userinfobot).
   - `TELEGRAM_ALLOWED_CHAT_ID`: Numeric chat ID where videos will be delivered.
   - `TELEGRAM_API_ID` & `TELEGRAM_API_HASH`: From [my.telegram.org](https://my.telegram.org) (for the Local Bot API 2GB upload server).

---

## Step-by-Step Deployment Instructions

### 1. Create a Project in Dokploy
1. Log in to your Dokploy dashboard.
2. Click **Create Project** (e.g. name it `Media Services` or `TikTok Recorder`).

### 2. Create a Compose Service
1. Inside your project, click **Create Service**.
2. Select **Compose** as the service type.
3. Name your service (e.g. `tiktok-live-recorder`).

### 3. Connect GitHub Repository
1. In the service settings under **Source**, select **GitHub**.
2. Select your repository: `horacebramwell/tiktok-live-recorder`.
3. Select branch: `main`.
4. Enable **Auto Deploy** if you want Dokploy to redeploy automatically whenever you push commits to `main`.
5. Ensure the compose file path is set to `docker-compose.yml`.

### 4. Configure Environment Variables
Navigate to the **Environment** tab in Dokploy and enter your configuration:

```env
# Required Telegram Bot Authentication
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_ALLOWED_USER_ID=123456789
TELEGRAM_ALLOWED_CHAT_ID=123456789

# Telegram Local Bot API Configuration (Enables up to 2GB uploads)
TELEGRAM_BOT_API_BASE_URL=http://telegram-bot-api:8081/bot
TELEGRAM_BOT_API_FILE_BASE_URL=http://telegram-bot-api:8081/file/bot
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef

# Storage & Watch Configuration
WATCH_INTERVAL_SECONDS=30
RECORDING_PATH=/data/recordings
DATABASE_PATH=/data/watch.db
MAX_CONCURRENT_RECORDINGS=3
MAX_RECORDING_PART_BYTES=1932735283
DELETE_AFTER_DAYS=0
LOG_LEVEL=INFO
```

### 5. Verify Persistent Volumes
Dokploy automatically provisions named volumes declared in `docker-compose.yml`:
- `tiktok_recorder_data`: Mounted to `/data` in the recorder container and `/data` in the Bot API container.
- `tiktok_telegram_bot_api_data`: Mounted to `/var/lib/telegram-bot-api`.

> [!IMPORTANT]
> The `/data` directory contains your persistent SQLite database (`/data/watch.db`) and all recordings (`/data/recordings/`). This data is preserved across container restarts, image updates, and Dokploy redeployments.

### 6. Deploy
1. Click **Deploy** in the top-right corner of Dokploy.
2. Open the **Deployments / Logs** tab to monitor the build process:
   - Dokploy will build the `tiktok-live-recorder` Dockerfile.
   - Pull `aiogram/telegram-bot-api:latest`.
   - Start both containers on the internal `recorder_net` network.

### 7. Verify Operation in Telegram
1. Open your Telegram bot.
2. Send `/start`. You should receive:
   ```text
   🤖 TikTok Live Recorder Service
   ✅ Service is active and healthy.
   👁 Watched creators: 0
   🔴 Active recordings: 0
   ```
3. Send `/watch <username>` to add a creator.
4. Send `/watching` to verify the account is monitored.

### 8. Verify Persistence Across Redeployments
1. Add a test creator using `/watch username`.
2. In Dokploy, click **Redeploy**.
3. Once redeployed, send `/watching` to your bot.
4. Verify that the creator target is still present in the list.
