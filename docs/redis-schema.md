# Redis Schema (Online Mode) — TYPEFASTER

All keys are built in `server/app/redis_keys.py` so the data model lives in one
place. Values are stored as UTF-8 strings (the client connects with
`decode_responses=True`).

## Keys

| Key | Type | Fields / value | Purpose | TTL |
|-----|------|----------------|---------|-----|
| `user:{username}` | HASH | `password_hash`, `username`, `created_at`, `races_played`, `best_wpm` | Account + lifetime stats. Username lowercased in the key. | none |
| `session:{jti}` | STRING | `username` | Active token session, keyed by the JWT's `jti`. Deleted on logout → instant revocation. | = token lifetime |
| `lobby:{code}` | HASH | `name`, `host`, `is_public`, `mode_seconds`, `status`, `created_at` | Lobby metadata. `status` ∈ waiting/countdown/racing/finished. | none (deleted when empty) |
| `lobby:{code}:players` | HASH | `username` → JSON `PlayerState` | Players + their live race state. | none |
| `lobbies:public` | SET | lobby `code`s | Index of joinable public lobbies (only while `status=waiting`). | none |
| `race:{code}` | HASH | `quote_id`, `text`, `mode_seconds`, `start_ms`, `status` | Active race snapshot for a lobby. | none (overwritten each race) |
| `leaderboard:global` | ZSET | `username` → best WPM | All-time ranking. | none |
| `leaderboard:daily:{YYYY-MM-DD}` | ZSET | `username` → best WPM | Per-day ranking (UTC). | none* |
| `leaderboard:weekly:{YYYY-Www}` | ZSET | `username` → best WPM | Rolling ISO-week ranking. | none* |
| `ghost:{username}:pb` | STRING | JSON replay timeline | Personal-best ghost for online ghost races. | none |

\* Daily/weekly keys naturally age out of relevance; an optional cron can
`EXPIRE` old period keys to cap memory (see deployment guide).

## Notes

- **Best-score semantics:** scores are written with `ZADD ... GT`, so a member's
  entry only updates when the new WPM is higher.
- **`PlayerState` JSON** (in `lobby:{code}:players`):
  ```json
  { "username": "alice", "ready": true, "progress": 57.0, "wpm": 81.0, "finished": false }
  ```
- **Replay timeline JSON** (in `ghost:{username}:pb`): `[ {"t": 1000, "p": 5}, ... ]`
  — the same compact shape used by the offline SQLite store.
- **Atomicity:** lobby/race mutations are small single-key ops; the race loop is
  serialized per-lobby in the server's `Hub` (one asyncio task per lobby).
- **Persistence:** Redis runs with AOF (`everysec`) + RDB snapshots so users and
  leaderboards survive restarts (see `infra/redis/redis.conf`). Sessions and live
  race/lobby state are ephemeral by design.

## Capacity

For a single small VM this model comfortably handles thousands of users and
many concurrent lobbies. `maxmemory-policy volatile-lru` evicts only keys with a
TTL (sessions) under pressure, protecting durable account/leaderboard data.
