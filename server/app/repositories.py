"""Redis-backed persistence for users, sessions, lobbies, races, leaderboards."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

from redis.asyncio import Redis
from typefaster_shared.dto import LobbySummary
from typefaster_shared.events import PlayerState

from . import redis_keys as keys


def _s(v: object) -> object:
    """Decode bytes to str; pass through everything else.

    Keeps the repository correct whether the client was created with
    ``decode_responses=True`` (real deployments) or returns raw bytes (some
    test doubles), so callers always see ``str`` values.
    """
    return v.decode("utf-8") if isinstance(v, bytes) else v


def _sd(d: dict) -> dict:  # type: ignore[type-arg]
    return {_s(k): _s(v) for k, v in d.items()} if d else d


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sanitize_username(raw: str) -> str:
    """Coerce an external display name into a valid username (3-24, [A-Za-z0-9_])."""
    cleaned = "".join(c if (c.isalnum() or c == "_") else "_" for c in raw).strip("_")
    return cleaned[:24]


def today_str() -> str:
    return date.today().isoformat()


def week_str(day: date | None = None) -> str:
    d = day or date.today()
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


class RedisRepository:
    def __init__(self, redis: Redis) -> None:
        self.r = redis

    # ── users ──────────────────────────────────────────────────────────
    async def create_user(self, username: str, password_hash: str) -> bool:
        key = keys.user(username)
        created = await self.r.hsetnx(key, "password_hash", password_hash)
        if not created:
            return False
        await self.r.hset(
            key,
            mapping={
                "username": username,
                "created_at": _utc_now_iso(),
                "races_played": 0,
                "best_wpm": 0.0,
            },
        )
        return True

    async def get_user(self, username: str) -> dict[str, str] | None:
        data = _sd(await self.r.hgetall(keys.user(username)))
        return data or None

    async def find_or_create_oauth_user(
        self, provider: str, provider_id: str, preferred_username: str
    ) -> str:
        """Map an external (provider, id) identity to a TYPEFASTER username,
        creating the account on first sign-in. Returns the username."""
        idx = keys.oauth(provider, provider_id)
        existing = _s(await self.r.get(idx))
        if existing:
            return str(existing)
        base = _sanitize_username(preferred_username) or f"{provider}user"
        username = base
        i = 0
        while await self.r.exists(keys.user(username)):
            i += 1
            username = f"{base}{i}"
        await self.r.hset(
            keys.user(username),
            mapping={
                "username": username,
                "created_at": _utc_now_iso(),
                "races_played": 0,
                "best_wpm": 0.0,
                "password_hash": "",  # OAuth-only account; password login disabled
                "provider": provider,
                "provider_id": provider_id,
            },
        )
        await self.r.set(idx, username)
        return username

    async def bump_user_stats(self, username: str, wpm: float) -> None:
        key = keys.user(username)
        if not await self.r.exists(key):
            return
        await self.r.hincrby(key, "races_played", 1)
        current = float(_s(await self.r.hget(key, "best_wpm")) or 0.0)
        if wpm > current:
            await self.r.hset(key, "best_wpm", wpm)

    # ── rate limiting ──────────────────────────────────────────────────
    async def incr_rate(self, key: str, window_seconds: int) -> int:
        """Increment a fixed-window counter, returning the new count."""
        n = int(await self.r.incr(key))
        if n == 1:
            await self.r.expire(key, window_seconds)
        return n

    async def incr_ws_connections(self, ip: str) -> int:
        """Count a new WebSocket connection for an IP, returning the live total.
        A safety TTL refreshes on each connect so a crashed process can't leak a
        permanently-elevated count."""
        key = f"ws:conn:{ip}"
        n = int(await self.r.incr(key))
        await self.r.expire(key, 3600)
        return n

    async def decr_ws_connections(self, ip: str) -> None:
        key = f"ws:conn:{ip}"
        if int(await self.r.decr(key)) <= 0:
            await self.r.delete(key)

    # ── sessions ───────────────────────────────────────────────────────
    async def create_session(self, jti: str, username: str, ttl_seconds: int) -> None:
        await self.r.set(keys.session(jti), username, ex=ttl_seconds)

    async def get_session(self, jti: str) -> str | None:
        return _s(await self.r.get(keys.session(jti)))  # type: ignore[return-value]

    async def delete_session(self, jti: str) -> None:
        await self.r.delete(keys.session(jti))

    # ── lobbies ────────────────────────────────────────────────────────
    async def create_lobby(
        self, code: str, name: str, host: str, is_public: bool, mode_seconds: int
    ) -> None:
        await self.r.hset(
            keys.lobby(code),
            mapping={
                "name": name,
                "host": host,
                "is_public": int(is_public),
                "mode_seconds": mode_seconds,
                "status": "waiting",
                "created_at": _utc_now_iso(),
            },
        )
        if is_public:
            await self.r.sadd(keys.PUBLIC_LOBBIES, code)

    async def get_lobby(self, code: str) -> dict[str, str] | None:
        data = _sd(await self.r.hgetall(keys.lobby(code)))
        return data or None

    async def set_lobby_status(self, code: str, status: str) -> None:
        await self.r.hset(keys.lobby(code), "status", status)
        # Only waiting public lobbies are browsable/joinable.
        if status == "waiting":
            lobby = await self.get_lobby(code)
            if lobby and lobby.get("is_public") == "1":
                await self.r.sadd(keys.PUBLIC_LOBBIES, code)
        else:
            await self.r.srem(keys.PUBLIC_LOBBIES, code)

    async def set_host(self, code: str, username: str) -> None:
        await self.r.hset(keys.lobby(code), "host", username)

    async def delete_lobby(self, code: str) -> None:
        await self.r.delete(keys.lobby(code), keys.lobby_players(code), keys.race(code))
        await self.r.srem(keys.PUBLIC_LOBBIES, code)

    async def list_public_lobbies(self) -> list[LobbySummary]:
        codes = {_s(c) for c in await self.r.smembers(keys.PUBLIC_LOBBIES)}
        out: list[LobbySummary] = []
        for code in codes:
            lobby = await self.get_lobby(code)
            if not lobby:
                await self.r.srem(keys.PUBLIC_LOBBIES, code)
                continue
            count = await self.r.hlen(keys.lobby_players(code))
            out.append(
                LobbySummary(
                    code=code,
                    name=lobby["name"],
                    host=lobby["host"],
                    is_public=lobby.get("is_public") == "1",
                    mode_seconds=int(lobby["mode_seconds"]),
                    status=lobby["status"],
                    player_count=count,
                )
            )
        return out

    # ── players ────────────────────────────────────────────────────────
    async def upsert_player(self, code: str, state: PlayerState) -> None:
        await self.r.hset(keys.lobby_players(code), state.username, state.model_dump_json())

    async def remove_player(self, code: str, username: str) -> int:
        await self.r.hdel(keys.lobby_players(code), username)
        return await self.r.hlen(keys.lobby_players(code))

    async def get_players(self, code: str) -> list[PlayerState]:
        raw = await self.r.hgetall(keys.lobby_players(code))
        return [PlayerState.model_validate_json(_s(v)) for v in raw.values()]

    async def get_player(self, code: str, username: str) -> PlayerState | None:
        v = await self.r.hget(keys.lobby_players(code), username)
        return PlayerState.model_validate_json(_s(v)) if v else None

    # ── race state ─────────────────────────────────────────────────────
    async def set_race(
        self, code: str, *, quote_id: str, text: str, mode_seconds: int, start_ms: int
    ) -> None:
        await self.r.hset(
            keys.race(code),
            mapping={
                "quote_id": quote_id,
                "text": text,
                "mode_seconds": mode_seconds,
                "start_ms": start_ms,
                "status": "racing",
            },
        )

    async def get_race(self, code: str) -> dict[str, str] | None:
        data = _sd(await self.r.hgetall(keys.race(code)))
        return data or None

    # ── leaderboards ───────────────────────────────────────────────────
    async def record_score(self, username: str, wpm: float) -> None:
        # GT=True keeps each member's best score only.
        await self.r.zadd(keys.leaderboard_global(), {username: wpm}, gt=True)
        await self.r.zadd(keys.leaderboard_daily(today_str()), {username: wpm}, gt=True)
        await self.r.zadd(keys.leaderboard_weekly(week_str()), {username: wpm}, gt=True)

    async def top(self, key: str, limit: int = 20) -> list[tuple[str, float]]:
        rows = await self.r.zrevrange(key, 0, limit - 1, withscores=True)
        return [(str(_s(member)), float(score)) for member, score in rows]

    # ── ghosts ─────────────────────────────────────────────────────────
    async def save_pb_ghost(self, username: str, timeline: list[dict[str, float]]) -> None:
        await self.r.set(keys.ghost_pb(username), json.dumps(timeline))

    async def get_pb_ghost(self, username: str) -> list[dict[str, float]] | None:
        v = _s(await self.r.get(keys.ghost_pb(username)))
        return json.loads(v) if v else None  # type: ignore[arg-type]
