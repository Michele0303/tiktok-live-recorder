import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils import dependencies  # noqa: E402


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout=b""):
        self.returncode = returncode
        self.stdout = stdout


def test_check_ffmpeg_binary_accepts_valid_binary(monkeypatch):
    monkeypatch.setattr(
        dependencies.subprocess,
        "run",
        lambda *args, **kwargs: FakeCompletedProcess(
            0, b"ffmpeg version 7.0.1 Copyright (c) 2000-2026"
        ),
    )
    assert dependencies.check_ffmpeg_binary("/custom/ffmpeg") is True


def test_check_ffmpeg_binary_rejects_non_ffmpeg_executable(monkeypatch):
    monkeypatch.setattr(
        dependencies.subprocess,
        "run",
        lambda *args, **kwargs: FakeCompletedProcess(0, b"Python 3.13.14"),
    )
    assert dependencies.check_ffmpeg_binary("/custom/python") is False


def test_check_ffmpeg_binary_rejects_nonzero_exit(monkeypatch):
    monkeypatch.setattr(
        dependencies.subprocess,
        "run",
        lambda *args, **kwargs: FakeCompletedProcess(1, b"ffmpeg version 7.0.1"),
    )
    assert dependencies.check_ffmpeg_binary("ffmpeg") is False


def test_check_ffmpeg_binary_handles_missing_file(monkeypatch):
    def raise_missing(*args, **kwargs):
        raise FileNotFoundError("no such file")

    monkeypatch.setattr(dependencies.subprocess, "run", raise_missing)
    assert dependencies.check_ffmpeg_binary("/missing/ffmpeg") is False


def test_check_ffmpeg_binary_handles_invalid_executable(monkeypatch):
    def raise_invalid(*args, **kwargs):
        raise PermissionError("permission denied")

    monkeypatch.setattr(dependencies.subprocess, "run", raise_invalid)
    assert dependencies.check_ffmpeg_binary("/broken/ffmpeg") is False


def test_check_ffmpeg_binary_handles_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=10)

    monkeypatch.setattr(dependencies.subprocess, "run", raise_timeout)
    assert dependencies.check_ffmpeg_binary("ffmpeg") is False


def test_check_ffmpeg_with_custom_path_exits_without_install_hint(monkeypatch):
    monkeypatch.setattr(dependencies, "check_ffmpeg_binary", lambda path: False)
    install_calls = []
    monkeypatch.setattr(
        dependencies, "install_ffmpeg_binary", lambda: install_calls.append(True)
    )

    with pytest.raises(SystemExit):
        dependencies.check_ffmpeg("/custom/ffmpeg")

    assert install_calls == []


def test_check_ffmpeg_without_custom_path_suggests_install(monkeypatch):
    monkeypatch.setattr(dependencies, "check_ffmpeg_binary", lambda path: False)
    install_calls = []
    monkeypatch.setattr(
        dependencies, "install_ffmpeg_binary", lambda: install_calls.append(True)
    )

    dependencies.check_ffmpeg()

    assert install_calls == [True]


def test_check_ffmpeg_accepts_valid_custom_path(monkeypatch):
    monkeypatch.setattr(dependencies, "check_ffmpeg_binary", lambda path: True)
    install_calls = []
    monkeypatch.setattr(
        dependencies, "install_ffmpeg_binary", lambda: install_calls.append(True)
    )

    dependencies.check_ffmpeg("/custom/ffmpeg")

    assert install_calls == []
