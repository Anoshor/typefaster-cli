# API Specification — TYPEFASTER Server (Phase 2)

Base URL: `https://<host>` (or `http://localhost:8000` in dev).
All bodies are JSON. Authenticated routes require `Authorization: Bearer <token>`.
Interactive docs are served at `/docs` (Swagger) and `/redoc`.

## Auth

### POST `/auth/register` → 201
Create an account and receive a token.
```json
// request
{ "username": "alice", "password": "hunter2hunter2" }
// response 201
{ "access_token": "<jwt>", "token_type": "bearer", "username": "alice" }
```
- `username`: 3–24 chars, `[A-Za-z0-9_]`.
- `password`: 8–128 chars.
- `409` if the username is taken.

### POST `/auth/login` → 200
```json
{ "username": "alice", "password": "hunter2hunter2" }
```
Returns the same `TokenResponse`. `401` on bad credentials.

### POST `/auth/logout` → 204
Header: `Authorization: Bearer <token>`. Revokes the token's server session
(idempotent; always 204).

### GET `/auth/me` → 200
```json
{ "username": "alice", "created_at": "2026-06-07T10:00:00+00:00",
  "races_played": 12, "best_wpm": 88.0 }
```

## Lobbies

### POST `/lobbies` → 201
```json
// request
{ "name": "Friday Sprint", "is_public": true, "mode_seconds": 60 }
// response
{ "code": "ABC123", "name": "Friday Sprint", "host": "alice",
  "is_public": true, "mode_seconds": 60, "status": "waiting", "player_count": 0 }
```
`mode_seconds` ∈ {30, 60, 120} (else 422).

### GET `/lobbies` → 200
List of joinable **public** lobbies (`LobbySummary[]`).

### GET `/lobbies/{code}` → 200
Full lobby state including players.
```json
{ "code": "ABC123", "name": "Friday Sprint", "host": "alice", "is_public": true,
  "mode_seconds": 60, "status": "waiting",
  "players": [ { "username": "alice", "ready": false, "progress": 0.0, "wpm": 0.0, "finished": false } ] }
```
`404` if unknown.

### POST `/lobbies/{code}/join` → 200
Validates the lobby is joinable (exists, `status=waiting`, not full) and returns
its `LobbySummary`. The player actually joins by opening the WebSocket
(see [websocket-protocol.md](websocket-protocol.md)). `404` unknown, `409` if
in-progress or full.

## Leaderboards

### GET `/leaderboards/{scope}` → 200
`scope` ∈ {`global`, `daily`, `weekly`}. Query: `limit` (1–100, default 20).
```json
{ "scope": "daily", "period": "2026-06-07",
  "entries": [ { "rank": 1, "username": "alice", "wpm": 92.0 } ] }
```
`global` has `period: null`. `404` for unknown scope.

## Health

| Route | Purpose | Codes |
|-------|---------|-------|
| `GET /healthz` | Liveness (process up) | 200 |
| `GET /readyz`  | Readiness (Redis reachable) | 200 / 503 |

## Errors
FastAPI's standard shape: `{ "detail": "<message>" }`. Common: `401`
(missing/expired token or bad credentials), `404`, `409`, `422` (validation).
