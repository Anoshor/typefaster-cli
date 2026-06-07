"""Server test fixtures backed by an in-memory fake Redis."""

from __future__ import annotations

import fakeredis.aioredis
import pytest
from app.config import Settings
from app.main import create_app
from starlette.testclient import TestClient


@pytest.fixture
def settings() -> Settings:
    return Settings(
        jwt_secret="test-secret",
        countdown_seconds=0,  # no countdown delay in tests
        access_token_minutes=60,
    )


@pytest.fixture
def client(settings: Settings):  # type: ignore[no-untyped-def]
    app = create_app()
    app.state.settings = settings
    app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    with TestClient(app) as c:
        yield c


def register(client: TestClient, username: str = "alice", password: str = "password123") -> str:
    resp = client.post("/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
