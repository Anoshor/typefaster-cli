"""Synchronous REST client for the TYPEFASTER server."""

from __future__ import annotations

import contextlib
from typing import Any

import httpx

from .token_store import DEFAULT_SERVER_URL, Session


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"[{status_code}] {detail}")
        self.status_code = status_code
        self.detail = detail


class ApiClient:
    def __init__(self, session: Session, timeout: float = 10.0) -> None:
        self.session = session
        self._timeout = timeout
        self._client = httpx.Client(base_url=session.server_url, timeout=timeout)
        # Set when a connection failure forced a fallback to the default server,
        # so callers can surface a one-time "saved server was unreachable" notice.
        self.failed_over = False

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
            # A connection-level failure (DNS/unreachable) against a non-default
            # server may mean the saved server is dead. Retry once on the default
            # and, if that works, persist it so the user self-heals.
            if self.session.server_url != DEFAULT_SERVER_URL and not self.failed_over:
                self._failover_to_default()
                try:
                    resp = self._client.request(method, path, **kwargs)
                except httpx.HTTPError as exc2:
                    raise ApiError(0, f"connection failed: {exc2}") from exc2
            else:
                raise ApiError(0, f"connection failed: {exc}") from exc
        if resp.status_code >= 400:
            detail = _extract_detail(resp)
            raise ApiError(resp.status_code, detail)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def _failover_to_default(self) -> None:
        """Switch the session to the default server, persist it, and rebuild the
        underlying client so the retry targets the new base URL."""
        self.session.server_url = DEFAULT_SERVER_URL
        with contextlib.suppress(OSError):
            self.session.save()  # persistence is best-effort; in-memory switch still works
        self._client.close()
        self._client = httpx.Client(base_url=DEFAULT_SERVER_URL, timeout=self._timeout)
        self.failed_over = True

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

    # ── oauth device flow ──────────────────────────────────────────────
    def oauth_start(self, provider: str) -> Any:
        return self._request("POST", f"/auth/oauth/{provider}/start")

    def oauth_poll(self, provider: str, device_code: str) -> Any:
        return self._request(
            "POST", f"/auth/oauth/{provider}/poll", json={"device_code": device_code}
        )

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
