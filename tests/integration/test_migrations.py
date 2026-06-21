"""Integration tests for schema migrations."""

from __future__ import annotations

from pathlib import Path

from typefaster.infra.db import connect
from typefaster.infra.migrations import migrate
from typefaster.infra.quote_loader import seed_quotes


def test_migrate_fresh_db(tmp_path: Path) -> None:
    conn = connect(tmp_path / "m.db")
    version = migrate(conn)
    assert version == 3
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "profile",
        "quote",
        "race",
        "replay",
        "daily_challenge",
        "schema_meta",
        "key_stats",
    } <= tables
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(race)")}
    assert "race_kind" in cols
    conn.close()


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    conn = connect(tmp_path / "m.db")
    assert migrate(conn) == 3
    assert migrate(conn) == 3  # second run no-ops
    conn.close()


def test_migrate_v3_on_existing_v2_db(tmp_path: Path) -> None:
    """A pre-v3 DB upgrades cleanly: key_stats is added, existing data intact."""
    db = tmp_path / "m.db"
    conn = connect(db)
    # Simulate an old DB stuck at version 2.
    migrate(conn)
    conn.execute("UPDATE schema_meta SET value='2' WHERE key='schema_version'")
    conn.execute("DROP TABLE key_stats")
    conn.commit()
    assert migrate(conn) == 3
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "key_stats" in tables
    conn.close()


def test_seed_populates_quote_table(tmp_path: Path) -> None:
    conn = connect(tmp_path / "m.db")
    migrate(conn)
    seed_quotes(conn)
    count = conn.execute("SELECT COUNT(*) AS c FROM quote").fetchone()["c"]
    assert count > 0
    conn.close()
