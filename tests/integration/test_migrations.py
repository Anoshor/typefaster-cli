"""Integration tests for schema migrations."""

from __future__ import annotations

from pathlib import Path

from typefaster.infra.db import connect
from typefaster.infra.migrations import migrate
from typefaster.infra.quote_loader import seed_quotes


def test_migrate_fresh_db(tmp_path: Path) -> None:
    conn = connect(tmp_path / "m.db")
    version = migrate(conn)
    assert version == 2
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"profile", "quote", "race", "replay", "daily_challenge", "schema_meta"} <= tables
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(race)")}
    assert "race_kind" in cols
    conn.close()


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    conn = connect(tmp_path / "m.db")
    assert migrate(conn) == 2
    assert migrate(conn) == 2  # second run no-ops
    conn.close()


def test_seed_populates_quote_table(tmp_path: Path) -> None:
    conn = connect(tmp_path / "m.db")
    migrate(conn)
    seed_quotes(conn)
    count = conn.execute("SELECT COUNT(*) AS c FROM quote").fetchone()["c"]
    assert count > 0
    conn.close()
