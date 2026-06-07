"""Core domain models. Pure dataclasses and enums — no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .errors import InvalidRaceModeError


class Difficulty(str, Enum):
    """Quote length bucket."""

    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

    @staticmethod
    def from_length(length: int) -> Difficulty:
        if length < 120:
            return Difficulty.SHORT
        if length < 250:
            return Difficulty.MEDIUM
        return Difficulty.LONG


class RaceMode(int, Enum):
    """Supported race durations, in seconds."""

    SHORT = 30
    NORMAL = 60
    LONG = 120

    @staticmethod
    def from_seconds(seconds: int) -> RaceMode:
        try:
            return RaceMode(seconds)
        except ValueError as exc:  # pragma: no cover - trivial
            raise InvalidRaceModeError(
                f"Unsupported race mode: {seconds}s (use 30, 60, or 120)"
            ) from exc


class GhostKind(str, Enum):
    """The three offline ghost sources."""

    PERSONAL_BEST = "personal-best"
    LAST = "last"
    RANDOM = "random"


class RaceKind(str, Enum):
    """How a race is bounded and measured.

    - ``QUOTE``: type one fixed quote to completion; measured by time-to-finish
      and WPM. Ghost races (same text) live here.
    - ``TIME``: type continuously for a fixed number of seconds (text streams);
      measured by WPM over the full duration.

    The two are scored and stored separately — they are not comparable.
    """

    QUOTE = "quote"
    TIME = "time"


@dataclass(frozen=True, slots=True)
class Quote:
    """A piece of text to be typed."""

    ext_id: str
    text: str
    source: str | None = None

    @property
    def length(self) -> int:
        return len(self.text)

    @property
    def difficulty(self) -> Difficulty:
        return Difficulty.from_length(self.length)


@dataclass(frozen=True, slots=True)
class Keystroke:
    """A single character input event with a millisecond timestamp."""

    char: str
    t_ms: int
    correct: bool


@dataclass(frozen=True, slots=True)
class ReplayPoint:
    """A point on a race's progress timeline.

    Serialized form matches the spec: ``{"t": <ms>, "p": <percent 0-100>}``.
    """

    t_ms: int
    progress_pct: float


@dataclass(frozen=True, slots=True)
class Ghost:
    """An opponent reconstructed from a stored replay timeline.

    ``quote`` is the exact text the ghost was recorded on, so a ghost race uses
    identical text for a fair head-to-head.
    """

    kind: GhostKind
    label: str
    timeline: list[ReplayPoint]
    wpm: float = 0.0
    quote: Quote | None = None


@dataclass(frozen=True, slots=True)
class RaceResult:
    """The computed outcome of a finished race."""

    wpm: float
    raw_wpm: float
    accuracy: float
    correct_chars: int
    incorrect_chars: int
    progress: float  # 0..1
    duration_ms: int
    mode_seconds: int  # TIME mode: the limit (30/60/120). QUOTE mode: 0.
    kind: RaceKind = RaceKind.QUOTE
    timeline: list[ReplayPoint] = field(default_factory=list)
    ghost_kind: GhostKind | None = None
    ghost_won: bool | None = None
    # Set when the run is implausible (paste/auto-input) — not recorded.
    suspicious: bool = False
    flags: tuple[str, ...] = ()

    @property
    def completed(self) -> bool:
        return self.progress >= 1.0


@dataclass(slots=True)
class Profile:
    """Local player profile with denormalized lifetime aggregates."""

    display_name: str = "you"
    created_at: str = ""
    races_played: int = 0
    races_won: int = 0
    best_wpm: float = 0.0
    best_accuracy: float = 0.0
    total_chars: int = 0
    total_time_ms: int = 0


@dataclass(frozen=True, slots=True)
class RaceRecord:
    """A persisted race row, returned for history/stats views."""

    id: int
    quote_source: str | None
    mode_seconds: int
    started_at: str
    duration_ms: int
    wpm: float
    raw_wpm: float
    accuracy: float
    correct_chars: int
    incorrect_chars: int
    progress: float
    is_daily: bool
    ghost_kind: GhostKind | None
    ghost_won: bool | None
    kind: RaceKind = RaceKind.QUOTE


@dataclass(frozen=True, slots=True)
class DailyChallenge:
    """A day's shared challenge plus local aggregates."""

    day: str  # YYYY-MM-DD
    quote: Quote
    best_wpm: float = 0.0
    attempts: int = 0
