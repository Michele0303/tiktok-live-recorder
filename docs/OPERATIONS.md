# Operations & Maintenance Guide

This document provides operational best practices for maintaining, troubleshooting, and operating the TikTok Live Recorder Telegram Watch Service.

---

## 1. Storage Management & Retention

### Disk Layout
All persistent data resides inside `/data`:
- `/data/watch.db`: SQLite database storing targets, timestamps, and recording records.
- `/data/recordings/<username>/<YYYY>/<MM>/<DD>/`: Partitioned video storage and metadata.

### Checking Storage via Telegram
Send `/storage` to your Telegram bot at any time to view:
- Total recordings saved
- Total recording storage size
- Available and used VPS disk space
- Configured retention policy

### Auto-Retention Policy (`DELETE_AFTER_DAYS`)
- By default, `DELETE_AFTER_DAYS=0` (recordings are kept indefinitely).
- To enable automatic deletion of old recordings, set `DELETE_AFTER_DAYS=14` (e.g. 14 days).
- The retention loop runs every 6 hours and removes completed recordings older than the threshold, updating SQLite metadata to record that the file was pruned.

---

## 2. Database Backup & Maintenance

### SQLite WAL Mode
The service configures SQLite in Write-Ahead Logging (`WAL`) mode for high concurrency.
The database files include:
- `/data/watch.db`
- `/data/watch.db-wal` (Write-Ahead Log)
- `/data/watch.db-shm` (Shared Memory)

### Performing a Safe Backup
To back up the database while the service is running, use SQLite's safe backup API:

```bash
sqlite3 /data/watch.db ".backup /data/watch_backup_$(date +%F).db"
```

---

## 3. Graceful Shutdown & Crash Recovery

### Handling Restarts and SIGTERM
The service listens for `SIGTERM` and `SIGINT` signals:
1. Stops accepting new polling cycles.
2. Gracefully signals active `TikTokRecorder` workers to finalize current buffers.
3. Remuxes partial streams to valid MP4 files and writes metadata.
4. Closes database connections cleanly.

### Startup Crash Reconciliation
If the container or host crashes unexpectedly during a recording:
- On startup, `WatchManager` automatically scans the `recordings` table.
- Any rows left in `STARTING`, `RECORDING`, `PROCESSING`, or `UPLOADING` state are reconciled to `STOPPED` with error note `"Interrupted by service restart"`.
- This ensures watch targets resume normal monitoring without duplicate jobs or orphaned state.

---

## 4. TikTok Cookies & Geo-Bypassing

Some TikTok creators or regions require authentication or trigger WAF/captcha challenges.

### Providing Custom Cookies
1. Export your TikTok session cookies (specifically `sessionid_ss` and `tt-target-idc`) using a browser extension (such as *Cookie-Editor*).
2. Place your `cookies.json` inside `/data/cookies.json` or mount it via Docker:
   ```json
   {
     "sessionid_ss": "your_session_cookie_here",
     "tt-target-idc": "useast2a"
   }
   ```
3. The service checks `/data/cookies.json` automatically on startup.

### Using a Proxy (`TIKTOK_PROXY`)
If your VPS IP is blocked or restricted by TikTok:
- Set `TIKTOK_PROXY=http://user:password@ip:port` or `socks5://ip:port` in your `.env`.
- Initial checks will route through the proxy, while stream data downloads directly for maximum speed and stability.

---

## 5. Log Inspection

View real-time logs in Dokploy or via Docker:

```bash
# Follow logs of the recorder container
docker logs -f tiktok-live-recorder

# Follow logs of the local bot API container
docker logs -f telegram-bot-api
```
