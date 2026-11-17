import requests

from http_utils import http_client
from http_utils.http_client import HttpClient


def _termux_client(monkeypatch):
    calls = []

    def fake_request(self, method, url, **kwargs):
        calls.append(kwargs.get("timeout"))

    monkeypatch.setattr(http_client, "is_termux", lambda: True)
    monkeypatch.setattr(requests.Session, "request", fake_request)
    return HttpClient().req, calls


def test_requests_session_gets_default_timeout(monkeypatch):
    session, calls = _termux_client(monkeypatch)

    session.get("https://www.tiktok.com/live")

    assert calls == [(10, 30)]


def test_explicit_timeout_still_wins(monkeypatch):
    session, calls = _termux_client(monkeypatch)

    session.get("https://tikrec.com/sign", timeout=10)

    assert calls == [10]
