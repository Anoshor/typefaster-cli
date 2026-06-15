"""Unit tests for the client networking helpers."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

import typefaster.net.api as api_mod
from typefaster.net.api import ApiClient, ws_url
from typefaster.net.token_store import DEFAULT_SERVER_URL, Session


def test_session_defaults(tmp_path: Path) -> None:
    s = Session.load(tmp_path / "auth.json")
    assert s.server_url.startswith("http")
    assert not s.logged_in


def test_session_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    s = Session.load(path)
    s.token = "abc"
    s.username = "alice"
    s.save(path)
    again = Session.load(path)
    assert again.logged_in
    assert again.username == "alice"


def test_session_clear(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    s = Session(token="x", username="bob")
    s.save(path)
    s.clear(path)
    assert not Session.load(path).logged_in


def test_session_heals_ephemeral_tunnel_url(tmp_path: Path) -> None:
    """A dead Cloudflare quick-tunnel URL is reset to the default on load."""
    path = tmp_path / "auth.json"
    Session(server_url="https://sectors-trend.trycloudflare.com", token="t").save(path)
    healed = Session.load(path)
    assert healed.server_url == DEFAULT_SERVER_URL
    assert healed.token == "t"  # token is preserved
    # The reset is persisted, so it survives the next load too.
    assert Session.load(path).server_url == DEFAULT_SERVER_URL


def test_session_keeps_custom_host(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    Session(server_url="https://play.example.com").save(path)
    assert Session.load(path).server_url == "https://play.example.com"


def _mock_httpx(monkeypatch: pytest.MonkeyPatch, dead_host: str) -> None:
    """Route all ApiClient httpx clients through a transport that fails for
    ``dead_host`` and returns 200 for anything else."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == dead_host:
            raise httpx.ConnectError("dns failure", request=request)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        api_mod.httpx, "Client", lambda **kw: real_client(transport=transport, **kw)
    )


def test_request_fails_over_to_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TYPEFASTER_CONFIG_DIR", str(tmp_path))
    _mock_httpx(monkeypatch, dead_host="dead.example.com")
    session = Session(server_url="https://dead.example.com")
    with ApiClient(session) as client:
        result = client._request("GET", "/auth/me")
    assert result == {"ok": True}
    assert client.failed_over is True
    assert session.server_url == DEFAULT_SERVER_URL
    # Persisted, so the next launch starts on the default.
    assert Session.load(tmp_path / "auth.json").server_url == DEFAULT_SERVER_URL


def test_request_does_not_fail_over_reachable_custom_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TYPEFASTER_CONFIG_DIR", str(tmp_path))
    _mock_httpx(monkeypatch, dead_host="never.example.com")
    session = Session(server_url="https://custom.example.com")
    with ApiClient(session) as client:
        client._request("GET", "/x")
    assert client.failed_over is False
    assert session.server_url == "https://custom.example.com"


def test_ws_url_http_to_ws() -> None:
    assert ws_url("http://localhost:8000", "ABC123", "tok") == (
        "ws://localhost:8000/ws/lobby/ABC123?token=tok"
    )


def test_ws_url_https_to_wss() -> None:
    assert ws_url("https://play.example.com/", "XY", "t").startswith("wss://play.example.com/ws/")
