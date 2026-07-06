import sys

import pytest


from utils.args_handler import validate_and_parse_args
from utils.custom_exceptions import ArgsParseError


def test_validate_mode(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["tiktok-live-recorder", "-mode", "manual", "-user", "test"]
    )
    validate_and_parse_args()  # Should not raise an exception

    monkeypatch.setattr(
        sys, "argv", ["tiktok-live-recorder", "-mode", "automatic", "-user", "test"]
    )
    validate_and_parse_args()  # Should not raise an exception

    monkeypatch.setattr(
        sys, "argv", ["tiktok-live-recorder", "-mode", "followers", "-user", "test"]
    )
    validate_and_parse_args()  # Should not raise an exception

    # Test for invalid mode
    monkeypatch.setattr(
        sys, "argv", ["tiktok-live-recorder", "-mode", "x", "-user", "test"]
    )
    with pytest.raises(
        ArgsParseError,
        match="Incorrect mode value. Choose between 'manual', 'automatic' or 'followers'.",
    ):
        validate_and_parse_args()  # Should raise an exception for unknown mode
