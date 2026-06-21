"""Lobby management: create, browse, inspect, join (validation)."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from typefaster_shared.dto import CreateLobbyRequest, LobbySummary
from typefaster_shared.events import LobbyState

from ..deps import CurrentUser, RepoDep, SettingsDep, rate_limiter

router = APIRouter(prefix="/lobbies", tags=["lobbies"])

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars
# Cap lobby creation per IP to stop spam (auth-gated, but still abusable).
_create_limit = Depends(rate_limiter("lobby_create", limit=12, window_seconds=60))


def _new_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(6))


@router.post(
    "",
    response_model=LobbySummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_create_limit],
)
async def create_lobby(
    body: CreateLobbyRequest, username: CurrentUser, repo: RepoDep
) -> LobbySummary:
    if body.mode_seconds not in (30, 60, 120):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "mode must be 30, 60, or 120")
    code = _new_code()
    while await repo.get_lobby(code) is not None:
        code = _new_code()
    await repo.create_lobby(code, body.name, username, body.is_public, body.mode_seconds)
    return LobbySummary(
        code=code,
        name=body.name,
        host=username,
        is_public=body.is_public,
        mode_seconds=body.mode_seconds,
        status="waiting",
        player_count=0,
    )


@router.get("", response_model=list[LobbySummary])
async def list_lobbies(repo: RepoDep, _: CurrentUser) -> list[LobbySummary]:
    return await repo.list_public_lobbies()


@router.get("/{code}", response_model=LobbyState)
async def get_lobby(code: str, repo: RepoDep, _: CurrentUser) -> LobbyState:
    lobby = await repo.get_lobby(code)
    if lobby is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lobby not found")
    players = await repo.get_players(code)
    return LobbyState(
        code=code,
        name=lobby["name"],
        host=lobby["host"],
        is_public=lobby.get("is_public") == "1",
        mode_seconds=int(lobby["mode_seconds"]),
        status=lobby["status"],
        players=players,
    )


@router.post("/{code}/join", response_model=LobbySummary)
async def join_lobby(
    code: str, username: CurrentUser, repo: RepoDep, settings: SettingsDep
) -> LobbySummary:
    lobby = await repo.get_lobby(code)
    if lobby is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lobby not found")
    if lobby["status"] != "waiting":
        raise HTTPException(status.HTTP_409_CONFLICT, "Race already in progress")
    players = await repo.get_players(code)
    already_in = any(p.username == username for p in players)
    if not already_in and len(players) >= settings.max_players_per_lobby:
        raise HTTPException(status.HTTP_409_CONFLICT, "Lobby is full")
    return LobbySummary(
        code=code,
        name=lobby["name"],
        host=lobby["host"],
        is_public=lobby.get("is_public") == "1",
        mode_seconds=int(lobby["mode_seconds"]),
        status=lobby["status"],
        player_count=len(players),
    )
