# SQLite Schema (Offline Mode) — TYPEFASTER-CLI

Single-file database at the OS data dir (via `platformdirs`), e.g.
`~/.local/share/typefaster/typefaster.db`. WAL mode for durability + concurrent reads.
Schema is versioned through `schema_meta` and upgraded by ordered migrations.

## DDL

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── meta: migration version tracking ──────────────────
CREATE TABLE schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);  -- ('schema_version','1')

-- ── local profile (singleton offline; multi-row ready) ──
CREATE TABLE profile (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    display_name  TEXT NOT NULL DEFAULT 'you',
    created_at    TEXT NOT NULL,                 -- ISO-8601 UTC
    -- denormalized aggregates (fast stats; recomputable from race)
    races_played  INTEGER NOT NULL DEFAULT 0,
    races_won     INTEGER NOT NULL DEFAULT 0,    -- ghost wins (multiplayer in P2)
    best_wpm      REAL    NOT NULL DEFAULT 0,
    best_accuracy REAL    NOT NULL DEFAULT 0,
    total_chars   INTEGER NOT NULL DEFAULT 0,
    total_time_ms INTEGER NOT NULL DEFAULT 0
);

-- ── quotes that have been raced (cache of text used) ──
CREATE TABLE quote (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ext_id    TEXT UNIQUE,        -- stable id from quotes.json
    text      TEXT NOT NULL,
    source    TEXT,               -- author / origin
    length    INTEGER NOT NULL,   -- char count (difficulty bucket)
    difficulty TEXT               -- 'short' | 'medium' | 'long'
);

-- ── one row per completed race ────────────────────────
CREATE TABLE race (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id      INTEGER NOT NULL REFERENCES profile(id),
    quote_id        INTEGER NOT NULL REFERENCES quote(id),
    mode_seconds    INTEGER NOT NULL,           -- 30 | 60 | 120
    started_at      TEXT NOT NULL,              -- ISO-8601 UTC
    duration_ms     INTEGER NOT NULL,           -- actual elapsed
    wpm             REAL NOT NULL,
    raw_wpm         REAL NOT NULL,
    accuracy        REAL NOT NULL,              -- 0..1
    correct_chars   INTEGER NOT NULL,
    incorrect_chars INTEGER NOT NULL,
    progress        REAL NOT NULL,              -- 0..1 completion
    is_daily        INTEGER NOT NULL DEFAULT 0, -- bool
    ghost_kind      TEXT,                       -- NULL|'personal-best'|'last'|'random'
    ghost_won       INTEGER                     -- NULL if no ghost else bool
);
CREATE INDEX idx_race_profile_time ON race(profile_id, started_at DESC);
CREATE INDEX idx_race_wpm          ON race(profile_id, wpm DESC);
CREATE INDEX idx_race_daily        ON race(is_daily, started_at);

-- ── replay timeline for ghost races ───────────────────
CREATE TABLE replay (
    race_id  INTEGER PRIMARY KEY REFERENCES race(id) ON DELETE CASCADE,
    timeline TEXT NOT NULL    -- JSON: [{"t":1000,"p":5},{"t":2000,"p":10}, ...]
);

-- ── daily challenge bookkeeping (offline-local) ───────
CREATE TABLE daily_challenge (
    day      TEXT PRIMARY KEY,   -- 'YYYY-MM-DD' (UTC)
    quote_id INTEGER NOT NULL REFERENCES quote(id),
    best_wpm REAL NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0
);
```

## Replay timeline format

Matches the spec shape; stored compactly as `t`/`p` to keep JSON small.

```json
[
  { "t": 1000, "p": 5 },
  { "t": 2000, "p": 10 },
  { "t": 3000, "p": 18 }
]
```

- `t` — milliseconds since race start.
- `p` — completion progress as a percentage (0–100).

The ghost bar samples this timeline against the live race clock and interpolates
between points for smooth animation.

## Design notes

- **Aggregates on `profile`** are a cache. Every value is recomputable from `race`,
  and a `recompute_profile()` repair routine guards against drift.
- **Low-cardinality attributes** (`mode_seconds`, `is_daily`, `ghost_kind`) are columns,
  not lookup tables — simplest queries.
- **`replay`** is a separate table so large JSON blobs stay out of hot stats queries.
- **Versioning** via `schema_meta`; `migrations.py` applies ordered upgrades on launch.
- Phase 2 adds essentially nothing here (online state lives in Redis); at most a
  `synced` flag for opportunistic upload of offline runs.

## Example queries

```sql
-- Personal best WPM run (for the `personal-best` ghost)
SELECT r.id, r.wpm, rp.timeline
FROM race r JOIN replay rp ON rp.race_id = r.id
WHERE r.profile_id = 1
ORDER BY r.wpm DESC
LIMIT 1;

-- Last race (for the `last` ghost)
SELECT r.id, rp.timeline
FROM race r JOIN replay rp ON rp.race_id = r.id
WHERE r.profile_id = 1
ORDER BY r.started_at DESC
LIMIT 1;

-- Random historical run (for the `random` ghost)
SELECT r.id, rp.timeline
FROM race r JOIN replay rp ON rp.race_id = r.id
WHERE r.profile_id = 1
ORDER BY RANDOM()
LIMIT 1;

-- Today's local daily leaderboard (best per day)
SELECT r.wpm, r.accuracy, r.started_at
FROM race r
WHERE r.is_daily = 1 AND substr(r.started_at, 1, 10) = '2026-06-07'
ORDER BY r.wpm DESC
LIMIT 20;

-- Stats summary
SELECT races_played, races_won, best_wpm, best_accuracy,
       total_chars, total_time_ms
FROM profile WHERE id = 1;

-- Average WPM / accuracy (computed, not cached)
SELECT AVG(wpm) AS avg_wpm, AVG(accuracy) AS avg_accuracy
FROM race WHERE profile_id = 1;
```
