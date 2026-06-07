"""Centralized Redis key builders.

Every key the server uses is constructed here so the data model is documented
in one place (see also ``docs/redis-schema.md``).
"""

from __future__ import annotations


def user(username: str) -> str:
    """HASH: password_hash, created_at, races_played, best_wpm."""
    return f"user:{username.lower()}"


def session(jti: str) -> str:
    """STRING (TTL): maps a token's jti -> username. Deleted on logout."""
    return f"session:{jti}"


def lobby(code: str) -> str:
    """HASH: name, host, is_public, mode_seconds, status, created_at."""
    return f"lobby:{code}"


def lobby_players(code: str) -> str:
    """HASH: username -> JSON PlayerState."""
    return f"lobby:{code}:players"


def race(code: str) -> str:
    """HASH: quote_id, text, mode_seconds, start_ms, status."""
    return f"race:{code}"


PUBLIC_LOBBIES = "lobbies:public"  # SET of joinable public lobby codes


def leaderboard_global() -> str:
    """ZSET: username -> best_wpm (all time)."""
    return "leaderboard:global"


def leaderboard_daily(day: str) -> str:
    """ZSET: username -> best_wpm for a given YYYY-MM-DD (UTC)."""
    return f"leaderboard:daily:{day}"


def leaderboard_weekly(week: str) -> str:
    """ZSET: username -> best_wpm for a given ISO year-week (e.g. 2026-W23)."""
    return f"leaderboard:weekly:{week}"


def ghost_pb(username: str) -> str:
    """STRING: JSON replay timeline of the user's personal-best run."""
    return f"ghost:{username.lower()}:pb"
