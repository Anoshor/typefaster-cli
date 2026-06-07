"""Daily challenge: deterministic shared quote + local daily leaderboard."""

from __future__ import annotations

from datetime import date

from ..domain.models import DailyChallenge, RaceRecord
from ..infra import quote_loader
from ..infra.repository import Repository


class DailyService:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def today(self, day: date | None = None) -> DailyChallenge:
        day = day or date.today()
        quote = quote_loader.daily_quote(day)
        return self._repo.get_or_create_daily(day.isoformat(), quote)

    def leaderboard(self, day: date | None = None, limit: int = 20) -> list[RaceRecord]:
        day = day or date.today()
        return self._repo.daily_leaderboard(day.isoformat(), limit=limit)
