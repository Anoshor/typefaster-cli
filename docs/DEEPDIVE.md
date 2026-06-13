# TYPEFASTER — Deep Dive (learn how it's built)

A guided tour of the whole system: the Python stack, the architecture, the
server/microservice design, **how WebSockets and the lobby work**, the data
models, deployment, packaging, and CI/CD — with "why" and "what to learn next".

---

## 1. Big picture

Two deployable pieces, one shared language (Python):

```
┌──────────────────────────┐         REST (httpx)         ┌───────────────────────────┐
│   CLIENT (your terminal) │  ───────────────────────────►│   SERVER (Oracle VM)      │
│  Typer + Textual + Rich  │   WebSocket (websockets)     │  FastAPI + WebSockets     │
│  SQLite (local progress) │  ◄══════════════════════════►│  Redis (state)            │
└──────────────────────────┘                              └───────────────────────────┘
        offline-first                                       server-authoritative online
```

- **Offline-first**: the game is fully playable with zero network — local SQLite
  stores your races, ghosts, stats, daily challenge.
- **Online**: a small **stateless** FastAPI service + **Redis** holds users,
  sessions, lobbies, live race state, and leaderboards. The server is
  *authoritative*: it owns race timing and re-scores results.

---

## 2. The Python stack (and why each)

| Library | Role | Why |
|---|---|---|
| **Typer** | CLI (`typefaster …`) | Type-hint-driven commands, auto help/validation. Built on Click. |
| **Rich** | terminal rendering | Tables, colors, progress bars, markup. |
| **Textual** | the TUI app | An async, widget/event framework on top of Rich — screens, focus, key bindings, layout. This is what makes it feel like an app, not a script. |
| **SQLite** (stdlib) | local persistence | Zero-config single-file DB with transactions + migrations. |
| **Pydantic v2** | data models / validation | Request/response schemas; fast (Rust core); used across shared/server. |
| **FastAPI** | HTTP + WebSocket server | ASGI, async-native, dependency injection, auto OpenAPI docs. |
| **redis-py (asyncio)** | server state store | Fast in-memory data structures (hashes, sorted sets) — perfect for lobbies + leaderboards. |
| **httpx** | client REST | Sync + async HTTP with HTTP/2. |
| **websockets** | client realtime | Pure-Python WS client used by the race screen. |
| **Hatchling** | build backend | Builds the wheel/sdist from the `client/` package. |
| **uvicorn** | ASGI server | Runs FastAPI (the process inside Docker). |

---

## 3. Clean architecture (the layering that keeps it sane)

The client is split so business logic never touches the terminal or the DB:

```
domain/      pure logic & models — NO Rich/Textual/SQLite imports
  typing_engine, calculators, ghost, models, anti_cheat
services/    use-cases that orchestrate domain + a Repository
  race_service, stats_service, daily_service, ghost_service, profile_service
infra/       adapters: SQLite repo, quote loader, clock, config, migrations
ui/          Textual screens + widgets (presentation only)
net/         online client: REST (httpx) + token store
```

**The dependency rule**: arrows point inward. `domain` depends on nothing;
`services` depend on a `Repository` *interface* (a `typing.Protocol`), not on
SQLite. That's **dependency inversion** — you could swap SQLite for anything and
the game logic wouldn't change. It also makes the core trivially unit-testable
(no I/O, time is injected via a `Clock`).

> Learn next: "Ports & Adapters / Hexagonal architecture", `typing.Protocol`,
> dependency injection.

### The typing engine (pure, deterministic)
`TypingEngine` consumes `(char, timestamp)` events and tracks per-character
correctness, cursor, keystroke counts, and a replay timeline. Timestamps are
*passed in* (not read from a clock), so it's 100% deterministic and testable.
WPM math (MonkeyType-style):
```
WPM      = (correct_chars / 5) / minutes        # a "word" = 5 chars
raw WPM  = (all_typed_chars / 5) / minutes
accuracy = correct_keystrokes / total_keystrokes
```
The clock starts on the **first keystroke** (a subtle but important detail — and
the source of an early "2222 WPM" bug when a stray timer reset the start).

---

## 4. Local data: SQLite

- One file in the OS data dir (`platformdirs`), opened in **WAL** mode for
  durability + concurrent reads.
- **Schema migrations** are an ordered list applied on startup, versioned in a
  `schema_meta` table (so upgrades are safe). Tables: `profile`, `quote`, `race`,
  `replay`, `daily_challenge`.
- **Ghosts** are stored as a compact replay timeline (`[{t, p}, …]`) — at race
  time the UI interpolates the ghost's progress at the current elapsed ms.

> Learn next: SQLite WAL, schema-migration patterns, why not JSON files
> (atomicity, queries, growth).

---

## 5. The server as a microservice

`server/app/` is a small, focused FastAPI service:

