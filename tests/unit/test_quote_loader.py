"""Unit tests for the quote dataset and seed logic."""

from __future__ import annotations

from pathlib import Path

from typefaster.domain.models import Difficulty
from typefaster.infra import quote_loader
from typefaster.infra.db import connect
from typefaster.infra.migrations import migrate


def test_dataset_meets_minimum() -> None:
    assert len(quote_loader.all_quotes()) >= 500


def test_no_duplicate_text() -> None:
    texts = [q.text for q in quote_loader.all_quotes()]
    assert len(set(texts)) == len(texts)


def test_difficulty_buckets_exist() -> None:
    diffs = {q.difficulty for q in quote_loader.all_quotes()}
    assert Difficulty.SHORT in diffs


def test_seed_quotes_inserts_all(tmp_path: Path) -> None:
    conn = connect(tmp_path / "seed.db")
    migrate(conn)
    inserted = quote_loader.seed_quotes(conn)
    count = conn.execute("SELECT COUNT(*) AS c FROM quote").fetchone()["c"]
    assert count == len(quote_loader.all_quotes())
    assert inserted == count
    conn.close()


def test_seed_quotes_is_idempotent(tmp_path: Path) -> None:
    conn = connect(tmp_path / "seed.db")
    migrate(conn)
    first = quote_loader.seed_quotes(conn)
    second = quote_loader.seed_quotes(conn)
    count = conn.execute("SELECT COUNT(*) AS c FROM quote").fetchone()["c"]
    assert first > 0
    assert second == 0  # all already present, INSERT OR IGNORE skips them
    assert count == first
    conn.close()
