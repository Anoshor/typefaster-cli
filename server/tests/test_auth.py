"""Authentication flow tests."""

from __future__ import annotations

from starlette.testclient import TestClient

from .conftest import auth_header, register


def test_register_returns_token(client: TestClient) -> None:
    resp = client.post("/auth/register", json={"username": "bob", "password": "password123"})
    assert resp.status_code == 201
    assert resp.json()["username"] == "bob"
    assert resp.json()["access_token"]


def test_duplicate_register_conflicts(client: TestClient) -> None:
    register(client, "carol")
    resp = client.post("/auth/register", json={"username": "carol", "password": "password123"})
    assert resp.status_code == 409


def test_login_wrong_password(client: TestClient) -> None:
    register(client, "dave")
    resp = client.post("/auth/login", json={"username": "dave", "password": "wrong-pass"})
    assert resp.status_code == 401


def test_login_success(client: TestClient) -> None:
    register(client, "erin")
    resp = client.post("/auth/login", json={"username": "erin", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_me_requires_auth(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_me_returns_profile(client: TestClient) -> None:
    token = register(client, "frank")
    resp = client.get("/auth/me", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["username"] == "frank"


def test_logout_invalidates_token(client: TestClient) -> None:
    token = register(client, "grace")
    assert client.get("/auth/me", headers=auth_header(token)).status_code == 200
    client.post("/auth/logout", headers=auth_header(token))
    assert client.get("/auth/me", headers=auth_header(token)).status_code == 401


def test_register_validation(client: TestClient) -> None:
    # too-short password
    resp = client.post("/auth/register", json={"username": "heidi", "password": "short"})
    assert resp.status_code == 422
