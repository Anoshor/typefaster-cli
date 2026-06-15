"""Integration tests for the SQLite repository."""

from __future__ import annotations

from dataclasses import replace

from typefaster.domain.models import GhostKind, Quote, RaceKind, RaceResult, ReplayPoint
from typefaster.infra.sqlite_repository import SQLiteRepository


def _result(
    wpm: float = 60.0,
    *,
    ghost_won: bool | None = None,
    kind: RaceKind = RaceKind.QUOTE,
    mode_seconds: int = 0,
) -> RaceResult:
    return RaceResult(
        wpm=wpm,
        raw_wpm=wpm + 5,
        accuracy=0.97,
        correct_chars=100,
        incorrect_chars=3,
        progress=1.0,
        duration_ms=60_000,
        mode_seconds=mode_seconds,
        kind=kind,
        timeline=[ReplayPoint(0, 0.0), ReplayPoint(60_000, 100.0)],
        ghost_kind=GhostKind.PERSONAL_BEST if ghost_won is not None else None,
        ghost_won=ghost_won,
    )


def _result_with_keys(key_stats: dict[str, tuple[int, int]]) -> RaceResult:
    return replace(_result(), key_stats=key_stats)


def test_key_stats_aggregate_across_races(repo: SQLiteRepository, quote: Quote) -> None:
    repo.save_race(
        result=_result_with_keys({"a": (10, 2), "b": (5, 0)}),
        quote=quote,
        started_at="2026-06-07T10:00:00",
    )
    repo.save_race(
        result=_result_with_keys({"a": (4, 1), "c": (3, 3)}),
        quote=quote,
        started_at="2026-06-07T10:05:00",
    )
    stats = repo.get_key_stats()
    assert stats["a"] == (14, 3)  # summed across both races
    assert stats["b"] == (5, 0)
    assert stats["c"] == (3, 3)


def test_wipe_clears_key_stats(repo: SQLiteRepository, quote: Quote) -> None:
    repo.save_race(
        result=_result_with_keys({"a": (10, 2)}),
        quote=quote,
        started_at="2026-06-07T10:00:00",
    )
    repo.wipe()
    assert repo.get_key_stats() == {}


def test_profile_created_on_init(repo: SQLiteRepository) -> None:
    p = repo.get_profile()
    assert p.display_name == "you"
    assert p.races_played == 0


def test_save_race_updates_aggregates(repo: SQLiteRepository, quote: Quote) -> None:
    repo.save_race(
        result=_result(80.0, ghost_won=True), quote=quote, started_at="2026-06-07T10:00:00"
    )
    p = repo.get_profile()
    assert p.races_played == 1
    assert p.races_won == 1
    assert p.best_wpm == 80.0
    assert p.total_chars == 103
    assert p.total_time_ms == 60_000


def test_personal_best_replay(repo: SQLiteRepository, quote: Quote) -> None:
    repo.save_race(result=_result(50.0), quote=quote, started_at="2026-06-07T10:00:00")
    repo.save_race(result=_result(90.0), quote=quote, started_at="2026-06-07T10:05:00")
    pb = repo.personal_best_replay()
    assert pb is not None
    timeline, wpm, pb_quote = pb
    assert wpm == 90.0
    assert timeline[-1].progress_pct == 100.0
    assert pb_quote.ext_id == quote.ext_id  # ghost carries its own quote


def test_last_replay(repo: SQLiteRepository, quote: Quote) -> None:
    repo.save_race(result=_result(50.0), quote=quote, started_at="2026-06-07T10:00:00")
    repo.save_race(result=_result(60.0), quote=quote, started_at="2026-06-07T11:00:00")
    last = repo.last_replay()
    assert last is not None and last[1] == 60.0


def test_implausible_run_is_not_a_ghost(repo: SQLiteRepository, quote: Quote) -> None:
    repo.save_race(result=_result(2222.0), quote=quote, started_at="2026-06-07T10:00:00")
    assert repo.personal_best_replay() is None  # filtered out (wpm > 300)


def test_time_mode_runs_are_not_ghosts(repo: SQLiteRepository, quote: Quote) -> None:
    repo.save_race(
        result=_result(90.0, kind=RaceKind.TIME, mode_seconds=60),
        quote=quote,
        started_at="2026-06-07T10:00:00",
    )
    assert repo.personal_best_replay() is None  # ghosts are quote-mode only


def test_history_and_count(repo: SQLiteRepository, quote: Quote) -> None:
    for i in range(3):
        repo.save_race(result=_result(50 + i), quote=quote, started_at=f"2026-06-07T1{i}:00:00")
    assert repo.count_races() == 3
    hist = repo.list_history(limit=2)
    assert len(hist) == 2
    assert hist[0].started_at > hist[1].started_at  # newest first


def test_best_by_mode(repo: SQLiteRepository, quote: Quote) -> None:
    repo.save_race(
        result=_result(70.0, kind=RaceKind.TIME, mode_seconds=30),
        quote=quote,
        started_at="2026-06-07T10:00:00",
    )
    repo.save_race(
        result=_result(85.0, kind=RaceKind.TIME, mode_seconds=60),
        quote=quote,
        started_at="2026-06-07T10:05:00",
    )
    best = repo.best_by_mode(RaceKind.TIME)
    assert best[30] == 70.0
    assert best[60] == 85.0


def test_best_quote_run(repo: SQLiteRepository, quote: Quote) -> None:
    repo.save_race(result=_result(60.0), quote=quote, started_at="2026-06-07T10:00:00")
    repo.save_race(result=_result(88.0), quote=quote, started_at="2026-06-07T10:05:00")
    best = repo.best_quote_run()
    assert best is not None and best[0] == 88.0


def test_recompute_profile_matches(repo: SQLiteRepository, quote: Quote) -> None:
    repo.save_race(
        result=_result(80.0, ghost_won=True), quote=quote, started_at="2026-06-07T10:00:00"
    )
    before = repo.get_profile()
    after = repo.recompute_profile()
    assert after.races_played == before.races_played
    assert after.best_wpm == before.best_wpm
    assert after.total_chars == before.total_chars


def test_daily_flow(repo: SQLiteRepository, quote: Quote) -> None:
    repo.get_or_create_daily("2026-06-07", quote)
    repo.save_race(
        result=_result(75.0), quote=quote, started_at="2026-06-07T09:00:00", is_daily=True
    )
    board = repo.daily_leaderboard("2026-06-07")
    assert len(board) == 1 and board[0].wpm == 75.0
    daily = repo.get_or_create_daily("2026-06-07", quote)
    assert daily.attempts == 1
    assert daily.best_wpm == 75.0
