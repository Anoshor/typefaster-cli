"""Integration tests for the stats service."""

from __future__ import annotations

from typefaster.domain.models import Quote, RaceResult, ReplayPoint
from typefaster.services.stats_service import StatsService


def _res(wpm: float) -> RaceResult:
    return RaceResult(
        wpm=wpm,
        raw_wpm=wpm,
        accuracy=0.95,
        correct_chars=50,
        incorrect_chars=2,
        progress=1.0,
        duration_ms=60_000,
        mode_seconds=0,
        timeline=[ReplayPoint(0, 0.0), ReplayPoint(60_000, 100.0)],
    )


def test_summary_aggregates(repo, quote: Quote) -> None:  # type: ignore[no-untyped-def]
    for i, wpm in enumerate([40.0, 60.0, 80.0]):
        repo.save_race(result=_res(wpm), quote=quote, started_at=f"2026-06-07T1{i}:00:00")
    svc = StatsService(repo)
    summary = svc.summary()
    assert summary.profile.races_played == 3
    assert summary.profile.best_wpm == 80.0
    assert summary.avg_wpm == 60.0
    assert len(summary.recent_wpm) == 3


def test_history_pages(repo, quote: Quote) -> None:  # type: ignore[no-untyped-def]
    for i in range(25):
        repo.save_race(result=_res(50.0), quote=quote, started_at=f"2026-06-07T10:{i:02d}:00")
    svc = StatsService(repo)
    assert svc.history_pages(page_size=20) == 2


def test_top_quote_runs_sorted(repo, quote: Quote) -> None:  # type: ignore[no-untyped-def]
    for wpm in [55.0, 75.0, 65.0]:
        repo.save_race(result=_res(wpm), quote=quote, started_at="2026-06-07T10:00:00")
    svc = StatsService(repo)
    runs = svc.top_quote_runs(limit=3)
    assert [r.wpm for r in runs] == [75.0, 65.0, 55.0]


def test_summary_separates_modes(repo, quote: Quote) -> None:  # type: ignore[no-untyped-def]
    from typefaster.domain.models import RaceKind

    # one quote run, one time run
    repo.save_race(result=_res(70.0), quote=quote, started_at="2026-06-07T10:00:00")
    time_res = RaceResult(
        wpm=95.0,
        raw_wpm=99.0,
        accuracy=0.96,
        correct_chars=400,
        incorrect_chars=5,
        progress=1.0,
        duration_ms=60_000,
        mode_seconds=60,
        kind=RaceKind.TIME,
        timeline=[ReplayPoint(0, 0.0)],
    )
    repo.save_race(result=time_res, quote=quote, started_at="2026-06-07T10:05:00")
    summary = StatsService(repo).summary()
    assert summary.quote_best_wpm == 70.0
    assert summary.time_best_by_mode.get(60) == 95.0
