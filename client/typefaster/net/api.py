"""Synchronous REST client for the TYPEFASTER server."""

from __future__ import annotations

from typing import Any

import httpx

from .token_store import Session


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"[{status_code}] {detail}")
        self.status_code = status_code
        self.detail = detail


class ApiClient:
    def __init__(self, session: Session, timeout: float = 10.0) -> None:
        self.session = session
        self._client = httpx.Client(base_url=session.server_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ApiClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ── helpers ────────────────────────────────────────────────────────
    def _auth_headers(self) -> dict[str, str]:
        if not self.session.token:
            return {}
        return {"Authorization": f"Bearer {self.session.token}"}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            resp = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise ApiError(0, f"connection failed: {exc}") from exc
        if resp.status_code >= 400:
            detail = _extract_detail(resp)
            raise ApiError(resp.status_code, detail)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # ── auth ───────────────────────────────────────────────────────────
    # These return parsed JSON; typed as Any since the shape is documented
    # by the server's response models rather than enforced client-side.
    def register(self, username: str, password: str) -> Any:
        return self._request(
            "POST", "/auth/register", json={"username": username, "password": password}
        )

    def login(self, username: str, password: str) -> Any:
        return self._request(
            "POST", "/auth/login", json={"username": username, "password": password}
        )

    def logout(self) -> None:
        self._request("POST", "/auth/logout", headers=self._auth_headers())

    def me(self) -> Any:
        return self._request("GET", "/auth/me", headers=self._auth_headers())

    # ── lobbies ────────────────────────────────────────────────────────
    def create_lobby(self, name: str, is_public: bool, mode_seconds: int) -> Any:
        return self._request(
            "POST",
            "/lobbies",
            json={"name": name, "is_public": is_public, "mode_seconds": mode_seconds},
            headers=self._auth_headers(),
        )

    def list_lobbies(self) -> Any:
        return self._request("GET", "/lobbies", headers=self._auth_headers())

    def join_lobby(self, code: str) -> Any:
        return self._request("POST", f"/lobbies/{code}/join", headers=self._auth_headers())

    def leaderboard(self, scope: str, limit: int = 20) -> Any:
        return self._request(
            "GET", f"/leaderboards/{scope}", params={"limit": limit}, headers=self._auth_headers()
        )


def _extract_detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])
    except Exception:
        pass
    return resp.text or resp.reason_phrase


def ws_url(server_url: str, code: str, token: str) -> str:
    base = server_url.replace("https://", "wss://").replace("http://", "ws://").rstrip("/")
    return f"{base}/ws/lobby/{code}?token={token}"
