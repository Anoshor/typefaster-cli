"""Unit tests for the typing-speed/accuracy math."""

from __future__ import annotations

import pytest

from typefaster.domain import calculators as calc


def test_wpm_basic() -> None:
    # 50 correct chars = 10 words; over 60s = 10 wpm.
    assert calc.wpm(50, 60_000) == pytest.approx(10.0)


def test_wpm_half_minute() -> None:
    # 25 chars = 5 words over 30s = 10 wpm.
    assert calc.wpm(25, 30_000) == pytest.approx(10.0)


def test_raw_wpm_includes_errors() -> None:
    assert calc.raw_wpm(100, 60_000) == pytest.approx(20.0)


def test_accuracy() -> None:
    assert calc.accuracy(95, 100) == pytest.approx(0.95)


def test_zero_guards() -> None:
    assert calc.wpm(50, 0) == 0.0
    assert calc.raw_wpm(50, 0) == 0.0
    assert calc.accuracy(0, 0) == 0.0
    assert calc.wpm(0, 60_000) == 0.0
