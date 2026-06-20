"""Unit tests for the pure typing engine."""

from __future__ import annotations

import pytest

from typefaster.domain.models import RaceKind
from typefaster.domain.typing_engine import TypingEngine


def _type(engine: TypingEngine, text: str, *, start_t: int = 0, step: int = 100) -> None:
    t = start_t
    for ch in text:
        engine.type_char(ch, t)
        t += step


def test_perfect_run() -> None:
    eng = TypingEngine("hello")
    _type(eng, "hello")
    assert eng.finished
    assert eng.correct_chars == 5
    assert eng.incorrect_chars == 0
    assert eng.progress == 1.0
    assert eng.live_accuracy() == pytest.approx(1.0)


def test_wrong_char_counts_against_accuracy() -> None:
    eng = TypingEngine("cat")
    eng.type_char("c", 0)
    eng.type_char("x", 100)  # wrong
    eng.type_char("t", 200)
    assert eng.correct_chars == 2
    assert eng.incorrect_chars == 1
    assert eng.total_keystrokes == 3
    assert eng.correct_keystrokes == 2
    assert eng.live_accuracy() == pytest.approx(2 / 3)


def test_backspace_corrects_buffer_but_not_accuracy() -> None:
    eng = TypingEngine("cat", allow_backspace=True)
    eng.type_char("c", 0)
    eng.type_char("x", 100)  # wrong
    eng.backspace(150)
    eng.type_char("a", 200)  # corrected
    eng.type_char("t", 300)
    assert eng.finished
    # Buffer is fully correct now...
    assert eng.correct_chars == 3
    assert eng.incorrect_chars == 0
    # ...but the original mistake still counts: 4 keystrokes, 3 correct.
    assert eng.total_keystrokes == 4
    assert eng.live_accuracy() == pytest.approx(3 / 4)


def test_key_stats_count_attempts_and_misses() -> None:
    eng = TypingEngine("cat")
    eng.type_char("c", 0)
    eng.type_char("x", 100)  # missed the 'a'
    eng.type_char("t", 200)
    # key 'a' was attempted once and missed once; 'c'/'t' clean.
    assert eng.key_stats["a"] == (1, 1)
    assert eng.key_stats["c"] == (1, 0)
    assert eng.key_stats["t"] == (1, 0)


def test_key_stats_count_corrected_mistakes() -> None:
    """A fumble counts as a miss even if backspaced and fixed."""
    eng = TypingEngine("cat", allow_backspace=True)
    eng.type_char("c", 0)
    eng.type_char("x", 100)  # wrong at 'a'
    eng.backspace(150)
    eng.type_char("a", 200)  # corrected: 'a' attempted twice now
    eng.type_char("t", 300)
    attempts, misses = eng.key_stats["a"]
    assert attempts == 2 and misses == 1


def test_key_stats_fold_case() -> None:
    eng = TypingEngine("Hi")
    eng.type_char("H", 0)
    eng.type_char("i", 100)
    assert "h" in eng.key_stats  # 'H' folded to 'h'
    assert "H" not in eng.key_stats


def test_backspace_disabled_is_noop() -> None:
    eng = TypingEngine("ab", allow_backspace=False)
    eng.type_char("a", 0)
    eng.backspace(50)
    assert eng.cursor == 1


def test_backspace_at_start_is_noop() -> None:
    eng = TypingEngine("ab")
    eng.backspace(0)
    assert eng.cursor == 0


def test_typing_past_end_is_ignored() -> None:
    eng = TypingEngine("hi")
    _type(eng, "hi")
    eng.type_char("x", 999)
    assert eng.total_keystrokes == 2


def test_timeline_starts_at_zero_and_grows() -> None:
    eng = TypingEngine("hi")
    eng.type_char("h", 100)
    eng.type_char("i", 200)
    tl = eng.timeline
    assert tl[0].t_ms == 0 and tl[0].progress_pct == 0.0
    assert tl[-1].progress_pct == 100.0


def test_result_snapshot() -> None:
    eng = TypingEngine("hello")
    _type(eng, "hello")
    result = eng.result(60_000, kind=RaceKind.TIME, mode_seconds=60)
    assert result.mode_seconds == 60
    assert result.kind is RaceKind.TIME
    assert result.correct_chars == 5
    assert result.completed
    assert result.wpm == pytest.approx(1.0)  # 5 chars = 1 word / 1 min


def test_empty_target_raises() -> None:
    with pytest.raises(ValueError):
        TypingEngine("")
