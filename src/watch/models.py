from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from typing import Any

from core.tiktok_recorder import TikTokRecorder


@dataclass
class ActiveJob:
    username: str
    room_id: str | None
    recording_id: int
    recorder: TikTokRecorder
    stop_event: threading.Event
    started_at: str
    is_one_off: bool = False
    task: asyncio.Task[Any] | None = None
