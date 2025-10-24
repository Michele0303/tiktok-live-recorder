<div align="center">

<h1> TikTok Live Recorder🎥</h1>

<em>TikTok Live Recorder is a tool for recording live streaming tiktok.</em>

[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/tiktokliverecorder)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) 
[![Licence](https://img.shields.io/github/license/Ileriayo/markdown-badges?style=for-the-badge)](./LICENSE)

The TikTok Live Recorder is a tool designed to easily capture and save live streaming sessions from TikTok. It records both audio and video, allowing users to revisit and preserve engaging live content for later enjoyment and analysis. It's a valuable resource for creators, researchers, and anyone who wants to capture memorable moments from TikTok live streams.

<img src="https://i.ibb.co/YTHp5DT/image.png" alt="image" border="0">

</div>

<div align="left">


  <h1> How To Use </h1>

- [Install on Windows & Linux 💻](#install-on-windows-)
- [Install on Linux 💻](#install-on-linux-)
- [Install on Android 📱](#install-on-android-)

</div>

## Install on Windows 💻

To clone and run this application, you'll need [Git](https://git-scm.com) and [Python3.11+](https://www.python.org/downloads/) and [FFmpeg](https://www.youtube.com/watch?v=OlNWCpFdVMA) installed on your computer. From your command line:

<!-- <img src="https://i.ibb.co/8DkzXZn/image.png" alt="image" border="0"> -->

<be>

</div>

  ```bash
# Clone this repository
$ git clone https://github.com/Michele0303/tiktok-live-recorder
# Go into the repository
$ cd tiktok-live-recorder
# Go into the source code
$ cd src
# Install dependencies
$ pip install -r requirements.txt
# Run the app on windows
$ python main.py -h
  ```

## Install on Linux 🐧

To clone and run this application, you'll need [Git](https://git-scm.com) and [Python3.11+](https://www.python.org/downloads/) and [FFmpeg](https://ffmpeg.org/download.html#build-linux) installed on your computer. From your command line:

<!-- <img src="https://i.ibb.co/8DkzXZn/image.png" alt="image" border="0"> -->

<be>

</div>

  ```bash
# Clone this repository
$ git clone https://github.com/Michele0303/tiktok-live-recorder
# Go into the repository
$ cd tiktok-live-recorder
# Go into the source code
$ cd src
# Install dependencies
$ pip install -r requirements.txt --break-system-packages
# Run the app on linux
$ python3 main.py -h
  ```

## Install on Android 📱

<b>Install Termux from F-Droid:</b> <a href="https://f-droid.org/packages/com.termux/">HERE</a> - Avoid installing from Play Store to prevent potential issues.

From termux command line:

<be>

</div>

  ```bash
# Update packages
$ pkg update
$ pkg upgrade
# Install git, python3, ffmpeg
$ pkg install git python3 ffmpeg
# Clone this repository
$ git clone https://github.com/Michele0303/tiktok-live-recorder
# Go into the repository
$ cd tiktok-live-recorder
# Go into the source code
$ cd src
# Install dependencies
$ pip install -r requirements.txt --break-system-packages
# Run the app
$ python main.py -h
  ```

<div align="left">

## Docker
TikTok Live Recorder can easily be run using Docker.  
The example below saves recordings into a local `./output` folder (created if it doesn’t exist):

```bash
$ sudo docker run \
  -v ./output:/output \
  michele0303/tiktok-live-recorder:latest \
  -output /output \
  -user <username>
```

## Guide

- <a href="https://github.com/Michele0303/tiktok-live-recorder/blob/main/docs/GUIDE.md#how-to-set-cookies">How to set cookies in cookies.json</a>
- <a href="https://github.com/Michele0303/tiktok-live-recorder/blob/main/docs/GUIDE.md#how-to-get-room_id">How to get room_id</a>
- <a href="https://github.com/Michele0303/tiktok-live-recorder/blob/main/docs/GUIDE.md#how-to-enable-upload-to-telegram">How to enable upload to telegram</a>

## To-Do List 🔮

- [x] <b>Automatic Recording</b>: Enable automatic recording of live TikTok sessions.
- [x] <b>Authentication:</b> Added support for cookies-based authentication.
- [x] <b>Recording by room_id:</b> Allow recording by providing the room ID.
- [x] <b>Recording by TikTok live URL:</b> Enable recording by directly using the TikTok live URL.
- [x] <b>Using a Proxy to Bypass Login Restrictions:</b> Implement the ability to use an HTTP proxy to bypass login restrictions in some countries (only to obtain the room ID).
- [x] <b>Implement a Logging System:</b> Set up a comprehensive logging system to track activities and errors.
- [x] <b>Implement Auto-Update Feature:</b> Create a system that automatically checks for new releases.
- [x] <b>Send Recorded Live Streams to Telegram:</b> Enable the option to send recorded live streams directly to Telegram.
- [ ] <b>Save Chat in a File:</b> Allow saving the chat from live streams in a file.
- [ ] <b>Support for M3U8:</b> Add support for recording live streams via m3u8 format.
- [ ] <b>Watchlist Feature:</b> Implement a watchlist to monitor multiple users simultaneously (while respecting TikTok's limitations).

## Legal ⚖️

This code is in no way affiliated with, authorized, maintained, sponsored or endorsed by TikTok or any of its affiliates or subsidiaries. Use at your own risk.
