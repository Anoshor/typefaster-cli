"""Regression tests for race timing.

Guards against the bug where the un-stopped countdown timer re-ran ``_begin``
every second and reset the start time, producing absurd WPM (e.g. 2222), and
verifies the clock starts on the first keystroke (MonkeyType/TypeRacer style).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from textual.app import App

import typefaster.ui.screens.race as racemod
from typefaster.domain.models import Quote, RaceKind, RaceMode
from typefaster.infra.clock import FakeClock
from typefaster.services.race_service import RaceSetup
from typefaster.ui.screens.race import RaceScreen

pytestmark = pytest.mark.ui


def _setup() -> RaceSetup:
    return RaceSetup(
        quote=Quote(ext_id="t1", text="ab cd", source="test"),
        target_text="ab cd",
        kind=RaceKind.QUOTE,
        mode=RaceMode.NORMAL,
        ghost=None,
        allow_backspace=True,
        is_daily=False,
        started_at=datetime.now(UTC).isoformat(),
    )


async def test_clock_starts_on_first_keystroke_and_wpm_is_sane(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(racemod, "_COUNTDOWN_FROM", 1)
    fake = FakeClock()
    captured: dict[str, object] = {}

    class Host(App[None]):
        def on_mount(self) -> None:
            self.push_screen(
                RaceScreen(_setup(), clock=fake), lambda r: captured.__setitem__("result", r)
            )

    app = Host()
    async with app.run_test() as pilot:
        await asyncio.sleep(1.2)  # let the 1s countdown elapse and _begin run once
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, RaceScreen)

        # Before any key, the clock has not started.
        assert screen._start_ms is None

        # Type "ab cd", advancing 3s of (fake) time per character → 12s total.
        for ch in "ab cd":
            await pilot.press("space" if ch == " " else ch)
            fake.advance(3000)
        await pilot.pause()

    result = captured["result"]
    assert result is not None
    # 5 chars = 1 word over 12s → 5 WPM. The bug produced thousands.
    assert result.duration_ms == 12_000
    assert result.wpm == pytest.approx(5.0, abs=0.5)
    assert not result.suspicious


async def test_begin_is_idempotent(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Re-invoking _begin (as the buggy countdown timer did) must not reset the
    start time once typing has begun."""
    monkeypatch.setattr(racemod, "_COUNTDOWN_FROM", 1)
    fake = FakeClock(start_ms=5_000)

    class Host(App[None]):
        def on_mount(self) -> None:
            self.push_screen(RaceScreen(_setup(), clock=fake))

    app = Host()
    async with app.run_test() as pilot:
        await asyncio.sleep(1.2)
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, RaceScreen)

        await pilot.press("a")  # first keystroke starts the clock
        start = screen._start_ms
        assert start == 5_000

        fake.advance(10_000)
        screen._begin()  # simulate the old repeated-begin bug
        assert screen._start_ms == start  # NOT reset
