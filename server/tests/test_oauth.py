"""Tests for OAuth device-flow endpoints and user mapping."""

from __future__ import annotations

import fakeredis.aioredis
import pytest
from starlette.testclient import TestClient

from app.repositories import RedisRepository


def test_unknown_provider_404(client: TestClient) -> None:
    assert client.post("/auth/oauth/myspace/start").status_code == 404


def test_provider_not_configured_returns_503(client: TestClient) -> None:
    # No client IDs set in test settings -> provider disabled.
    assert client.post("/auth/oauth/github/start").status_code == 503
    assert client.post("/auth/oauth/google/start").status_code == 503


@pytest.mark.asyncio
async def test_find_or_create_oauth_user_is_stable() -> None:
    repo = RedisRepository(fakeredis.aioredis.FakeRedis(decode_responses=True))
    u1 = await repo.find_or_create_oauth_user("github", "12345", "Alice-Smith")
    u2 = await repo.find_or_create_oauth_user("github", "12345", "Alice-Smith")
    assert u1 == u2  # same identity -> same account
    assert u1 == "Alice_Smith"  # sanitized to a valid username
    user = await repo.get_user(u1)
    assert user is not None and user["provider"] == "github"


@pytest.mark.asyncio
async def test_oauth_username_collision_gets_suffix() -> None:
    repo = RedisRepository(fakeredis.aioredis.FakeRedis(decode_responses=True))
    await repo.create_user("bob", "hash")  # password user takes "bob"
    name = await repo.find_or_create_oauth_user("google", "sub-1", "bob")
    assert name != "bob" and name.startswith("bob")