```
main.py          app factory + lifespan (Redis pool, graceful shutdown) + WS route
config.py        env-driven settings (pydantic-settings)
deps.py          DI: settings, redis repo, current-user, rate limiter
security.py      bcrypt hashing + JWT issue/verify
repositories.py  ALL Redis access behind one class
redis_keys.py    every key builder in one place (the data model, documented)
routers/         auth, oauth, lobbies, leaderboards, health
ws/manager.py    the realtime Hub (lobbies + race orchestration)
quotes.py        server-side quote selection
```

Key ideas:
- **Lifespan**: on startup it opens one async Redis connection pool and builds the
  `Hub`; on shutdown it cancels in-flight races and closes Redis (graceful).
- **Dependency injection**: routes declare `RepoDep`, `SettingsDep`,
  `CurrentUser` — FastAPI wires them. `current_user` decodes the JWT *and* checks
  the session still exists in Redis (so logout truly revokes).
- **Stateless app + stateful Redis**: the FastAPI process holds no durable state,
  so it can restart freely; everything lives in Redis. (In-flight WS races are
  the one piece of in-process state — acceptable to lose on restart.)

### Auth
- **Passwords**: bcrypt (salted, slow hash). Stored as a hash, never plaintext.
- **JWT** access token (`sub`, `jti`, `exp`), signed with `HS256`. The `jti` keys
  a `session:{jti}` Redis entry with a TTL = token lifetime → revocable on logout.
- **OAuth (GitHub/Google) device flow** — the "`gh auth login`" pattern for CLIs:
  the client asks the server to start; the server calls the provider, gets a
  `user_code` + URL; you approve in a browser; the client polls until the server
  exchanges it and issues *our* JWT. No client secret ever touches your machine.

> Learn next: bcrypt vs argon2, JWT structure & pitfalls, OAuth 2.0 Device
> Authorization Grant (RFC 8628).

---

## 6. Redis data model

Why Redis: lobbies and leaderboards are exactly its native types.

| Key | Type | Purpose |
|---|---|---|
| `user:{name}` | HASH | password hash, created_at, stats |
| `session:{jti}` | STRING (TTL) | active token → username (revocable) |
| `oauth:{provider}:{id}` | STRING | external identity → our username |
| `lobby:{code}` | HASH | name, host, mode, status |
| `lobby:{code}:players` | HASH | username → JSON `PlayerState` |
| `lobbies:public` | SET | browsable lobby codes |
| `race:{code}` | HASH | quote, text, start_ms, status |
| `leaderboard:global` / `:daily:{d}` / `:weekly:{w}` | ZSET | username → best WPM |
| `rl:{bucket}:{ip}` | STRING (TTL) | rate-limit counters |

**Sorted sets (ZSET)** make leaderboards trivial: `ZADD … GT` keeps each player's
best score; `ZREVRANGE` reads the top N in rank order, O(log n).

> Learn next: Redis data types, `ZADD GT`, TTL/eviction, AOF vs RDB persistence.

---

## 7. WebSockets & the lobby (the realtime core)

### Why WebSockets?
HTTP is request/response — the server can't *push*. A typing race needs the
server to push countdowns and every opponent's progress in real time. A
**WebSocket** upgrades a single HTTP connection into a persistent, bidirectional,
full-duplex channel (it starts as `GET … Upgrade: websocket`, then both sides
send frames whenever they want). Over TLS it's `wss://`.

### The protocol (one JSON envelope both ways)
```json
{ "type": "RACE_START", "ts": 1749…, "data": { "text": "…", "mode_seconds": 60 } }
```
- **Client → server**: `SET_READY`, `PROGRESS`, `FINISH`, `CHAT`, `LEAVE`.
- **Server → client**: `PLAYER_JOINED/LEFT`, `LOBBY_UPDATE`, `READY_STATE`,
  `RACE_COUNTDOWN`, `RACE_START`, `RACE_PROGRESS`, `RACE_FINISHED`, `ERROR`.

Full reference: [`websocket-protocol.md`](websocket-protocol.md).

### Server-authoritative design (anti-cheat by construction)
Clients never decide timing. The server:
1. Validates the JWT from the `?token=` query on connect (closes `4401` if bad).
2. Adds the player to the lobby, broadcasts presence.
3. When **all connected players are ready**, runs the countdown, picks the quote,
   stamps `server_start_ms`, and broadcasts `RACE_START` to everyone at once.
4. Relays each `PROGRESS` to the others (live bars).
5. On `FINISH`, **recomputes** WPM/accuracy from raw counts using the *shared*
   scoring module and runs anti-cheat before writing the leaderboard — the
   client's self-reported numbers are never trusted.

### The Hub / Room concurrency model
`ws/manager.py` keeps an in-memory `Hub` of `Room`s (one per lobby). Each Room
holds the connected `WebSocket`s and an `asyncio.Event` (`all_finished`). The
race loop is a single `asyncio.Task` per room:
```python
await broadcast(RACE_COUNTDOWN…)          # 3,2,1
await set_race(...) ; broadcast(RACE_START…)
try:
    await asyncio.wait_for(room.all_finished.wait(), timeout=mode_seconds)
except TimeoutError:
    pass                                   # time ran out
broadcast(RACE_FINISHED, standings=…)
```
Everything runs on **one event loop** — no threads, no locks for the hot path,
because asyncio is cooperative single-threaded concurrency. Broadcasts fan out
with `asyncio.gather`. A dropped socket is caught per-send so one dead client
can't break the room.

