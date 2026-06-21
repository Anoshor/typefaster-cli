"""Tests for app-layer abuse / flood guards."""

from __future__ import annotations

import fakeredis.aioredis
import pytest
from app.abuse import MessageRateLimiter
from app.config import Settings
from app.main import create_app
from app.repositories import RedisRepository
from starlette.testclient import TestClient

from .conftest import auth_header, register


def _client(**overrides: object) -> TestClient:
    settings = Settings(
        jwt_secret="test-secret", countdown_seconds=0, access_token_minutes=60, **overrides
    )
    app = create_app()
    app.state.settings = settings
    app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return TestClient(app)


# ── global per-IP HTTP limiter ─────────────────────────────────────────


def test_global_rate_limit_blocks_flood() -> None:
    with _client(global_rate_limit=3) as c:
        codes = [c.get("/auth/me").status_code for _ in range(5)]
    # First 3 pass through (401, no token); the rest are throttled.
    assert codes[:3] == [401, 401, 401]
    assert codes[3:] == [429, 429]


def test_health_endpoints_exempt_from_global_limit() -> None:
    with _client(global_rate_limit=2) as c:
        codes = [c.get("/healthz").status_code for _ in range(5)]
    assert codes == [200, 200, 200, 200, 200]


def test_lobby_creation_is_rate_limited() -> None:
    # High global cap so only the lobby-create bucket (12/min) trips.
    with _client(global_rate_limit=1000) as c:
        h = auth_header(register(c, "flooder"))
        codes = [
            c.post(
                "/lobbies",
                json={"name": f"L{i}", "is_public": True, "mode_seconds": 60},
                headers=h,
            ).status_code
            for i in range(14)
        ]
    assert codes.count(201) == 12
    assert codes[12] == 429


# ── per-connection WebSocket message limiter ───────────────────────────


def test_message_rate_limiter_blocks_over_cap() -> None:
    clock = [0.0]
    lim = MessageRateLimiter(3, 10.0, now=lambda: clock[0])
    assert [lim.allow() for _ in range(4)] == [True, True, True, False]


def test_message_rate_limiter_resets_after_window() -> None:
    clock = [0.0]
    lim = MessageRateLimiter(2, 10.0, now=lambda: clock[0])
    assert lim.allow() and lim.allow() and not lim.allow()
    clock[0] = 11.0  # window elapsed
    assert lim.allow() is True


# ── WS connection counters ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_connection_counters() -> None:
    repo = RedisRepository(fakeredis.aioredis.FakeRedis(decode_responses=True))
    assert await repo.incr_ws_connections("1.2.3.4") == 1
    assert await repo.incr_ws_connections("1.2.3.4") == 2
    await repo.decr_ws_connections("1.2.3.4")
    assert await repo.incr_ws_connections("1.2.3.4") == 2  # back up from 1
    # A different IP is tracked independently.
    assert await repo.incr_ws_connections("5.6.7.8") == 1
