# System Architecture & Design

This document details the architecture, component interactions, sequence flows, and state machines for the TikTok Live Recorder Telegram Watch Service.

---

## 1. High-Level System Architecture

```mermaid
flowchart TD
    User([Authorized Telegram User]) -->|/watch, /status, /record, /stop| Bot[Telegram Bot Application\npython-telegram-bot]
    Bot --> Auth{Authorization Layer\nUser & Chat ID Check}
    Auth -->|Authorized| WM[WatchManager]
    Auth -->|Unauthorized| Deny[Reject / Silent Drop]

    WM <-->|Read / Write Watch Targets & Recordings| DB[(SQLite Database\n/data/watch.db)]
    WM -->|Poll Live Status| TikTokAPI[TikTok Webcast API]
    
    WM -->|Spawn Recording Job| Worker[Recording Worker]
    Worker -->|Stream Capture| Recorder[TikTokRecorder Core]
    Recorder -->|Download Chunks| CDN[TikTok Live CDN]
    Recorder -->|Save Stream| Storage[(Persistent Storage\n/data/recordings/...)]
    
    Worker -->|Remux & Segment| FFmpeg[FFmpeg Engine]
    FFmpeg -->|MP4 Parts & metadata.json| Storage
    
    Worker -->|Deliver Video| Delivery[Telegram Delivery Service]
    Delivery -->|Send Video / Multipart| BotAPI[Telegram Bot API / Local Bot API]
    BotAPI -->|Push Media & Notifications| User
```

---

## 2. `/watch` Sequence Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Telegram User
    participant Bot as Telegram Bot
    participant Auth as Auth Layer
    participant WM as WatchManager
    participant DB as SQLite DB
    participant API as TikTokAPI
    participant Worker as RecordingWorker
    participant Delivery as Delivery Service

    User->>Bot: /watch @username
    Bot->>Auth: Verify user_id & chat_id
    Auth-->>Bot: Authorized
    Bot->>WM: watch("username")
    WM->>DB: add_or_enable_watch("username")
    WM->>API: check_live_status("username")
    
    alt User is currently Offline
        API-->>WM: is_live = False
        WM->>DB: update_watch_status(OFFLINE)
        WM-->>Bot: Return "Watching @username (Offline)"
        Bot-->>User: 👁 Watching @username (I'll auto-record their next LIVE)
    else User is already LIVE
        API-->>WM: is_live = True, room_id
        WM->>DB: update_watch_status(LIVE)
        WM->>DB: create_recording(STARTING)
        WM->>Worker: execute_recording_job() [Async Background Thread]
        WM-->>Bot: Return "🔴 @username is LIVE. Recording started."
        Bot-->>User: 🔴 @username is already LIVE. Recording is starting now.
        
        loop Stream Capture
            Worker->>API: Download stream chunks
        end
        
        Worker->>Worker: Stream ends / User stops
        Worker->>Worker: FFmpeg convert FLV -> MP4
        Worker->>Worker: Segment if > MAX_RECORDING_PART_BYTES
        Worker->>Worker: Generate metadata.json
        Worker->>DB: update_recording(UPLOADING)
        Worker->>Delivery: deliver_recording(parts)
        Delivery->>User: ✅ Recording complete (Duration, Size) + Video Part(s)
        Worker->>DB: update_recording(COMPLETE)
        Worker->>DB: update_watch_status(OFFLINE)
    end
```

---

## 3. Recording Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> WAITING: Target added to Watch List
    WAITING --> STARTING: LIVE detected by Polling / /record
    STARTING --> RECORDING: Worker spawned & Stream opened
    
    RECORDING --> RECORDING: Streaming chunks to disk
    RECORDING --> PROCESSING: Stream ended / /stop command / duration reached
    
    PROCESSING --> UPLOADING: MP4 remuxed, segmented & metadata written
    
    UPLOADING --> COMPLETE: Telegram upload succeeded
    UPLOADING --> FAILED: Telegram upload failed (Local file preserved)
    
    RECORDING --> STOPPED: Service restart / SIGTERM reconciliation
    PROCESSING --> STOPPED: Service restart reconciliation
    
    COMPLETE --> [*]
    FAILED --> [*]
    STOPPED --> [*]
```

---

## 4. Deployment Topology (Dokploy / Docker Compose)

```mermaid
flowchart LR
    subgraph Host["VPS Host (Dokploy)"]
        subgraph Net["Internal Docker Bridge (tiktok_recorder_network)"]
            RecContainer["tiktok-live-recorder\n(Python 3.13 + FFmpeg)"]
            BotAPIContainer["telegram-bot-api\n(Local Bot API Server)"]
        end
        
        subgraph Volumes["Persistent Docker Volumes"]
            DataVol[("tiktok_recorder_data\n(/data)\n• watch.db\n• recordings/")]
            ApiVol[("tiktok_telegram_bot_api_data\n(/var/lib/telegram-bot-api)")]
        end
    end

    RecContainer <-->|Internal HTTP on port 8081| BotAPIContainer
    RecContainer --- DataVol
    BotAPIContainer --- DataVol
    BotAPIContainer --- ApiVol
    
    BotAPIContainer <==>|HTTPS / Long Polling| TelegramCloud["Telegram Cloud Servers"]
    RecContainer <==>|HTTPS| TikTokCloud["TikTok Webcast & Stream CDN"]
```

---

## 5. Storage Partitioning Layout

Recordings are deterministically structured by creator and UTC date to prevent file collisions and keep directories manageable:

```text
/data/
├── watch.db                 # SQLite database file (WAL mode)
├── watch.db-wal
├── watch.db-shm
├── cookies.json             # Optional custom TikTok cookies
└── recordings/
    └── username/
        └── 2026/
            └── 08/
                └── 24/
                    └── username_2026-08-24_22-42-15/
                        ├── recording.mp4          # Final remuxed video (< 1.8 GB)
                        ├── metadata.json          # Recording metadata
                        ├── username_part_000.mp4   # If segmented (> 1.8 GB)
                        └── username_part_001.mp4
```
