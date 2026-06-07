"""Integration tests for the race + ghost services."""

from __future__ import annotations

import pytest

from typefaster.domain.errors import GhostUnavailableError
from typefaster.domain.models import GhostKind, RaceKind
from typefaster.domain.typing_engine import TypingEngine
from typefaster.services.ghost_service import GhostService
from typefaster.services.race_service import RaceService


def _play(text: str, *, t_step: int = 50) -> TypingEngine:
    eng = TypingEngine(text)
    t = 0
    for ch in text:
        eng.type_char(ch, t)
        t += t_step
    return eng


def _quote_result(eng: TypingEngine, elapsed: int = 60_000):  # type: ignore[no-untyped-def]
    return eng.result(elapsed, kind=RaceKind.QUOTE, mode_seconds=0)


def test_prepare_and_finish_persists(repo) -> None:  # type: ignore[no-untyped-def]
    svc = RaceService(repo)
    setup = svc.prepare(kind=RaceKind.QUOTE)
    eng = _play(setup.target_text)
    summary = svc.finish(setup, _quote_result(eng))

    assert summary.race_id > 0
    assert summary.new_personal_best is True
    assert repo.count_races() == 1


def test_ghost_unavailable_before_any_race(repo) -> None:  # type: ignore[no-untyped-def]
    ghosts = GhostService(repo)
    with pytest.raises(GhostUnavailableError):
        ghosts.load(GhostKind.PERSONAL_BEST)
    assert ghosts.try_load(GhostKind.LAST) is None


def test_ghost_available_after_race_and_matches_quote(repo) -> None:  # type: ignore[no-untyped-def]
    svc = RaceService(repo)
    setup = svc.prepare(kind=RaceKind.QUOTE)
    eng = _play(setup.target_text)
    svc.finish(setup, _quote_result(eng))

    ghosts = GhostService(repo)
    pb = ghosts.load(GhostKind.PERSONAL_BEST)
    assert pb.kind is GhostKind.PERSONAL_BEST
    assert pb.timeline[-1].progress_pct == 100.0
    # The ghost carries the exact quote it was recorded on.
    assert pb.quote is not None
    assert pb.quote.text == setup.target_text


def test_ghost_race_uses_ghosts_quote(repo) -> None:  # type: ignore[no-untyped-def]
    svc = RaceService(repo)
    first = svc.prepare(kind=RaceKind.QUOTE)
    svc.finish(first, _quote_result(_play(first.target_text)))

    # A subsequent ghost race must use the SAME text as the ghost.
    second = svc.prepare(kind=RaceKind.QUOTE, ghost_kind=GhostKind.PERSONAL_BEST)
    assert second.ghost is not None
    assert second.target_text == second.ghost.quote.text


def test_prepare_with_ghost_returns_none_when_no_history(repo) -> None:  # type: ignore[no-untyped-def]
    svc = RaceService(repo)
    setup = svc.prepare(kind=RaceKind.QUOTE, ghost_kind=GhostKind.PERSONAL_BEST)
    assert setup.ghost is None  # graceful: first race has no ghost
    assert setup.target_text  # still got a random quote to type


def test_time_mode_has_long_text_and_no_ghost(repo) -> None:  # type: ignore[no-untyped-def]
    from typefaster.domain.models import RaceMode

    svc = RaceService(repo)
    setup = svc.prepare(kind=RaceKind.TIME, mode=RaceMode.NORMAL)
    assert setup.kind is RaceKind.TIME
    assert setup.ghost is None
    # Enough text to not run out at 60s for a fast typist.
    assert len(setup.target_text) > 1000


def test_daily_setup_uses_daily_quote(repo) -> None:  # type: ignore[no-untyped-def]
    svc = RaceService(repo)
    setup = svc.prepare(kind=RaceKind.QUOTE, daily=True)
    assert setup.is_daily is True
