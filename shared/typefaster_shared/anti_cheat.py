"""Lightweight anti-cheat heuristics.

Deliberately conservative: flag clearly impossible results, don't try to be a
full statistical detector. A flagged race is kept but excluded from
leaderboards and marked ``suspicious``.
"""

from __future__ import annotations

from dataclasses import dataclass

# Tunables. The fastest verified human typists peak around ~300 WPM in bursts;
# sustained world-record pace is ~215 WPM. We flag well above that.
MAX_PLAUSIBLE_WPM = 250.0
MAX_PLAUSIBLE_BURST_WPM = 350.0
MIN_KEYSTROKE_INTERVAL_MS = 12  # ~10000 cpm; below this is non-human


@dataclass(frozen=True, slots=True)
class CheatReport:
    suspicious: bool
    reasons: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.suspicious


def evaluate(
    *,
    wpm: float,
    raw_wpm: float,
    duration_ms: int,
    total_keystrokes: int,
    quote_length: int,
    correct_chars: int,
    pasted: bool = False,
) -> CheatReport:
    reasons: list[str] = []

    if pasted:
        reasons.append("paste_detected")
    if wpm > MAX_PLAUSIBLE_WPM:
        reasons.append("impossible_wpm")
    if raw_wpm > MAX_PLAUSIBLE_BURST_WPM:
        reasons.append("impossible_burst")
    if correct_chars > quote_length:
        reasons.append("overcount_chars")

    # Average per-keystroke interval too low to be human.
    if total_keystrokes > 5 and duration_ms > 0:
        interval = duration_ms / total_keystrokes
        if interval < MIN_KEYSTROKE_INTERVAL_MS:
            reasons.append("superhuman_cadence")

    # Completed a long quote in an implausibly short time.
    if quote_length >= 50 and duration_ms < 1000:
        reasons.append("impossible_completion_time")

    return CheatReport(suspicious=bool(reasons), reasons=tuple(reasons))
