"""Lobby REST tests."""

from __future__ import annotations

from starlette.testclient import TestClient

from .conftest import auth_header, register


def test_create_and_list_public_lobby(client: TestClient) -> None:
    token = register(client, "ivan")
    h = auth_header(token)
    resp = client.post(
        "/lobbies", json={"name": "Speed Run", "is_public": True, "mode_seconds": 60}, headers=h
    )
    assert resp.status_code == 201
    code = resp.json()["code"]
    assert len(code) == 6

    listing = client.get("/lobbies", headers=h)
    assert listing.status_code == 200
    codes = [lobby["code"] for lobby in listing.json()]
    assert code in codes


def test_private_lobby_not_listed(client: TestClient) -> None:
    token = register(client, "judy")
    h = auth_header(token)
    resp = client.post(
        "/lobbies", json={"name": "Secret", "is_public": False, "mode_seconds": 30}, headers=h
    )
    code = resp.json()["code"]
    listing = client.get("/lobbies", headers=h).json()
    assert code not in [lobby["code"] for lobby in listing]


def test_get_unknown_lobby_404(client: TestClient) -> None:
    token = register(client, "ken")
    assert client.get("/lobbies/ZZZZZZ", headers=auth_header(token)).status_code == 404


def test_join_validates(client: TestClient) -> None:
    token = register(client, "lee")
    h = auth_header(token)
    code = client.post("/lobbies", json={"name": "Join Me", "mode_seconds": 60}, headers=h).json()[
        "code"
    ]
    resp = client.post(f"/lobbies/{code}/join", headers=h)
    assert resp.status_code == 200
    assert resp.json()["code"] == code


def test_invalid_mode_rejected(client: TestClient) -> None:
    token = register(client, "mary")
    resp = client.post(
        "/lobbies", json={"name": "Bad", "mode_seconds": 45}, headers=auth_header(token)
    )
    assert resp.status_code == 422


def test_lobbies_require_auth(client: TestClient) -> None:
    assert client.get("/lobbies").status_code == 401
