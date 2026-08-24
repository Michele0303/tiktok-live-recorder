from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _load_env_file(env_path: Path | str) -> dict[str, str]:
    """Parse a simple .env file without external dependencies."""
    env_vars: dict[str, str] = {}
    path = Path(env_path)
    if not path.is_file():
        return env_vars

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                # Remove surrounding quotes if present
                if (val.startswith('"') and val.endswith('"')) or (
                    val.startswith("'") and val.endswith("'")
                ):
                    val = val[1:-1]
                env_vars[key] = val
    return env_vars


@dataclass
class Settings:
    # Telegram Bot configuration
    telegram_bot_token: str
    telegram_allowed_user_id: int
    telegram_allowed_chat_id: int

    # Optional Telegram Bot API URLs (for self-hosted Local Bot API)
    telegram_bot_api_base_url: str | None = None
    telegram_bot_api_file_base_url: str | None = None

    # Infrastructure credentials (for Local Bot API container)
    telegram_api_id: str | None = None
    telegram_api_hash: str | None = None

    # Service behavior
    watch_interval_seconds: int = 30
    recording_path: str = "/data/recordings"
    database_path: str = "/data/watch.db"
    max_concurrent_recordings: int = 3
    max_recording_part_bytes: int = 1_932_735_283  # ~1.8 GB safe limit for 2GB Bot API
    delete_after_days: int = 0  # 0 means never auto-delete
    log_level: str = "INFO"

    # TikTok configuration
    tiktok_cookies_path: str | None = None
    tiktok_proxy: str | None = None
    ffmpeg_path: str = "ffmpeg"

    # Runtime attributes
    cookies: dict[str, Any] = field(default_factory=dict)

    def ensure_directories(self) -> None:
        """Ensure necessary storage and database parent directories exist."""
        rec_dir = Path(self.recording_path)
        rec_dir.mkdir(parents=True, exist_ok=True)

        db_dir = Path(self.database_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def load_cookies(self) -> dict[str, Any]:
        """Load cookies from configured path, /data/cookies.json, or src/cookies.json."""
        candidate_paths = []
        if self.tiktok_cookies_path:
            candidate_paths.append(Path(self.tiktok_cookies_path))
        candidate_paths.append(Path("/data/cookies.json"))
        candidate_paths.append(
            Path(__file__).resolve().parent.parent / "cookies.json"
        )

        for p in candidate_paths:
            if p.is_file():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            self.cookies = data
                            return data
                except Exception:
                    continue

        self.cookies = {}
        return self.cookies


def load_settings(env_file: Path | str | None = None) -> Settings:
    """Load and validate settings from environment variables and optional .env file."""
    file_vars: dict[str, str] = {}
    if env_file:
        file_vars = _load_env_file(env_file)
    else:
        # Check standard locations
        for default_env in (Path(".env"), Path("/data/.env")):
            if default_env.is_file():
                file_vars = _load_env_file(default_env)
                break

    def get_val(key: str, default: Any = None) -> Any:
        if key in os.environ:
            return os.environ[key]
        if key in file_vars:
            return file_vars[key]
        return default

    bot_token = get_val("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is required. Please set it in your environment or .env file."
        )

    user_id_raw = get_val("TELEGRAM_ALLOWED_USER_ID")
    if user_id_raw is None or str(user_id_raw).strip() == "":
        raise ValueError(
            "TELEGRAM_ALLOWED_USER_ID is required for access control."
        )
    try:
        allowed_user_id = int(str(user_id_raw).strip())
    except ValueError as err:
        raise ValueError(
            f"TELEGRAM_ALLOWED_USER_ID must be a valid integer ID, got: {user_id_raw}"
        ) from err

    chat_id_raw = get_val("TELEGRAM_ALLOWED_CHAT_ID")
    if chat_id_raw is None or str(chat_id_raw).strip() == "":
        raise ValueError(
            "TELEGRAM_ALLOWED_CHAT_ID is required for message delivery."
        )
    try:
        allowed_chat_id = int(str(chat_id_raw).strip())
    except ValueError as err:
        raise ValueError(
            f"TELEGRAM_ALLOWED_CHAT_ID must be a valid integer ID, got: {chat_id_raw}"
        ) from err

    api_base_url = get_val("TELEGRAM_BOT_API_BASE_URL")
    if api_base_url:
        api_base_url = api_base_url.strip() or None

    api_file_base_url = get_val("TELEGRAM_BOT_API_FILE_BASE_URL")
    if api_file_base_url:
        api_file_base_url = api_file_base_url.strip() or None

    api_id = get_val("TELEGRAM_API_ID")
    api_hash = get_val("TELEGRAM_API_HASH")

    watch_interval = int(get_val("WATCH_INTERVAL_SECONDS", 30))
    if watch_interval < 5:
        watch_interval = 5

    recording_path = get_val("RECORDING_PATH", "/data/recordings").strip()
    database_path = get_val("DATABASE_PATH", "/data/watch.db").strip()
    max_concurrent = int(get_val("MAX_CONCURRENT_RECORDINGS", 3))
    max_part_bytes = int(get_val("MAX_RECORDING_PART_BYTES", 1_932_735_283))
    delete_after_days = int(get_val("DELETE_AFTER_DAYS", 0))
    log_level = get_val("LOG_LEVEL", "INFO").upper().strip()

    cookies_path = get_val("TIKTOK_COOKIES_PATH")
    proxy = get_val("TIKTOK_PROXY")
    ffmpeg_path = get_val("FFMPEG_PATH", "ffmpeg")

    settings = Settings(
        telegram_bot_token=bot_token,
        telegram_allowed_user_id=allowed_user_id,
        telegram_allowed_chat_id=allowed_chat_id,
        telegram_bot_api_base_url=api_base_url,
        telegram_bot_api_file_base_url=api_file_base_url,
        telegram_api_id=api_id,
        telegram_api_hash=api_hash,
        watch_interval_seconds=watch_interval,
        recording_path=recording_path,
        database_path=database_path,
        max_concurrent_recordings=max_concurrent,
        max_recording_part_bytes=max_part_bytes,
        delete_after_days=delete_after_days,
        log_level=log_level,
        tiktok_cookies_path=cookies_path,
        tiktok_proxy=proxy,
        ffmpeg_path=ffmpeg_path,
    )
    settings.load_cookies()
    return settings
