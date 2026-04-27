<div align="center">

# TikTok Live Recorder 🎥

_TikTok Live Recorder is a tool for recording live streaming TikTok._

[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/tiktokliverecorder)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
[![Licence](https://img.shields.io/github/license/Ileriayo/markdown-badges?style=for-the-badge)](./LICENSE)
[![Stars](https://img.shields.io/github/stars/Michele0303/tiktok-live-recorder?style=for-the-badge)](https://github.com/Michele0303/tiktok-live-recorder/stargazers)
[![Release](https://img.shields.io/github/v/release/Michele0303/tiktok-live-recorder?style=for-the-badge)](https://github.com/Michele0303/tiktok-live-recorder/releases/latest)
[![Docker Pulls](https://img.shields.io/docker/pulls/michele0303/tiktok-live-recorder?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/michele0303/tiktok-live-recorder)

The TikTok Live Recorder is a tool designed to easily capture and save live streaming sessions from TikTok. It records both audio and video, allowing users to revisit and preserve engaging live content for later enjoyment and analysis. It's a valuable resource for creators, researchers, and anyone who wants to capture memorable moments from TikTok live streams.

![preview](https://i.ibb.co/YTHp5DT/image.png)

</div>

---

### Don't want to run it yourself?

**[TikRec](https://tikrec.com?utm_source=github&utm_medium=readme&utm_campaign=tiktok-live-recorder)** is the hosted cloud version of this recorder. Same recording engine, running 24/7 on a server, delivering MP4s straight to your Telegram.

- No installation, no terminal, no FFmpeg
- Add TikTok usernames to a watchlist via [@tikrec_live_bot](https://t.me/tikrec_live_bot?start=s_github) on Telegram
- Recordings delivered automatically when creators go live
- Free for your watchlist. Past recordings from the archive available with Telegram Stars.

**[Open TikRec on Telegram](https://t.me/tikrec_live_bot?start=s_github)** | **[Browse the recording archive](https://tikrec.com/latest?utm_source=github&utm_medium=readme&utm_campaign=tiktok-live-recorder)**

---

## Table of Contents

- [Installation](#installation)
- [Usage](#command-line-usage)
- [Guide](#guide)
- [TikRec Cloud vs Self-Hosted](#tikrec-cloud-vs-self-hosted)

## Installation

**Prerequisites:** [Git](https://git-scm.com), [Python 3.11+](https://www.python.org/downloads/), [FFmpeg](https://ffmpeg.org/download.html)

<details>
<summary>Windows 💻</summary>

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
git clone https://github.com/Michele0303/tiktok-live-recorder
cd tiktok-live-recorder
uv venv
uv sync
uv run python src/main.py -h
```

</details>

<details>
<summary>Linux 🐧</summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/Michele0303/tiktok-live-recorder
cd tiktok-live-recorder
uv venv
uv sync
uv run python src/main.py -h
```

</details>

<details>
<summary>macOS 🍎</summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
brew install ffmpeg
git clone https://github.com/Michele0303/tiktok-live-recorder
cd tiktok-live-recorder
uv venv
uv sync
uv run python src/main.py -h
```

</details>

<details>
<summary>Android — Termux 📱</summary>

Install Termux from [F-Droid](https://f-droid.org/packages/com.termux/) (avoid the Play Store version).

```bash
pkg update && pkg upgrade
pkg install git ffmpeg uv tur-repo
pkg uninstall python
pkg install python3.11
git clone https://github.com/Michele0303/tiktok-live-recorder
cd tiktok-live-recorder
uv venv
uv sync
uv run python src/main.py -h
```

</details>

<details>
<summary>Docker 🐳</summary>

```bash
sudo docker run \
  -v ./output:/output \
  michele0303/tiktok-live-recorder:latest \
  -output /output \
  -user <username>
```

</details>

## Command-Line Usage

```bash
uv run python src/main.py [options]
```

### Options

| Flag | Description |
|------|-------------|
| `-user <USERNAME>` | Username(s) to record. Separate multiple with commas. |
| `-url <URL>` | TikTok live URL to record from. |
| `-room_id <ROOM_ID>` | Room ID to record from. |
| `-mode <MODE>` | Recording mode: `manual`, `automatic`, `followers`. |
| `-automatic_interval <MIN>` | Polling interval in minutes (automatic mode only). |
| `-output <DIRECTORY>` | Directory where recordings will be saved. |
| `-duration <SECONDS>` | Stop recording after this many seconds. |
| `-proxy <URL>` | HTTP proxy to bypass regional restrictions. |
| `-bitrate <BITRATE>` | Output bitrate for post-processing (e.g. `1M`, `1000k`). |
| `-telegram` | Upload the recording to Telegram when done. Requires `telegram.json`. |
| `-no-update-check` | Skip the automatic update check on startup. |

### Recording Modes

- **`manual`** *(default)*: Records immediately if the user is currently live.
- **`automatic`**: Polls at regular intervals and records whenever the user goes live.
- **`followers`**: Automatically records live streams from all followed users.

## TikRec Cloud vs Self-Hosted

This CLI tool gives you full control - run it on your own machine, customize the output, pipe it into your own workflow. But it requires a computer running 24/7, FFmpeg installed, and manual setup per creator.

[TikRec](https://tikrec.com?utm_source=github&utm_medium=readme&utm_campaign=tiktok-live-recorder) is the cloud version built by the same developer. It uses the same FFmpeg recording engine but runs on a server so you don't have to keep anything running.

| | This CLI | [TikRec Cloud](https://tikrec.com?utm_source=github&utm_medium=readme&utm_campaign=tiktok-live-recorder) |
|---|---|---|
| Setup | Python + FFmpeg + terminal | Open Telegram, send /watch |
| Runs on | Your machine | Cloud (24/7) |
| Storage | Your disk | Telegram (unlimited) |
| Multi-creator | One process per user | Automatic for all watchlist |
| Monitoring | Manual | 24/7, detection < 3 min |
| Cost | Free + electricity | Free |
| Customizable | Full source code | No |

**Use this CLI** if you want full control, custom output, or integration with your own tools.

**Use [TikRec](https://t.me/tikrec_live_bot?start=s_github)** if you want recordings delivered to Telegram without maintaining anything.

## Guide

- [How to set cookies in cookies.json](https://github.com/Michele0303/tiktok-live-recorder/blob/main/docs/GUIDE.md#how-to-set-cookies)
- [How to get room_id](https://github.com/Michele0303/tiktok-live-recorder/blob/main/docs/GUIDE.md#how-to-get-room_id)
- [How to enable upload to Telegram](https://github.com/Michele0303/tiktok-live-recorder/blob/main/docs/GUIDE.md#how-to-enable-upload-to-telegram)

## Contributing

Contributions are welcome! Feel free to open an [issue](https://github.com/Michele0303/tiktok-live-recorder/issues) or submit a [pull request](https://github.com/Michele0303/tiktok-live-recorder/pulls).

## Legal ⚖️

This code is in no way affiliated with, authorized, maintained, sponsored or endorsed by TikTok or any of its affiliates or subsidiaries. Use at your own risk.
