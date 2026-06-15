"""SQLite implementation of the Repository port."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ..domain.models import (
    DailyChallenge,
    GhostKind,
    Profile,
    Quote,
    RaceKind,
    RaceRecord,
    RaceResult,
    ReplayPoint,
)
from . import replay_store
from .db import connect, transaction
from .migrations import migrate
from .paths import db_path

# Ghosts and leaderboards ignore runs above this (paste/auto-input artifacts).
MAX_PLAUSIBLE_WPM = 300.0


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SQLiteRepository:
    """All offline persistence behind one adapter."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._conn = connect(path or db_path())
        migrate(self._conn)
        self._ensure_profile()

    # ── lifecycle ──────────────────────────────────────────────────────
    def close(self) -> None:
        self._conn.close()

    def _ensure_profile(self) -> None:
        row = self._conn.execute("SELECT id FROM profile WHERE id = 1").fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO profile(id, display_name, created_at) VALUES(1, 'you', ?)",
                (_utc_now_iso(),),
            )

    # ── profile ────────────────────────────────────────────────────────
    def get_profile(self) -> Profile:
        r = self._conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
        return Profile(
            display_name=r["display_name"],
            created_at=r["created_at"],
            races_played=r["races_played"],
            races_won=r["races_won"],
            best_wpm=r["best_wpm"],
            best_accuracy=r["best_accuracy"],
            total_chars=r["total_chars"],
            total_time_ms=r["total_time_ms"],
        )

    def recompute_profile(self) -> Profile:
        agg = self._conn.execute("""
            SELECT
              COUNT(*)                            AS races_played,
              COALESCE(SUM(ghost_won), 0)         AS races_won,
              COALESCE(MAX(wpm), 0)               AS best_wpm,
              COALESCE(MAX(accuracy), 0)          AS best_accuracy,
              COALESCE(SUM(correct_chars + incorrect_chars), 0) AS total_chars,
              COALESCE(SUM(duration_ms), 0)       AS total_time_ms
            FROM race
            """).fetchone()
        with transaction(self._conn):
            self._conn.execute(
                """
                UPDATE profile SET
                  races_played = ?, races_won = ?, best_wpm = ?,
                  best_accuracy = ?, total_chars = ?, total_time_ms = ?
                WHERE id = 1
                """,
                (
                    agg["races_played"],
                    agg["races_won"],
                    agg["best_wpm"],
                    agg["best_accuracy"],
                    agg["total_chars"],
                    agg["total_time_ms"],
                ),
            )
        return self.get_profile()

    def delete_implausible_races(self, max_wpm: float = 300.0) -> int:
        """Remove races with an impossible WPM (e.g. legacy paste artifacts) and
        recompute aggregates. Returns the number of rows removed."""
        with transaction(self._conn):
            cur = self._conn.execute("DELETE FROM race WHERE wpm > ?", (max_wpm,))
            removed = cur.rowcount
        self.recompute_profile()
        return int(removed)

    def wipe(self) -> None:
        """Delete all local race data and reset profile aggregates."""
        with transaction(self._conn):
            self._conn.execute("DELETE FROM race")
            self._conn.execute("DELETE FROM daily_challenge")
            self._conn.execute("DELETE FROM key_stats")
        self.recompute_profile()

    # ── quotes ─────────────────────────────────────────────────────────
    def upsert_quote(self, quote: Quote) -> int:
        self._conn.execute(
            """
            INSERT INTO quote(ext_id, text, source, length, difficulty)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(ext_id) DO UPDATE SET text=excluded.text, source=excluded.source
            """,
            (quote.ext_id, quote.text, quote.source, quote.length, quote.difficulty.value),
        )
        row = self._conn.execute(
            "SELECT id FROM quote WHERE ext_id = ?", (quote.ext_id,)
        ).fetchone()
        return int(row["id"])

    # ── races ──────────────────────────────────────────────────────────
    def save_race(
        self,
        *,
        result: RaceResult,
        quote: Quote,
        started_at: str,
        is_daily: bool = False,
    ) -> int:
        quote_id = self.upsert_quote(quote)
        with transaction(self._conn):
            cur = self._conn.execute(
                """
                INSERT INTO race(
                  profile_id, quote_id, mode_seconds, started_at, duration_ms,
                  wpm, raw_wpm, accuracy, correct_chars, incorrect_chars, progress,
                  is_daily, ghost_kind, ghost_won, race_kind
                ) VALUES(1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    quote_id,
                    result.mode_seconds,
                    started_at,
                    result.duration_ms,
                    result.wpm,
                    result.raw_wpm,
                    result.accuracy,
                    result.correct_chars,
                    result.incorrect_chars,
                    result.progress,
                    int(is_daily),
                    result.ghost_kind.value if result.ghost_kind else None,
                    None if result.ghost_won is None else int(result.ghost_won),
                    result.kind.value,
                ),
            )
            row_id = cur.lastrowid
            assert row_id is not None
            race_id = int(row_id)
            self._conn.execute(
                "INSERT INTO replay(race_id, timeline) VALUES(?, ?)",
                (race_id, replay_store.serialize(result.timeline)),
            )
            self._bump_profile(result)
            self._bump_key_stats(result.key_stats, started_at)
            if is_daily:
                self._bump_daily(started_at[:10], quote_id, result.wpm)
        return race_id

    def _bump_key_stats(self, key_stats: dict[str, tuple[int, int]], updated_at: str) -> None:
        """Add this race's per-key attempts/misses into the running aggregate."""
        for key_char, (attempts, misses) in key_stats.items():
            self._conn.execute(
                """
                INSERT INTO key_stats(key_char, attempts, misses, updated_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(key_char) DO UPDATE SET
                  attempts   = attempts + excluded.attempts,
                  misses     = misses + excluded.misses,
                  updated_at = excluded.updated_at
                """,
                (key_char, attempts, misses, updated_at),
            )

    def record_key_stats(self, key_stats: dict[str, tuple[int, int]], updated_at: str) -> None:
        """Standalone per-key update (used by drills, which feed the coach but
        are not recorded as competitive races)."""
        with transaction(self._conn):
            self._bump_key_stats(key_stats, updated_at)

    def get_key_stats(self) -> dict[str, tuple[int, int]]:
        rows = self._conn.execute("SELECT key_char, attempts, misses FROM key_stats").fetchall()
        return {r["key_char"]: (r["attempts"], r["misses"]) for r in rows}

    def _bump_profile(self, result: RaceResult) -> None:
        won = 1 if result.ghost_won else 0
        self._conn.execute(
            """
            UPDATE profile SET
              races_played  = races_played + 1,
              races_won     = races_won + ?,
              best_wpm      = MAX(best_wpm, ?),
              best_accuracy = MAX(best_accuracy, ?),
              total_chars   = total_chars + ?,
              total_time_ms = total_time_ms + ?
            WHERE id = 1
            """,
            (
                won,
                result.wpm,
                result.accuracy,
                result.correct_chars + result.incorrect_chars,
                result.duration_ms,
            ),
        )

    def list_history(self, limit: int = 20, offset: int = 0) -> list[RaceRecord]:
        rows = self._conn.execute(
            """
            SELECT r.*, q.source AS quote_source
            FROM race r JOIN quote q ON q.id = r.quote_id
            ORDER BY r.started_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [self._to_record(r) for r in rows]

    def count_races(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS c FROM race").fetchone()["c"])

    def average_wpm_accuracy(self) -> tuple[float, float]:
        r = self._conn.execute("SELECT AVG(wpm) AS w, AVG(accuracy) AS a FROM race").fetchone()
        return (float(r["w"] or 0.0), float(r["a"] or 0.0))

    def best_by_mode(self, kind: RaceKind = RaceKind.TIME) -> dict[int, float]:
        rows = self._conn.execute(
            "SELECT mode_seconds, MAX(wpm) AS best FROM race WHERE race_kind = ? "
            "GROUP BY mode_seconds",
            (kind.value,),
        ).fetchall()
        return {int(r["mode_seconds"]): float(r["best"]) for r in rows}

    def best_quote_run(self) -> tuple[float, int] | None:
        """Best (wpm, fastest duration_ms) across completed quote-mode races."""
        row = self._conn.execute(
            """
            SELECT MAX(wpm) AS best_wpm,
                   MIN(CASE WHEN progress >= 1.0 THEN duration_ms END) AS best_ms
            FROM race WHERE race_kind = ?
            """,
            (RaceKind.QUOTE.value,),
        ).fetchone()
        if row is None or row["best_wpm"] is None:
            return None
        return (float(row["best_wpm"]), int(row["best_ms"] or 0))

    def top_runs(
        self, mode_seconds: int, limit: int = 10, kind: RaceKind = RaceKind.TIME
    ) -> list[RaceRecord]:
        rows = self._conn.execute(
            """
            SELECT r.*, q.source AS quote_source
            FROM race r JOIN quote q ON q.id = r.quote_id
            WHERE r.race_kind = ? AND r.mode_seconds = ?
            ORDER BY r.wpm DESC
            LIMIT ?
            """,
            (kind.value, mode_seconds, limit),
        ).fetchall()
        return [self._to_record(r) for r in rows]

    def top_quote_runs(self, limit: int = 10) -> list[RaceRecord]:
        rows = self._conn.execute(
            """
            SELECT r.*, q.source AS quote_source
            FROM race r JOIN quote q ON q.id = r.quote_id
            WHERE r.race_kind = ?
            ORDER BY r.wpm DESC
            LIMIT ?
            """,
            (RaceKind.QUOTE.value, limit),
        ).fetchall()
        return [self._to_record(r) for r in rows]

    # ── ghosts ─────────────────────────────────────────────────────────
    # Only completed, plausible QUOTE-mode races make valid ghosts (same text,
    # human speed), so a ghost is always a fair head-to-head on identical text.
    def _replay_for(
        self, where_order: str, params: tuple[object, ...] = ()
    ) -> tuple[list[ReplayPoint], float, Quote] | None:
        row = self._conn.execute(
            f"""
            SELECT rp.timeline, r.wpm, q.ext_id, q.text, q.source
            FROM race r
            JOIN replay rp ON rp.race_id = r.id
            JOIN quote q ON q.id = r.quote_id
            WHERE r.race_kind = 'quote' AND r.progress >= 1.0 AND r.wpm <= {MAX_PLAUSIBLE_WPM}
            {where_order}
            LIMIT 1
            """,
            params,
        ).fetchone()
        if row is None:
            return None
        quote = Quote(ext_id=row["ext_id"], text=row["text"], source=row["source"])
        return replay_store.deserialize(row["timeline"]), float(row["wpm"]), quote

    def personal_best_replay(self) -> tuple[list[ReplayPoint], float, Quote] | None:
        return self._replay_for("ORDER BY r.wpm DESC")

    def last_replay(self) -> tuple[list[ReplayPoint], float, Quote] | None:
        return self._replay_for("ORDER BY r.started_at DESC")

    def random_replay(self) -> tuple[list[ReplayPoint], float, Quote] | None:
        return self._replay_for("ORDER BY RANDOM()")

    def best_replay_for_quote(self, ext_id: str) -> tuple[list[ReplayPoint], float, Quote] | None:
        """Best ghost recorded on a specific quote (used by the daily challenge)."""
        return self._replay_for("AND q.ext_id = ? ORDER BY r.wpm DESC", (ext_id,))

    # ── daily ──────────────────────────────────────────────────────────
    def get_or_create_daily(self, day: str, quote: Quote) -> DailyChallenge:
        quote_id = self.upsert_quote(quote)
        row = self._conn.execute("SELECT * FROM daily_challenge WHERE day = ?", (day,)).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO daily_challenge(day, quote_id) VALUES(?, ?)",
                (day, quote_id),
            )
            return DailyChallenge(day=day, quote=quote)
        return DailyChallenge(
            day=day, quote=quote, best_wpm=float(row["best_wpm"]), attempts=int(row["attempts"])
        )

    def _bump_daily(self, day: str, quote_id: int, wpm: float) -> None:
        self._conn.execute(
            """
            INSERT INTO daily_challenge(day, quote_id, best_wpm, attempts)
            VALUES(?, ?, ?, 1)
            ON CONFLICT(day) DO UPDATE SET
              best_wpm = MAX(best_wpm, excluded.best_wpm),
              attempts = attempts + 1
            """,
            (day, quote_id, wpm),
        )

    def daily_leaderboard(self, day: str, limit: int = 20) -> list[RaceRecord]:
        rows = self._conn.execute(
            """
            SELECT r.*, q.source AS quote_source
            FROM race r JOIN quote q ON q.id = r.quote_id
            WHERE r.is_daily = 1 AND substr(r.started_at, 1, 10) = ?
            ORDER BY r.wpm DESC
            LIMIT ?
            """,
            (day, limit),
        ).fetchall()
        return [self._to_record(r) for r in rows]

    # ── helpers ────────────────────────────────────────────────────────
    @staticmethod
    def _to_record(r: sqlite3.Row) -> RaceRecord:
        return RaceRecord(
            id=int(r["id"]),
            quote_source=r["quote_source"],
            mode_seconds=int(r["mode_seconds"]),
            started_at=r["started_at"],
            duration_ms=int(r["duration_ms"]),
            wpm=float(r["wpm"]),
            raw_wpm=float(r["raw_wpm"]),
            accuracy=float(r["accuracy"]),
            correct_chars=int(r["correct_chars"]),
            incorrect_chars=int(r["incorrect_chars"]),
            progress=float(r["progress"]),
            is_daily=bool(r["is_daily"]),
            ghost_kind=GhostKind(r["ghost_kind"]) if r["ghost_kind"] else None,
            ghost_won=None if r["ghost_won"] is None else bool(r["ghost_won"]),
            kind=RaceKind(r["race_kind"]),  # column always present after migration v2
        )
