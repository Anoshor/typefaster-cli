"""OAuth Device Authorization Flow (GitHub + Google).

This is the `gh auth login` style flow for CLIs: the client gets a short code +
URL, the user approves in a browser, and the client polls until we issue a
TYPEFASTER JWT. No client secrets live on the user's machine; Google's secret
stays server-side. Both providers are free.

Endpoints:
  POST /auth/oauth/{provider}/start  -> { device_code, user_code, verification_uri, interval, expires_in }
  POST /auth/oauth/{provider}/poll   -> { status: "pending"|"slow_down" } (200) or { access_token, username } (200)
                                        terminal errors -> 400
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typefaster_shared.dto import TokenResponse

from ..config import Settings
from ..deps import RepoDep, SettingsDep
from ..repositories import RedisRepository
from ..security import create_access_token

router = APIRouter(prefix="/auth/oauth", tags=["auth"])

_PROVIDERS = {
    "github": {
        "device": "https://github.com/login/device/code",
        "token": "https://github.com/login/oauth/access_token",
        "userinfo": "https://api.github.com/user",
        "scope": "read:user",
    },
    "google": {
        "device": "https://oauth2.googleapis.com/device/code",
        "token": "https://oauth2.googleapis.com/token",
        "userinfo": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
    },
}
_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


class PollBody(BaseModel):
    device_code: str


def _client_id(provider: str, settings: Settings) -> str:
    cid = settings.github_client_id if provider == "github" else settings.google_client_id
    if not cid:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"{provider} login is not configured on this server",
        )
    return cid


def _check_provider(provider: str) -> None:
    if provider not in _PROVIDERS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown provider")


@router.post("/{provider}/start")
async def start(provider: str, settings: SettingsDep) -> dict[str, Any]:
    _check_provider(provider)
    cid = _client_id(provider, settings)
    p = _PROVIDERS[provider]
    async with httpx.AsyncClient(timeout=10) as http:
        resp = await http.post(
            p["device"],
            data={"client_id": cid, "scope": p["scope"]},
            headers={"Accept": "application/json"},
        )
    if resp.status_code >= 400:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Provider device request failed")
    d = resp.json()
    return {
        "device_code": d["device_code"],
        "user_code": d["user_code"],
        # GitHub: verification_uri · Google: verification_url
        "verification_uri": d.get("verification_uri") or d.get("verification_url"),
        "interval": int(d.get("interval", 5)),
        "expires_in": int(d.get("expires_in", 900)),
    }


@router.post("/{provider}/poll")
async def poll(
    provider: str, body: PollBody, settings: SettingsDep, repo: RepoDep
) -> dict[str, Any]:
    _check_provider(provider)
    cid = _client_id(provider, settings)
    p = _PROVIDERS[provider]

    data = {"client_id": cid, "device_code": body.device_code, "grant_type": _GRANT}
    if provider == "google":
        data["client_secret"] = settings.google_client_secret

    async with httpx.AsyncClient(timeout=10) as http:
        tok = await http.post(p["token"], data=data, headers={"Accept": "application/json"})
        token_json = tok.json()

        err = token_json.get("error")
        if err == "authorization_pending":
            return {"status": "pending"}
        if err == "slow_down":
            return {"status": "slow_down"}
        if err:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Authorization failed: {err}")

        access = token_json.get("access_token")
        if not access:
            return {"status": "pending"}

        info = await http.get(p["userinfo"], headers={"Authorization": f"Bearer {access}"})
        if info.status_code >= 400:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not fetch profile")
        profile = info.json()

    provider_id, preferred = _identity(provider, profile)
    username = await repo.find_or_create_oauth_user(provider, provider_id, preferred)
    return await _issue(username, settings, repo)


def _identity(provider: str, profile: dict[str, Any]) -> tuple[str, str]:
    if provider == "github":
        return str(profile["id"]), str(profile.get("login") or "player")
    # google
    email = str(profile.get("email") or "")
    return str(profile["sub"]), (email.split("@")[0] or str(profile.get("name") or "player"))


async def _issue(username: str, settings: Settings, repo: RedisRepository) -> dict[str, Any]:
    token, jti = create_access_token(username, settings)
    await repo.create_session(jti, username, settings.access_token_minutes * 60)
    return TokenResponse(access_token=token, username=username).model_dump() | {"status": "ok"}
