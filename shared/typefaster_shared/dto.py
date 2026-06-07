"""REST request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=24, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserPublic(BaseModel):
    username: str
    created_at: str
    races_played: int = 0
    best_wpm: float = 0.0


class CreateLobbyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    is_public: bool = True
    mode_seconds: int = 60


class LobbySummary(BaseModel):
    code: str
    name: str
    host: str
    is_public: bool
    mode_seconds: int
    status: str
    player_count: int


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    wpm: float


class LeaderboardResponse(BaseModel):
    scope: str  # global | daily | weekly
    period: str | None = None
    entries: list[LeaderboardEntry]
