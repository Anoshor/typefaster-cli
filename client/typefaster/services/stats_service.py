"""Read-side aggregation for the stats / history / leaderboard screens."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.models import Profile, RaceKind, RaceRecord
from ..infra.repository import Repository


@dataclass(slots=True)
class StatsSummary:
    profile: Profile
    avg_wpm: float
    avg_accuracy: float
    time_best_by_mode: dict[int, float]  # TIME mode: seconds -> best WPM
    quote_best_wpm: float  # QUOTE mode: best WPM
    quote_best_ms: int  # QUOTE mode: fastest completion (ms)
    recent_wpm: list[float]


class StatsService:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def summary(self) -> StatsSummary:
        profile = self._repo.get_profile()
        avg_wpm, avg_acc = self._repo.average_wpm_accuracy()
        recent = [r.wpm for r in reversed(self._repo.list_history(limit=20))]
        quote_best = self._repo.best_quote_run()
        return StatsSummary(
            profile=profile,
            avg_wpm=round(avg_wpm, 1),
            avg_accuracy=round(avg_acc, 4),
            time_best_by_mode=self._repo.best_by_mode(RaceKind.TIME),
            quote_best_wpm=quote_best[0] if quote_best else 0.0,
            quote_best_ms=quote_best[1] if quote_best else 0,
            recent_wpm=recent,
        )

    def history(self, limit: int = 20, offset: int = 0) -> list[RaceRecord]:
        return self._repo.list_history(limit=limit, offset=offset)

    def history_pages(self, page_size: int = 20) -> int:
        total = self._repo.count_races()
        return max(1, (total + page_size - 1) // page_size)

    def top_time_runs(self, mode_seconds: int, limit: int = 10) -> list[RaceRecord]:
        return self._repo.top_runs(mode_seconds, limit=limit, kind=RaceKind.TIME)

    def top_quote_runs(self, limit: int = 10) -> list[RaceRecord]:
        return self._repo.top_quote_runs(limit=limit)
