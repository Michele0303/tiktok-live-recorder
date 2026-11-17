import pytest
from curl_cffi.requests.exceptions import ConnectionError as CurlConnectionError
from curl_cffi.requests.exceptions import Timeout as CurlTimeout
from requests import ConnectionError as RequestsConnectionError

import core.tiktok_recorder as recorder
from utils.custom_exceptions import (
    TikRecUnavailableError,
    TikTokRecorderError,
    UserLiveError,
)
from utils.enums import TikTokError


@pytest.fixture
def hints(monkeypatch):
    monkeypatch.setattr(recorder, "_proxy_hint_shown", False)
    shown = []
    monkeypatch.setattr(recorder.logger, "info", lambda msg: shown.append(msg))
    return shown


@pytest.mark.parametrize(
    "error",
    [
        TikTokRecorderError(TikTokError.COUNTRY_BLACKLISTED),
        TikTokRecorderError(TikTokError.COUNTRY_BLACKLISTED_AUTO_MODE),
        UserLiveError(TikTokError.WAF_BLOCKED),
        RequestsConnectionError("timed out"),
        CurlConnectionError("curl: (7) Failed to connect"),
        CurlTimeout("curl: (28) Operation timed out"),
    ],
)
def test_hint_shown_once_for_ip_errors(hints, error):
    recorder.proxy_hint(None, error)
    recorder.proxy_hint(None, error)

    assert len(hints) == 2
    assert "-proxy" in hints[0]
    assert "Sponsored" in hints[1] and "TIKTOKREC" in hints[1]


def test_hint_skipped_when_proxy_set(hints):
    recorder.proxy_hint("http://1.2.3.4:8080", UserLiveError(TikTokError.WAF_BLOCKED))
    assert hints == []


def test_hint_skipped_for_unrelated_errors(hints):
    recorder.proxy_hint(None, UserLiveError(TikTokError.USER_NOT_CURRENTLY_LIVE))
    recorder.proxy_hint(None, ValueError("boom"))
    assert hints == []


def _chained(outer, cause):
    try:
        raise outer from cause
    except Exception as error:
        return error


def test_hint_shown_for_wrapped_curl_error(hints):
    error = _chained(TikTokRecorderError("lookup failed"), CurlTimeout("timed out"))
    recorder.proxy_hint(None, error)
    assert len(hints) == 2


def test_hint_skipped_when_tikrec_is_down(hints):
    error = _chained(
        TikRecUnavailableError("TikRec could not resolve the RoomID"),
        CurlConnectionError("curl: (7) Failed to connect to tikrec.com"),
    )
    recorder.proxy_hint(None, error)
    assert hints == []
