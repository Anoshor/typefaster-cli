"""Unit tests for the quote dataset and selection logic."""

from __future__ import annotations

import random
from datetime import date

from typefaster.domain.models import Difficulty
from typefaster.infra import quote_loader


def test_dataset_meets_minimum() -> None:
    assert len(quote_loader.all_quotes()) >= 500


def test_no_duplicate_text() -> None:
    texts = [q.text for q in quote_loader.all_quotes()]
    assert len(set(texts)) == len(texts)


def test_random_is_seedable() -> None:
    a = quote_loader.random_quote(random.Random(1))
    b = quote_loader.random_quote(random.Random(1))
    assert a.ext_id == b.ext_id


def test_difficulty_buckets_exist() -> None:
    diffs = {q.difficulty for q in quote_loader.all_quotes()}
    assert Difficulty.SHORT in diffs


def test_daily_is_deterministic_per_day() -> None:
    day = date(2026, 6, 7)
    assert quote_loader.daily_quote(day).ext_id == quote_loader.daily_quote(day).ext_id


def test_daily_differs_across_days() -> None:
    a = quote_loader.daily_quote(date(2026, 6, 7))
    b = quote_loader.daily_quote(date(2026, 6, 8))
    # Not guaranteed different, but extremely likely for these two dates.
    assert a.ext_id != b.ext_id
