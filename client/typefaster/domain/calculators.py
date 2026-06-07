"""Typing-speed and accuracy math. Pure functions, MonkeyType-style.

Definitions
-----------
- A "word" is normalized to 5 characters.
- ``wpm``      = (correct_chars / 5) / minutes
- ``raw_wpm``  = (total_typed_chars / 5) / minutes  (errors included)
- ``accuracy`` = correct_keystrokes / total_keystrokes  (0..1)

All functions guard against division by zero and return 0.0 for empty input.
"""

from __future__ import annotations

CHARS_PER_WORD = 5


def _minutes(elapsed_ms: int) -> float:
    return elapsed_ms / 1000.0 / 60.0


def wpm(correct_chars: int, elapsed_ms: int) -> float:
    """Net words-per-minute based on correctly typed characters."""
    minutes = _minutes(elapsed_ms)
    if minutes <= 0:
        return 0.0
    return (correct_chars / CHARS_PER_WORD) / minutes


def raw_wpm(total_typed_chars: int, elapsed_ms: int) -> float:
    """Gross words-per-minute including incorrect characters."""
    minutes = _minutes(elapsed_ms)
    if minutes <= 0:
        return 0.0
    return (total_typed_chars / CHARS_PER_WORD) / minutes


def accuracy(correct_keystrokes: int, total_keystrokes: int) -> float:
    """Fraction of character keystrokes that were correct (0..1)."""
    if total_keystrokes <= 0:
        return 0.0
    return correct_keystrokes / total_keystrokes


def round_stats(value: float, digits: int = 1) -> float:
    """Round a stat for display/storage consistency."""
    return round(value, digits)
