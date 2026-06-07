"""Authentication: register, login, logout, me."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import APIRouter, Header, HTTPException, status
from typefaster_shared.dto import LoginRequest, RegisterRequest, TokenResponse, UserPublic

from ..deps import CurrentUser, RepoDep, SettingsDep
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, repo: RepoDep, settings: SettingsDep) -> TokenResponse:
    created = await repo.create_user(body.username, hash_password(body.password))
    if not created:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
    token, jti = create_access_token(body.username, settings)
    await repo.create_session(jti, body.username, settings.access_token_minutes * 60)
    return TokenResponse(access_token=token, username=body.username)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, repo: RepoDep, settings: SettingsDep) -> TokenResponse:
    user = await repo.get_user(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token, jti = create_access_token(body.username, settings)
    await repo.create_session(jti, body.username, settings.access_token_minutes * 60)
    return TokenResponse(access_token=token, username=body.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    repo: RepoDep,
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return
    jti = payload.get("jti")
    if jti:
        await repo.delete_session(jti)


@router.get("/me", response_model=UserPublic)
async def me(username: CurrentUser, repo: RepoDep) -> UserPublic:
    user = await repo.get_user(username)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserPublic(
        username=user["username"],
        created_at=user["created_at"],
        races_played=int(user.get("races_played", 0)),
        best_wpm=float(user.get("best_wpm", 0.0)),
    )
