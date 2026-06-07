"""FastAPI dependencies: settings, redis, repository, current user."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request, status

from .config import Settings
from .repositories import RedisRepository


def settings_dep(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


def repo_dep(request: Request) -> RedisRepository:
    return RedisRepository(request.app.state.redis)


SettingsDep = Annotated[Settings, Depends(settings_dep)]
RepoDep = Annotated[RedisRepository, Depends(repo_dep)]


async def current_user(
    repo: RepoDep,
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    username = await resolve_token(token, repo, settings)
    if username is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return username


async def resolve_token(token: str, repo: RedisRepository, settings: Settings) -> str | None:
    """Decode a JWT and confirm its session is still active. Returns username."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    jti = payload.get("jti")
    sub = payload.get("sub")
    if not jti or not sub:
        return None
    session_user = await repo.get_session(jti)
    if session_user != sub:
        return None
    return str(sub)


CurrentUser = Annotated[str, Depends(current_user)]
