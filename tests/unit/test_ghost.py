"""Unit tests for ghost progress sampling."""

from __future__ import annotations

import pytest

from typefaster.domain.ghost import ghost_won, progress_at
from typefaster.domain.models import ReplayPoint

TL = [
    ReplayPoint(0, 0.0),
    ReplayPoint(1000, 25.0),
    ReplayPoint(2000, 50.0),
    ReplayPoint(4000, 100.0),
]


def test_progress_before_start() -> None:
    assert progress_at(TL, -50) == 0.0


def test_progress_after_end_clamps() -> None:
    assert progress_at(TL, 9999) == 100.0


def test_progress_exact_point() -> None:
    assert progress_at(TL, 1000) == 25.0


def test_progress_interpolated() -> None:
    # Halfway between 2000ms (50%) and 4000ms (100%) -> 75%.
    assert progress_at(TL, 3000) == pytest.approx(75.0)


def test_progress_empty_timeline() -> None:
    assert progress_at([], 1000) == 0.0


def test_ghost_won_true() -> None:
    # Ghost reaches 100% at 4000ms; player took 5000ms.
    assert ghost_won(TL, 5000) is True


def test_ghost_won_false() -> None:
    assert ghost_won(TL, 3000) is False


def test_ghost_won_never_finished() -> None:
    partial = [ReplayPoint(0, 0.0), ReplayPoint(1000, 40.0)]
    assert ghost_won(partial, 5000) is False
