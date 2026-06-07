"""Offline plausibility checks for a finished race.

Pure and dependency-free. Mirrors the server's anti-cheat thresholds
(``typefaster_shared.anti_cheat``) so offline and online behave consistently.
A flagged race is shown to the player but is *not* recorded (no stats, no
personal best), preventing pastes / held keys / auto-input from polluting data.
"""

from __future__ import annotations

# The fastest sustained human typing is ~215 WPM; bursts peak near ~300.
MAX_PLAUSIBLE_WPM = 300.0
MAX_PLAUSIBLE_RAW_WPM = 400.0
MIN_KEYSTROKE_INTERVAL_MS = 12.0  # below ~10000 cpm is non-human


def evaluate(
    *,
    wpm: float,
    raw_wpm: float,
    duration_ms: int,
    total_keystrokes: int,
    quote_length: int,
    pasted: bool = False,
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(suspicious, reasons)`` for a finished race."""
    reasons: list[str] = []

    if pasted:
        reasons.append("paste detected")
    if wpm > MAX_PLAUSIBLE_WPM:
        reasons.append("impossible WPM")
    if raw_wpm > MAX_PLAUSIBLE_RAW_WPM:
        reasons.append("impossible burst speed")

    if (
        total_keystrokes > 5
        and duration_ms > 0
        and duration_ms / total_keystrokes < MIN_KEYSTROKE_INTERVAL_MS
    ):
        reasons.append("superhuman cadence")

    if quote_length >= 40 and duration_ms < 1000:
        reasons.append("impossible completion time")

    return bool(reasons), tuple(reasons)
