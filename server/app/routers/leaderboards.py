"""Global / daily / weekly leaderboards."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from typefaster_shared.dto import LeaderboardEntry, LeaderboardResponse

from .. import redis_keys as keys
from ..deps import CurrentUser, RepoDep
from ..repositories import today_str, week_str

router = APIRouter(prefix="/leaderboards", tags=["leaderboards"])


def _build(scope: str, rows: list[tuple[str, float]], period: str | None) -> LeaderboardResponse:
    entries = [
        LeaderboardEntry(rank=i, username=u, wpm=round(w, 1)) for i, (u, w) in enumerate(rows, 1)
    ]
    return LeaderboardResponse(scope=scope, period=period, entries=entries)


@router.get("/{scope}", response_model=LeaderboardResponse)
async def leaderboard(
    scope: str,
    repo: RepoDep,
    _: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
) -> LeaderboardResponse:
    if scope == "global":
        key, period = keys.leaderboard_global(), None
    elif scope == "daily":
        period = today_str()
        key = keys.leaderboard_daily(period)
    elif scope == "weekly":
        period = week_str()
        key = keys.leaderboard_weekly(period)
    else:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "scope must be global, daily, or weekly")
    rows = await repo.top(key, limit=limit)
    return _build(scope, rows, period)
