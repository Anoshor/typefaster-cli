"""Daily-challenge streak computation."""

from __future__ import annotations

from datetime import date

from typefaster.domain.models import Quote, RaceKind, RaceResult, ReplayPoint
from typefaster.infra.sqlite_repository import SQLiteRepository
from typefaster.services.daily_service import DailyService


def _play_daily(repo: SQLiteRepository, quote: Quote, day: str) -> None:
    repo.save_race(
        result=RaceResult(
            wpm=60.0,
            raw_wpm=65.0,
            accuracy=0.95,
            correct_chars=90,
            incorrect_chars=5,
            progress=1.0,
            duration_ms=60_000,
            mode_seconds=0,
            kind=RaceKind.QUOTE,
            timeline=[ReplayPoint(0, 0.0), ReplayPoint(60_000, 100.0)],
        ),
        quote=quote,
        started_at=f"{day}T10:00:00+00:00",
        is_daily=True,
    )


def test_streak_zero_when_never_played(repo: SQLiteRepository) -> None:
    assert DailyService(repo).streak(date(2026, 6, 10)) == 0


def test_streak_counts_consecutive_days(repo: SQLiteRepository, quote: Quote) -> None:
    for day in ("2026-06-08", "2026-06-09", "2026-06-10"):
        _play_daily(repo, quote, day)
    assert DailyService(repo).streak(date(2026, 6, 10)) == 3


def test_streak_alive_when_today_unplayed(repo: SQLiteRepository, quote: Quote) -> None:
    # Played yesterday and the day before, not yet today → streak survives at 2.
    for day in ("2026-06-08", "2026-06-09"):
        _play_daily(repo, quote, day)
    assert DailyService(repo).streak(date(2026, 6, 10)) == 2


def test_streak_broken_by_gap(repo: SQLiteRepository, quote: Quote) -> None:
    for day in ("2026-06-06", "2026-06-07", "2026-06-09"):
        _play_daily(repo, quote, day)
    # 06-08 was skipped, so only 06-09 counts toward 06-10.
    assert DailyService(repo).streak(date(2026, 6, 10)) == 1
