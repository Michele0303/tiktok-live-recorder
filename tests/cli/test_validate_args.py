import sys

import pytest


from utils.args_handler import validate_and_parse_args
from utils.custom_exceptions import ArgsParseError
from utils.enums import Mode


def test_manual_mode_valid_with_user(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["tiktok-live-recorder", "-mode", "manual", "-user", "test"]
    )
    args, mode = validate_and_parse_args()
    assert args.user == "test"
    assert mode == Mode.MANUAL


def test_automatic_mode_valid_with_user(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["tiktok-live-recorder", "-mode", "automatic", "-user", "test"]
    )
    args, mode = validate_and_parse_args()
    assert args.user == "test"
    assert mode == Mode.AUTOMATIC


def test_followers_mode_valid_with_user(monkeypatch):
    # User input is not required for followers mode
    monkeypatch.setattr(
        sys, "argv", ["tiktok-live-recorder", "-mode", "followers", "-user", "test"]
    )
    args, mode = validate_and_parse_args()
    assert args.user == "test"
    assert mode == Mode.FOLLOWERS


def test_manual_mode_valid_without_user(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tiktok-live-recorder", "-mode", "manual"])
    with pytest.raises(
        ArgsParseError,
        match="Missing URL, username, or room ID. Please provide one of these parameters.",
    ):
        validate_and_parse_args()  # Should not raise an exception


def test_automatic_mode_valid_without_user(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tiktok-live-recorder", "-mode", "automatic"])
    with pytest.raises(
        ArgsParseError,
        match="Missing URL, username, or room ID. Please provide one of these parameters.",
    ):
        validate_and_parse_args()


def test_followers_mode_valid_without_user(monkeypatch):
    # User input is not required for followers mode
    monkeypatch.setattr(sys, "argv", ["tiktok-live-recorder", "-mode", "followers"])
    _, mode = validate_and_parse_args()  # Should not raise an exception
    assert mode == Mode.FOLLOWERS


def test_invalid_mode(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["tiktok-live-recorder", "-mode", "x", "-user", "test"]
    )
    with pytest.raises(
        ArgsParseError,
        match="Incorrect mode value. Choose between 'manual', 'automatic' or 'followers'.",
    ):
        validate_and_parse_args()  # Should raise an ArgsParseError for unknown mode
