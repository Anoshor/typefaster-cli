"""WebSocket protocol: event types, the message envelope, and payload schemas.

Every WebSocket frame is a JSON object with the shape::

    { "type": "<EVENT>", "ts": <unix_seconds>, "data": { ... } }

``ServerEvent`` values are sent server→client; ``ClientCommand`` values are
sent client→server. See ``docs/websocket-protocol.md`` for full examples.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ServerEvent(str, Enum):
    LOBBY_CREATED = "LOBBY_CREATED"
    LOBBY_UPDATE = "LOBBY_UPDATE"
    PLAYER_JOINED = "PLAYER_JOINED"
    PLAYER_LEFT = "PLAYER_LEFT"
    READY_STATE = "READY_STATE"
    HOST_CHANGED = "HOST_CHANGED"
    RACE_COUNTDOWN = "RACE_COUNTDOWN"
    RACE_START = "RACE_START"
    RACE_PROGRESS = "RACE_PROGRESS"
    RACE_FINISHED = "RACE_FINISHED"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    DAILY_CHALLENGE_UPDATE = "DAILY_CHALLENGE_UPDATE"
    ERROR = "ERROR"


class ClientCommand(str, Enum):
    SET_READY = "SET_READY"
    PROGRESS = "PROGRESS"
    FINISH = "FINISH"
    CHAT = "CHAT"
    LEAVE = "LEAVE"


class Envelope(BaseModel):
    """The universal frame wrapper."""

    type: str
    data: dict[str, Any] = Field(default_factory=dict)
    ts: float = Field(default_factory=lambda: time.time())

    @classmethod
    def of(cls, event: ServerEvent | ClientCommand, **data: Any) -> Envelope:
        return cls(type=event.value, data=data)


# ── Payload schemas (documentation + optional validation) ─────────────────
class PlayerState(BaseModel):
    username: str
    ready: bool = False
    progress: float = 0.0  # 0..100
    wpm: float = 0.0
    finished: bool = False


class LobbyState(BaseModel):
    code: str
    name: str
    host: str
    is_public: bool
    mode_seconds: int
    status: str  # waiting | countdown | racing | finished
    players: list[PlayerState]


class RaceStartPayload(BaseModel):
    quote_id: str
    text: str
    mode_seconds: int
    server_start_ms: int


class ProgressPayload(BaseModel):
    progress: float  # 0..100
    wpm: float
    correct_chars: int
    total_keystrokes: int


class FinishPayload(BaseModel):
    duration_ms: int
    correct_chars: int
    incorrect_chars: int
    total_keystrokes: int
    correct_keystrokes: int
    pasted: bool = False


class ChatPayload(BaseModel):
    message: str
