"""Headless Textual pilot smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from typefaster.domain.models import RaceKind, RaceMode
from typefaster.services.container import build_app
from typefaster.services.race_service import RaceConfig
from typefaster.ui.app import TypefasterApp
from typefaster.ui.screens.account import AccountScreen
from typefaster.ui.screens.coach import CoachScreen
from typefaster.ui.screens.lobby_browser import LobbyBrowserScreen
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


async def test_open_account_panel(services) -> None:  # type: ignore[no-untyped-def]
    app = TypefasterApp(services=services)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.open("account")
        await pilot.pause()
        assert isinstance(app.screen, AccountScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, MainMenu)


async def test_open_coach_panel(services) -> None:  # type: ignore[no-untyped-def]
    app = TypefasterApp(services=services)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.open("coach")
        await pilot.pause()
        assert isinstance(app.screen, CoachScreen)  # renders empty state on a fresh DB
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, MainMenu)


async def test_coach_panel_renders_with_data(services) -> None:  # type: ignore[no-untyped-def]
    # Seed enough per-key data so the coach renders the full report (most-missed
    # table + heatmap), not the empty state.
    from typefaster.domain.models import Quote, RaceKind, RaceResult, ReplayPoint

    services.repo.save_race(
        result=RaceResult(
            wpm=60.0,
            raw_wpm=65.0,
            accuracy=0.9,
            correct_chars=90,
            incorrect_chars=10,
            progress=1.0,
            duration_ms=60_000,
            mode_seconds=0,
            kind=RaceKind.QUOTE,
            timeline=[ReplayPoint(0, 0.0), ReplayPoint(60_000, 100.0)],
            key_stats={"a": (40, 12), "s": (30, 1), "f": (25, 0)},
        ),
        quote=Quote(ext_id="seed", text="seed text", source="t"),
        started_at="2026-06-07T10:00:00",
    )
    assert services.coach.enough_data() is True

    app = TypefasterApp(services=services)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.open("coach")
        await pilot.pause()
        assert isinstance(app.screen, CoachScreen)


async def test_coach_drill_launches_race(services) -> None:  # type: ignore[no-untyped-def]
    from typefaster.domain.models import Quote, RaceKind, RaceResult, ReplayPoint

    services.repo.save_race(
        result=RaceResult(
            wpm=60.0,
            raw_wpm=65.0,
            accuracy=0.9,
            correct_chars=90,
            incorrect_chars=10,
            progress=1.0,
            duration_ms=60_000,
            mode_seconds=0,
            kind=RaceKind.QUOTE,
            timeline=[ReplayPoint(0, 0.0), ReplayPoint(60_000, 100.0)],
            key_stats={"a": (40, 12), "s": (30, 1), "f": (25, 0)},
        ),
        quote=Quote(ext_id="seed", text="seed text", source="t"),
        started_at="2026-06-07T10:00:00",
    )
    app = TypefasterApp(services=services)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.open("coach")
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        assert isinstance(app.screen, RaceScreen)


async def test_open_online_lobby_panel(services) -> None:  # type: ignore[no-untyped-def]
    app = TypefasterApp(services=services)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.open("online")
        await pilot.pause()
        assert isinstance(app.screen, LobbyBrowserScreen)
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
