"""Authoritative scoring math, shared by client and server.

The server recomputes results from raw inputs and never trusts client-reported
WPM/accuracy. Identical math on both sides keeps the displayed and validated
numbers consistent.
"""

from __future__ import annotations

CHARS_PER_WORD = 5


def wpm(correct_chars: int, elapsed_ms: int) -> float:
    minutes = elapsed_ms / 60_000.0
    if minutes <= 0:
        return 0.0
    return (correct_chars / CHARS_PER_WORD) / minutes


def raw_wpm(total_chars: int, elapsed_ms: int) -> float:
    minutes = elapsed_ms / 60_000.0
    if minutes <= 0:
        return 0.0
    return (total_chars / CHARS_PER_WORD) / minutes


def accuracy(correct_keystrokes: int, total_keystrokes: int) -> float:
    if total_keystrokes <= 0:
        return 0.0
    return correct_keystrokes / total_keystrokes
