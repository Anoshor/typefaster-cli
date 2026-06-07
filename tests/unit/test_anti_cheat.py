"""Unit tests for offline plausibility checks."""

from __future__ import annotations

from typefaster.domain import anti_cheat


def test_normal_run_is_clean() -> None:
    # 100 chars in 40s ≈ 30 WPM — clearly human.
    suspicious, reasons = anti_cheat.evaluate(
        wpm=30, raw_wpm=33, duration_ms=40_000, total_keystrokes=103, quote_length=100
    )
    assert not suspicious
    assert reasons == ()


def test_fast_but_human_is_clean() -> None:
    # 110 WPM is fast but legitimate.
    suspicious, _ = anti_cheat.evaluate(
        wpm=110, raw_wpm=120, duration_ms=30_000, total_keystrokes=290, quote_length=275
    )
    assert not suspicious


def test_paste_flagged() -> None:
    suspicious, reasons = anti_cheat.evaluate(
        wpm=30, raw_wpm=30, duration_ms=40_000, total_keystrokes=100, quote_length=100, pasted=True
    )
    assert suspicious
    assert "paste detected" in reasons


def test_the_2222_bug_is_flagged() -> None:
    # The exact pathological case: 117 chars in 0.6s -> ~2222 WPM.
    suspicious, reasons = anti_cheat.evaluate(
        wpm=2222, raw_wpm=2335, duration_ms=600, total_keystrokes=119, quote_length=117
    )
    assert suspicious
    assert "impossible WPM" in reasons
    assert "superhuman cadence" in reasons
    assert "impossible completion time" in reasons
