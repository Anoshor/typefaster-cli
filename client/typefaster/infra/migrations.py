"""Ordered schema migrations, versioned via the ``schema_meta`` table."""

from __future__ import annotations

import sqlite3

# Each migration is (version, SQL). Applied in order; never edit a shipped one.
_MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS profile (
            id            INTEGER PRIMARY KEY CHECK (id = 1),
            display_name  TEXT NOT NULL DEFAULT 'you',
            created_at    TEXT NOT NULL,
            races_played  INTEGER NOT NULL DEFAULT 0,
            races_won     INTEGER NOT NULL DEFAULT 0,
            best_wpm      REAL    NOT NULL DEFAULT 0,
            best_accuracy REAL    NOT NULL DEFAULT 0,
            total_chars   INTEGER NOT NULL DEFAULT 0,
            total_time_ms INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS quote (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_id     TEXT UNIQUE,
            text       TEXT NOT NULL,
            source     TEXT,
            length     INTEGER NOT NULL,
            difficulty TEXT
        );

        CREATE TABLE IF NOT EXISTS race (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id      INTEGER NOT NULL REFERENCES profile(id),
            quote_id        INTEGER NOT NULL REFERENCES quote(id),
            mode_seconds    INTEGER NOT NULL,
            started_at      TEXT NOT NULL,
            duration_ms     INTEGER NOT NULL,
            wpm             REAL NOT NULL,
            raw_wpm         REAL NOT NULL,
            accuracy        REAL NOT NULL,
            correct_chars   INTEGER NOT NULL,
            incorrect_chars INTEGER NOT NULL,
            progress        REAL NOT NULL,
            is_daily        INTEGER NOT NULL DEFAULT 0,
            ghost_kind      TEXT,
            ghost_won       INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_race_profile_time ON race(profile_id, started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_race_wpm          ON race(profile_id, wpm DESC);
        CREATE INDEX IF NOT EXISTS idx_race_daily        ON race(is_daily, started_at);

        CREATE TABLE IF NOT EXISTS replay (
            race_id  INTEGER PRIMARY KEY REFERENCES race(id) ON DELETE CASCADE,
            timeline TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_challenge (
            day      TEXT PRIMARY KEY,
            quote_id INTEGER NOT NULL REFERENCES quote(id),
            best_wpm REAL NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0
        );
        """,
    ),
    (
        2,
        # Distinguish quote-mode (finish one text) from time-mode (type for N s).
        # Existing rows predate the split and were single-quote races.
        """
        ALTER TABLE race ADD COLUMN race_kind TEXT NOT NULL DEFAULT 'quote';
        CREATE INDEX IF NOT EXISTS idx_race_kind_wpm ON race(race_kind, mode_seconds, wpm DESC);
        """,
    ),
    (
        3,
        # Running per-key (case-folded) attempt/miss aggregate for the typing
        # coach. One row per key; upserted after every race. Local-only.
        """
        CREATE TABLE IF NOT EXISTS key_stats (
            key_char   TEXT PRIMARY KEY,
            attempts   INTEGER NOT NULL DEFAULT 0,
            misses     INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        );
        """,
    ),
]


def _current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_meta'"
    ).fetchone()
    if row is None:
        return 0
    cur = conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
    return int(cur["value"]) if cur else 0


def migrate(conn: sqlite3.Connection) -> int:
    """Apply all pending migrations. Returns the resulting schema version."""
    version = _current_version(conn)
    for target, sql in _MIGRATIONS:
        if target > version:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(target),),
            )
            version = target
    return version
