"""Password hashing (bcrypt) and JWT issuing/verification."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from .config import Settings

# bcrypt operates on at most 72 bytes; truncate consistently for hash + verify.
_BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(username: str, settings: Settings) -> tuple[str, str]:
    """Return ``(token, jti)``. The ``jti`` keys the server-side session so a
    token can be revoked on logout."""
    jti = uuid.uuid4().hex
    now = datetime.now(UTC)
    payload = {
        "sub": username,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
