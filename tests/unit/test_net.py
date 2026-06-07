"""Unit tests for the client networking helpers."""

from __future__ import annotations

from pathlib import Path

from typefaster.net.api import ws_url
from typefaster.net.token_store import Session


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


def test_ws_url_http_to_ws() -> None:
    assert ws_url("http://localhost:8000", "ABC123", "tok") == (
        "ws://localhost:8000/ws/lobby/ABC123?token=tok"
    )


def test_ws_url_https_to_wss() -> None:
    assert ws_url("https://play.example.com/", "XY", "t").startswith("wss://play.example.com/ws/")
