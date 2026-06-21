"""Unit tests for the quote dataset and seed logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from typefaster.domain.models import Difficulty
from typefaster.infra import quote_loader
from typefaster.infra.db import connect
from typefaster.infra.migrations import migrate


@pytest.fixture()
def seeded_conn(tmp_path: Path):
    conn = connect(tmp_path / "seed.db")
    migrate(conn)
    quote_loader.seed_quotes(conn)
    yield conn
    conn.close()


def test_dataset_meets_minimum(seeded_conn) -> None:
    count = seeded_conn.execute("SELECT COUNT(*) AS c FROM quote").fetchone()["c"]
    assert count >= 500


def test_no_duplicate_text(seeded_conn) -> None:
    rows = seeded_conn.execute("SELECT text FROM quote").fetchall()
    texts = [r["text"] for r in rows]
    assert len(set(texts)) == len(texts)


def test_difficulty_buckets_exist(seeded_conn) -> None:
    rows = seeded_conn.execute("SELECT DISTINCT difficulty FROM quote").fetchall()
    diffs = {r["difficulty"] for r in rows}
    assert Difficulty.SHORT.value in diffs


def test_seed_quotes_inserts_all(tmp_path: Path) -> None:
    conn = connect(tmp_path / "seed.db")
    migrate(conn)
    inserted = quote_loader.seed_quotes(conn)
    count = conn.execute("SELECT COUNT(*) AS c FROM quote").fetchone()["c"]
    assert count == inserted
    assert count >= 500
    conn.close()


def test_seed_quotes_is_idempotent(tmp_path: Path) -> None:
    conn = connect(tmp_path / "seed.db")
    migrate(conn)
    first = quote_loader.seed_quotes(conn)
    second = quote_loader.seed_quotes(conn)
    count = conn.execute("SELECT COUNT(*) AS c FROM quote").fetchone()["c"]
    assert first > 0
    assert second == 0
    assert count == first
    conn.close()
