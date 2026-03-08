from dataclasses import dataclass

from utils.enums import Mode


@dataclass
class RecorderConfig:
    mode: Mode
    url: str | None = None
    user: str | None = None
    room_id: str | None = None
    automatic_interval: int = 5
    cookies: dict | None = None
    proxy: str | None = None
    output: str | None = None
    duration: int | None = None
    use_telegram: bool = False
    bitrate: str | None = None
    tikrec_url: str | None = None
