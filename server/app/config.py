"""Server configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TYPEFASTER_", env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24  # 1 day
    cors_origins: str = "*"
    countdown_seconds: int = 3
    max_players_per_lobby: int = 8


def get_settings() -> Settings:
    return Settings()
