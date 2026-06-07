"""The typing engine — pure state machine over a stream of keystrokes.

Time is injected (millisecond timestamps passed in), so the engine is fully
deterministic and unit-testable without a clock.

Backspace model (MonkeyType-style, the locked Phase 1 decision)
---------------------------------------------------------------
- Typing any character advances the cursor; a wrong char is recorded in place
  (shown red by the UI) and the cursor still advances.
- Backspace moves the cursor back one and clears that slot's correctness, so the
  player can retype it. Backspace is *not* counted as a keystroke.
- Accuracy is measured over **every** character keystroke (including ones later
  corrected), so corrections don't inflate accuracy. Completion/progress is
  measured from the current buffer state.
"""

from __future__ import annotations

from .calculators import accuracy, raw_wpm, wpm
from .models import GhostKind, RaceKind, RaceResult, ReplayPoint


class TypingEngine:
    """Processes keystrokes against a target string."""

    def __init__(self, target: str, *, allow_backspace: bool = True) -> None:
        if not target:
            raise ValueError("target text must not be empty")
        self.target = target
        self.allow_backspace = allow_backspace

        # Per-index correctness of the current buffer: None=untyped, True/False.
        self._states: list[bool | None] = [None] * len(target)
        self._cursor = 0  # index of the next character to type

        # Lifetime keystroke counters (corrections do not decrement these).
        self._total_keystrokes = 0
        self._correct_keystrokes = 0

        self._timeline: list[ReplayPoint] = [ReplayPoint(0, 0.0)]
        self._last_progress_pct = 0.0

    # ── input ──────────────────────────────────────────────────────────
    def type_char(self, char: str, t_ms: int) -> None:
        """Apply a single character keypress at time ``t_ms``."""
        if self.finished:
            return
        if len(char) != 1:
            raise ValueError("type_char expects exactly one character")

        expected = self.target[self._cursor]
        is_correct = char == expected
        self._states[self._cursor] = is_correct
        self._cursor += 1

        self._total_keystrokes += 1
        if is_correct:
            self._correct_keystrokes += 1

        self._record(t_ms)

    def backspace(self, t_ms: int) -> None:
        """Move the cursor back one position and clear that slot."""
        if not self.allow_backspace:
            return
        if self._cursor == 0:
            return
        self._cursor -= 1
        self._states[self._cursor] = None
        self._record(t_ms)

    # ── derived state ──────────────────────────────────────────────────
    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def states(self) -> list[bool | None]:
        """Read-only view of per-index correctness (for the UI to render)."""
        return list(self._states)

    @property
    def correct_chars(self) -> int:
        return sum(1 for s in self._states if s is True)

    @property
    def incorrect_chars(self) -> int:
        return sum(1 for s in self._states if s is False)

    @property
    def total_keystrokes(self) -> int:
        return self._total_keystrokes

    @property
    def correct_keystrokes(self) -> int:
        return self._correct_keystrokes

    @property
    def progress(self) -> float:
        """Completion fraction 0..1 based on cursor position."""
        return self._cursor / len(self.target)

    @property
    def finished(self) -> bool:
        return self._cursor >= len(self.target)

    def live_wpm(self, elapsed_ms: int) -> float:
        return wpm(self.correct_chars, elapsed_ms)

    def live_accuracy(self) -> float:
        return accuracy(self._correct_keystrokes, self._total_keystrokes)

    # ── timeline / result ──────────────────────────────────────────────
    def _record(self, t_ms: int) -> None:
        pct = round(self.progress * 100.0, 2)
        if pct != self._last_progress_pct:
            self._timeline.append(ReplayPoint(t_ms, pct))
            self._last_progress_pct = pct

    @property
    def timeline(self) -> list[ReplayPoint]:
        return list(self._timeline)

    def result(
        self,
        elapsed_ms: int,
        *,
        kind: RaceKind = RaceKind.QUOTE,
        mode_seconds: int = 0,
        ghost_kind: GhostKind | None = None,
        ghost_won: bool | None = None,
    ) -> RaceResult:
        """Snapshot the final result for an elapsed duration.

        ``mode_seconds`` is the time limit for TIME mode, or 0 for QUOTE mode.
        """
        return RaceResult(
            wpm=round(self.live_wpm(elapsed_ms), 2),
            raw_wpm=round(raw_wpm(self._total_keystrokes, elapsed_ms), 2),
            accuracy=round(self.live_accuracy(), 4),
            correct_chars=self.correct_chars,
            incorrect_chars=self.incorrect_chars,
            progress=round(self.progress, 4),
            duration_ms=elapsed_ms,
            mode_seconds=mode_seconds,
            kind=kind,
            timeline=self.timeline,
            ghost_kind=ghost_kind,
            ghost_won=ghost_won,
        )
