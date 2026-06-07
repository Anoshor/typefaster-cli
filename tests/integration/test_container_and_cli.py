"""Integration tests for the composition root and CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from typefaster.cli import app
from typefaster.domain.models import RaceKind
from typefaster.domain.typing_engine import TypingEngine
from typefaster.services.container import build_app

runner = CliRunner()


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("TYPEFASTER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("TYPEFASTER_CONFIG_DIR", str(tmp_path / "cfg"))
    return tmp_path


def test_build_app_wires_services(env: Path) -> None:
    application = build_app()
    try:
        assert application.profile.get().display_name == "you"
        assert application.settings.default_time in (30, 60, 120)
    finally:
        application.close()


def test_profile_repair(env: Path) -> None:
    application = build_app()
    try:
        setup = application.race.prepare(kind=RaceKind.QUOTE)
        eng = TypingEngine(setup.target_text)
        for i, ch in enumerate(setup.target_text):
            eng.type_char(ch, i * 40)
        application.race.finish(setup, eng.result(60_000, kind=RaceKind.QUOTE))
        repaired = application.profile.repair()
        assert repaired.races_played == 1
    finally:
        application.close()


def test_daily_service(env: Path) -> None:
    application = build_app()
    try:
        challenge = application.daily.today()
        assert challenge.quote.text
        assert application.daily.leaderboard() == []
    finally:
        application.close()


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "typefaster" in result.stdout


def test_cli_stats_empty(env: Path) -> None:
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Races played" in result.stdout


def test_cli_history_empty(env: Path) -> None:
    result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "No races yet" in result.stdout


def test_cli_profile(env: Path) -> None:
    result = runner.invoke(app, ["profile"])
    assert result.exit_code == 0
    assert "Profile" in result.stdout


def test_cli_race_invalid_time(env: Path) -> None:
    result = runner.invoke(app, ["race", "--mode", "time", "--time", "45"])
    assert result.exit_code != 0


def test_cli_race_invalid_ghost(env: Path) -> None:
    result = runner.invoke(app, ["race", "--ghost", "bogus"])
    assert result.exit_code != 0


def test_cli_race_invalid_mode(env: Path) -> None:
    result = runner.invoke(app, ["race", "--mode", "bogus"])
    assert result.exit_code != 0
