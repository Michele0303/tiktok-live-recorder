from __future__ import annotations

from pathlib import Path

import pytest

from config.settings import Settings, _load_env_file, load_settings


def test_load_env_file_parses_content(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# Comment line\n"
        "TELEGRAM_BOT_TOKEN=token123\n"
        "TELEGRAM_ALLOWED_USER_ID=111222\n"
        'TELEGRAM_ALLOWED_CHAT_ID="333444"\n'
        "WATCH_INTERVAL_SECONDS=45\n",
        encoding="utf-8",
    )

    parsed = _load_env_file(env_file)
    assert parsed["TELEGRAM_BOT_TOKEN"] == "token123"
    assert parsed["TELEGRAM_ALLOWED_USER_ID"] == "111222"
    assert parsed["TELEGRAM_ALLOWED_CHAT_ID"] == "333444"
    assert parsed["WATCH_INTERVAL_SECONDS"] == "45"


def test_load_settings_success(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TELEGRAM_BOT_TOKEN=secret_bot_token\n"
        "TELEGRAM_ALLOWED_USER_ID=12345\n"
        "TELEGRAM_ALLOWED_CHAT_ID=67890\n"
        "WATCH_INTERVAL_SECONDS=40\n"
        "RECORDING_PATH=/tmp/test_rec\n"
        "DATABASE_PATH=/tmp/test_watch.db\n"
        "MAX_CONCURRENT_RECORDINGS=5\n"
        "DELETE_AFTER_DAYS=7\n",
        encoding="utf-8",
    )

    settings = load_settings(env_file)
    assert settings.telegram_bot_token == "secret_bot_token"
    assert settings.telegram_allowed_user_id == 12345
    assert settings.telegram_allowed_chat_id == 67890
    assert settings.watch_interval_seconds == 40
    assert settings.recording_path == "/tmp/test_rec"
    assert settings.database_path == "/tmp/test_watch.db"
    assert settings.max_concurrent_recordings == 5
    assert settings.delete_after_days == 7


def test_load_settings_missing_token_raises():
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN is required"):
        load_settings(Path("/non/existent/env"))


def test_load_settings_missing_user_id_raises(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "valid_token")
    monkeypatch.delenv("TELEGRAM_ALLOWED_USER_ID", raising=False)
    with pytest.raises(ValueError, match="TELEGRAM_ALLOWED_USER_ID is required"):
        load_settings(Path("/non/existent/env"))


def test_load_settings_invalid_user_id_raises(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "valid_token")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_ID", "not_a_number")
    with pytest.raises(ValueError, match="must be a valid integer"):
        load_settings(Path("/non/existent/env"))


def test_settings_ensure_directories(tmp_path: Path):
    rec_dir = tmp_path / "rec" / "nested"
    db_file = tmp_path / "db" / "watch.db"
    settings = Settings(
        telegram_bot_token="tok",
        telegram_allowed_user_id=1,
        telegram_allowed_chat_id=1,
        recording_path=str(rec_dir),
        database_path=str(db_file),
    )
    settings.ensure_directories()
    assert rec_dir.is_dir()
    assert db_file.parent.is_dir()
