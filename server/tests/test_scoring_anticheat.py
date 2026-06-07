"""Pure tests for shared scoring and anti-cheat."""

from __future__ import annotations

import pytest
from typefaster_shared import anti_cheat, scoring


def test_wpm() -> None:
    assert scoring.wpm(50, 60_000) == pytest.approx(10.0)


def test_accuracy() -> None:
    assert scoring.accuracy(90, 100) == pytest.approx(0.9)
    assert scoring.accuracy(0, 0) == 0.0


def test_clean_result_passes() -> None:
    report = anti_cheat.evaluate(
        wpm=85,
        raw_wpm=92,
        duration_ms=60_000,
        total_keystrokes=440,
        quote_length=420,
        correct_chars=410,
    )
    assert report.ok
    assert report.reasons == ()


def test_paste_flagged() -> None:
    report = anti_cheat.evaluate(
        wpm=85,
        raw_wpm=92,
        duration_ms=60_000,
        total_keystrokes=440,
        quote_length=420,
        correct_chars=410,
        pasted=True,
    )
    assert report.suspicious
    assert "paste_detected" in report.reasons


def test_impossible_wpm_flagged() -> None:
    report = anti_cheat.evaluate(
        wpm=400,
        raw_wpm=410,
        duration_ms=10_000,
        total_keystrokes=400,
        quote_length=300,
        correct_chars=300,
    )
    assert report.suspicious
    assert "impossible_wpm" in report.reasons


def test_superhuman_cadence_flagged() -> None:
    report = anti_cheat.evaluate(
        wpm=120,
        raw_wpm=130,
        duration_ms=200,
        total_keystrokes=100,
        quote_length=100,
        correct_chars=100,
    )
    assert report.suspicious
    assert "superhuman_cadence" in report.reasons