### Client side (Textual)
The race screen opens the WS in a Textual **worker**, drives a `TypingEngine`
from key events, sends throttled `PROGRESS`, and renders incoming events. Because
the TUI runs its own asyncio loop, blocking REST calls (login/lobby) are pushed
to **worker threads** and marshalled back with `call_from_thread`.

> Learn next: the WebSocket RFC 6455 handshake, `asyncio` tasks/events/`gather`,
> back-pressure (bounded queues), heartbeats/ping-pong, reconnection with
> exponential backoff, and horizontal scaling (multiple server instances need a
> Redis pub/sub fan-out since WS connections are per-process).

### What a production-grade upgrade would add
- **Heartbeats** (ping/pong) + idle timeouts to drop half-open connections.
- **Reconnect** with resume tokens.
- **Pub/Sub fan-out** (Redis channels) so you can run >1 server behind a load
  balancer and still broadcast across them.
- **Per-message size limits / rate limits** on the socket.

---

## 8. Concurrency model summary
- **Server**: one asyncio event loop; async Redis; one task per active race.
- **Client TUI**: one asyncio loop (Textual); blocking HTTP in threads; the WS in
  an async worker.
- **Pure domain** is sync and deterministic (time injected) — easy to test.

---

## 9. Packaging & distribution
- **Wheel/sdist** built by Hatchling from `client/typefaster` (quotes bundled as
  package data). The `typefaster` command is a `console_scripts` entry point.
- **PyPI** via GitHub Actions on a version tag, using **Trusted Publishing
  (OIDC)** — GitHub proves its identity to PyPI, so **no API tokens** are stored.
- **Homebrew tap** (`Anoshor/homebrew-typefaster`): a Ruby formula that builds a
  Python virtualenv with pinned `resource` blocks for every dependency.
  **Bottles** (prebuilt binaries) make `brew install` a fast download instead of
  a source build.

> Learn next: PEP 517/518 build backends, entry points, PyPI Trusted Publishing,
> Homebrew formula `virtualenv_install_with_resources` + bottling.

---

## 10. Containerization & deployment
- **Docker** multi-stage-ish image: install `shared` then `server`, run as a
  non-root user, with a `HEALTHCHECK`. `docker-compose.yml` wires server + Redis
  on a private network (Redis is never published).
- **Colima** is the local Docker engine (a free, OSS Lima VM) — a drop-in for
  Docker Desktop; the `docker` CLI talks to it via a context.
- **Production**: an **Oracle Cloud Always-Free** Ubuntu VM runs the compose
  stack 24/7 for $0. **Caddy** sits in front as a reverse proxy and gets an
  automatic **Let's Encrypt** TLS cert for `<ip>.sslip.io` (sslip.io is free
  wildcard DNS that maps an IP-embedded hostname to that IP — no domain needed),
  giving `https://` + `wss://`.
- Hardening: SSH key-only, `fail2ban`, `unattended-upgrades`, a locked-down
  firewall (see [`SECURITY-REVIEW.md`](SECURITY-REVIEW.md)).

> Learn next: Docker networking, reverse proxies, ACME/Let's Encrypt (HTTP-01),
> the difference between a cloud Security List and the host firewall.

---

## 11. Testing & CI/CD
- **Tests**: `pytest` — pure unit tests for the engine/calculators/anti-cheat,
  integration tests for the SQLite repo/services, **Textual pilot** tests that
  drive the TUI headlessly, and server tests using **fakeredis** + FastAPI's
  `TestClient` (including a full WebSocket race).
- **Quality gates**: `ruff` (lint), `black` (format), `mypy --strict` (types).
- **CI** (GitHub Actions): runs the gates on 3.11/3.12, plus **pip-audit**,
  **CodeQL**, and **Dependabot** for supply-chain safety. A tag triggers the
  release pipeline (PyPI + GitHub Release + GHCR server image).

> Learn next: property-based testing (Hypothesis), coverage gates, test doubles
> (fakes vs mocks), GitHub Actions OIDC.

---

## 12. Ideas to level up (great learning projects)
- **Scale the realtime layer**: add Redis pub/sub so multiple server instances
  share lobby/race events behind a load balancer.
- **Spectator mode** & **rematch** in lobbies.
- **Per-message WS auth refresh** + reconnect/resume.
- **Observability**: structured logs → Loki/Grafana, error tracking (Sentry),
  `/metrics` for Prometheus.
- **Postgres** for durable accounts/history (keep Redis for hot realtime state).
- **Property tests** for the typing engine; **load tests** (k6) for the WS server.

---

### Map of the code
- Client: `client/typefaster/{domain,services,infra,ui,net}`
- Server: `server/app/{routers,ws,…}` · Shared: `shared/typefaster_shared`
- Docs: `docs/` (architecture, sqlite-schema, redis-schema, websocket-protocol,
  api-spec, deploy-*, SECURITY-REVIEW, this file)
