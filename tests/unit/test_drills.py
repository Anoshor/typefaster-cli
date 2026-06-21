"""Unit tests for adaptive drill generation."""

from __future__ import annotations

import random

import pytest

from typefaster.domain.drills import build_drill

_WORDS = ["the", "quick", "brown", "fox", "jazz", "zebra", "puzzle", "apple", "lion"]


def test_deterministic_with_seeded_rng() -> None:
    a = build_drill(["z"], _WORDS, length=10, rng=random.Random(1))
    b = build_drill(["z"], _WORDS, length=10, rng=random.Random(1))
    assert a == b


def test_respects_length() -> None:
    out = build_drill(["z"], _WORDS, length=15, rng=random.Random(0))
    assert len(out.split()) == 15


def test_biases_toward_weak_keys() -> None:
    # Weak key 'z' → z-words (jazz, zebra, puzzle) should dominate.
    out = build_drill(["z"], _WORDS, length=50, rng=random.Random(0))
    z_words = sum(1 for w in out.split() if "z" in w)
    assert z_words > 40


def test_no_weak_keys_falls_back_to_sample() -> None:
    out = build_drill([], _WORDS, length=10, rng=random.Random(0))
    assert len(out.split()) == 10


def test_space_only_weak_keys_falls_back() -> None:
    out = build_drill([" "], _WORDS, length=8, rng=random.Random(0))
    assert len(out.split()) == 8


def test_empty_words_raises() -> None:
    with pytest.raises(ValueError):
        build_drill(["z"], [], length=10)
