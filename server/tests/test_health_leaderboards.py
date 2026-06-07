"""Health and leaderboard endpoint tests."""

from __future__ import annotations

from starlette.testclient import TestClient

from .conftest import auth_header, register


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_readyz(client: TestClient) -> None:
    resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_empty_global_leaderboard(client: TestClient) -> None:
    token = register(client, "nora")
    resp = client.get("/leaderboards/global", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["scope"] == "global"
    assert resp.json()["entries"] == []


def test_unknown_scope_404(client: TestClient) -> None:
    token = register(client, "omar")
    assert client.get("/leaderboards/yearly", headers=auth_header(token)).status_code == 404


def test_daily_scope_has_period(client: TestClient) -> None:
    token = register(client, "pia")
    resp = client.get("/leaderboards/daily", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["period"] is not None
