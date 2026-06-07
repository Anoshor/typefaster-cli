# WebSocket Protocol — TYPEFASTER (Phase 2)

Endpoint: `wss://<host>/ws/lobby/{code}?token=<jwt>`

- The token is validated on connect; an invalid/expired token closes the socket
  with code `4401`. An unknown lobby closes with `4404`.
- Every frame is a JSON **envelope**:
  ```json
  { "type": "<EVENT>", "ts": 1749300000.12, "data": { ... } }
  ```
- The **server is authoritative** for race timing. Clients never start or stop a
  race; they only ready up, report progress, and submit a final result, which
  the server re-scores and validates.

## Client → Server commands

| `type` | `data` | Meaning |
|--------|--------|---------|
| `SET_READY` | `{ "ready": true }` | Toggle ready. When all players are ready the server begins the race. |
| `PROGRESS` | `{ "progress": 0-100, "wpm": float }` | Live position update (sent a few times/sec). |
| `FINISH` | `{ "duration_ms", "correct_chars", "incorrect_chars", "total_keystrokes", "correct_keystrokes", "pasted" }` | Final result for server validation. |
| `CHAT` | `{ "message": "gg" }` | Lobby chat. |
| `LEAVE` | `{}` | Leave the lobby. |

## Server → Client events

| `type` | `data` (example) | When |
|--------|------------------|------|
| `PLAYER_JOINED` | `{ "username": "bob" }` | A player connects. |
| `PLAYER_LEFT` | `{ "username": "bob" }` | A player disconnects/leaves. |
| `HOST_CHANGED` | `{ "host": "carol" }` | Host left; host transferred. |
| `READY_STATE` | `{ "username": "bob", "ready": true }` | A player's ready flag changed. |
| `LOBBY_UPDATE` | `{ "code", "name", "host", "status", "mode_seconds", "players": [PlayerState] }` | Full lobby snapshot after any change. |
| `RACE_COUNTDOWN` | `{ "count": 3 }` | Per-second countdown (3,2,1). |
| `RACE_START` | `{ "quote_id", "text", "mode_seconds", "server_start_ms" }` | Race begins; clients start typing. |
| `RACE_PROGRESS` | `{ "username", "progress", "wpm" }` | Relayed opponent progress. |
| `RACE_FINISHED` (per-player) | `{ "username", "wpm", "accuracy", "suspicious", "flags": [] }` | A player finished. |
| `RACE_FINISHED` (final) | `{ "final": true, "standings": [ { "username","wpm","accuracy","suspicious","flags" } ] }` | Race over (time up or all finished). |
| `CHAT_MESSAGE` | `{ "username", "message" }` | Chat relay. |
| `DAILY_CHALLENGE_UPDATE` | `{ "day", "quote_id" }` | (Reserved) daily challenge change. |
| `ERROR` | `{ "message": "Lobby not found" }` | Recoverable error. |

## Typical flow

```text
client                         server
  | --- connect (?token) ----->|  validate token
  | <-- PLAYER_JOINED ---------|
  | <-- LOBBY_UPDATE ----------|
  | --- SET_READY{ready} ----->|  (all ready?)
  | <-- RACE_COUNTDOWN 3,2,1 --|
  | <-- RACE_START{text,...} --|  status=racing
  | --- PROGRESS (xN) -------->|
  | <-- RACE_PROGRESS (peers) -|
  | --- FINISH{...} ---------->|  re-score + anti-cheat + leaderboard write
  | <-- RACE_FINISHED (you) ---|
  | <-- RACE_FINISHED final ---|  standings; lobby resets to waiting
```

## Validation & anti-cheat
On `FINISH` the server recomputes WPM/accuracy from the raw counts
(`shared/typefaster_shared/scoring.py`) and runs heuristics
(`anti_cheat.py`): paste, impossible WPM/burst, superhuman cadence, impossible
completion time, char overcount. A flagged result is reported with
`suspicious: true` and its `flags`, and is **excluded** from leaderboards.
