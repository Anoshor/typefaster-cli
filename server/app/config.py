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

    # Abuse / DDoS hardening (app-layer). All per-IP unless noted; tune via env.
    global_rate_limit: int = 120  # max HTTP requests per IP per window
    global_rate_window: int = 60  # seconds
    ws_max_connections_per_ip: int = 10  # concurrent lobby sockets per IP
    ws_max_messages_per_window: int = 60  # messages per connection per window
    ws_message_window_seconds: int = 10  # → ~6 msg/s sustained per connection

    # OAuth device-flow login (all free). Empty => that provider is disabled.
    github_client_id: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""  # Google device flow requires the secret


def get_settings() -> Settings:
    return Settings()
