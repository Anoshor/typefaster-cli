"""Headless Textual pilot smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from typefaster.domain.models import RaceKind, RaceMode
from typefaster.services.container import build_app
from typefaster.services.race_service import RaceConfig
from typefaster.ui.app import TypefasterApp
from typefaster.ui.screens.main_menu import MainMenu
from typefaster.ui.screens.race import RaceScreen
from typefaster.ui.screens.stats import StatsScreen

pytestmark = pytest.mark.ui


@pytest.fixture
def services(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("TYPEFASTER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("TYPEFASTER_CONFIG_DIR", str(tmp_path / "cfg"))
    s = build_app()
    yield s
    s.close()


async def test_app_boots_to_menu(services) -> None:  # type: ignore[no-untyped-def]
    app = TypefasterApp(services=services)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, MainMenu)


async def test_open_stats_panel(services) -> None:  # type: ignore[no-untyped-def]
    app = TypefasterApp(services=services)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.open("stats")
        await pilot.pause()
        assert isinstance(app.screen, StatsScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, MainMenu)


async def test_initial_race_mounts_race_screen(services) -> None:  # type: ignore[no-untyped-def]
    app = TypefasterApp(
        services=services,
        initial_race=RaceConfig(kind=RaceKind.TIME, mode=RaceMode.SHORT),
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, RaceScreen)
