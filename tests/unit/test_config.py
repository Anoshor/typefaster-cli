"""Unit tests for settings persistence."""

from __future__ import annotations

from pathlib import Path

from typefaster.infra.config import Settings


def test_defaults(tmp_path: Path) -> None:
    s = Settings.load(tmp_path / "settings.json")
    assert s.default_time == 60
    assert s.allow_backspace is True
    assert (tmp_path / "settings.json").exists()  # created on first load


def test_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    s = Settings.load(path)
    s.theme = "light"
    s.allow_backspace = False
    s.save(path)
    again = Settings.load(path)
    assert again.theme == "light"
    assert again.allow_backspace is False


def test_corrupt_file_falls_back(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    s = Settings.load(path)
    assert s.default_time == 60
