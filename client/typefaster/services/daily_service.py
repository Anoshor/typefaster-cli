"""Daily challenge: deterministic shared quote + local daily leaderboard."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from ..domain.models import DailyChallenge, RaceRecord
from ..infra import quote_loader
from ..infra.repository import Repository


def _utc_today() -> date:
    """The daily challenge day in UTC.

    Races are stored with a UTC ``started_at`` and the daily leaderboard filters
    on that, so the day MUST be UTC too — otherwise (e.g. in IST) results land on
    the wrong day and the challenge never updates. UTC also makes the daily
    genuinely 'the same for everyone'.
    """
    return datetime.now(UTC).date()


class DailyService:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def today(self, day: date | None = None) -> DailyChallenge:
        day = day or _utc_today()
        quote = quote_loader.daily_quote(day)
        return self._repo.get_or_create_daily(day.isoformat(), quote)

    def leaderboard(self, day: date | None = None, limit: int = 20) -> list[RaceRecord]:
        day = day or _utc_today()
        return self._repo.daily_leaderboard(day.isoformat(), limit=limit)

    def streak(self, day: date | None = None) -> int:
        """Consecutive daily-challenge days ending today (or yesterday, if today
        hasn't been played yet — the streak is still alive, just not extended)."""
        today = day or _utc_today()
        played = set(self._repo.daily_days_played())
        cursor = today if today.isoformat() in played else today - timedelta(days=1)
        n = 0
        while cursor.isoformat() in played:
            n += 1
            cursor -= timedelta(days=1)
        return n
