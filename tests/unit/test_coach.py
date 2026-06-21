"""Unit tests for the typing coach service and keyboard model."""

from __future__ import annotations

from typefaster.domain import keyboard
from typefaster.services.coach_service import CoachService


class _FakeRepo:
    """Minimal stand-in exposing just what CoachService reads."""

    def __init__(self, stats: dict[str, tuple[int, int]]) -> None:
        self._stats = stats

    def get_key_stats(self) -> dict[str, tuple[int, int]]:
        return self._stats


def _coach(stats: dict[str, tuple[int, int]]) -> CoachService:
    return CoachService(_FakeRepo(stats))  # type: ignore[arg-type]


def test_enough_data_threshold() -> None:
    assert _coach({"a": (10, 0), "b": (10, 0)}).enough_data() is False  # 20 < 50
    assert _coach({"a": (40, 0), "b": (20, 0)}).enough_data() is True  # 60 >= 50


def test_weakest_keys_ignores_low_attempt_keys() -> None:
    # 'z' has a terrible rate but only 3 attempts → filtered out.
    coach = _coach({"a": (100, 30), "z": (3, 3)})
    keys = [k.key for k in coach.weakest_keys(min_attempts=20)]
    assert keys == ["a"]


def test_weakest_keys_worst_first() -> None:
    coach = _coach({"a": (100, 50), "b": (100, 10), "c": (100, 30)})
    ranked = coach.weakest_keys(min_attempts=20)
    assert [k.key for k in ranked] == ["a", "c", "b"]  # 50% < 70% < 90% accuracy
    assert ranked[0].accuracy == 0.5


def test_heatmap_accuracy() -> None:
    heat = _coach({"a": (10, 1), "b": (4, 0)}).heatmap()
    assert heat["a"] == 0.9
    assert heat["b"] == 1.0


def test_keyboard_covers_letters_and_space() -> None:
    for ch in "abcdefghijklmnopqrstuvwxyz ":
        info = keyboard.key_info(ch)
        assert info is not None, ch
        assert info.finger and info.home_key and info.tip


def test_keyboard_folds_case_and_skips_digits() -> None:
    assert keyboard.key_info("R") == keyboard.key_info("r")
    assert keyboard.key_info("5") is None


def test_keyboard_home_row_tip() -> None:
    info = keyboard.key_info("f")
    assert info is not None
    assert "home row" in info.tip
