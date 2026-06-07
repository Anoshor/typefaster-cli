# Roadmap — TYPEFASTER-CLI

**Status:** Phase 1 ✅ and Phase 2 ✅ are both implemented and tested
(93 tests passing: 66 client, 27 server). The sections below record the plan;
boxes are checked as delivered.

## Phase 1 — Offline experience ✅

Goal: a brand-new user runs `typefaster` and is racing within seconds, with durable
local progression and ghost races — fun even with zero other players.

| Step | Deliverable |
|---|---|
| 1.0 Scaffold | repo, pyproject, Makefile, ruff/black/mypy/pytest, CI, stub dirs |
| 1.1 Domain core | models, typing_engine, calculators, ghost sampling (pure) |
| 1.2 Quotes dataset | `assets/quotes.json` (≥500, tagged short/medium/long), loader, seed script |
| 1.3 Persistence | db, migrations, sqlite_repository, replay_store, config |
| 1.4 Services | race / profile / stats / ghost / daily services |
| 1.5 UI shell | Textual app, theme, main menu, navigation, settings |
| 1.6 Race UX | race/countdown/results screens + widgets, ghost animation |
| 1.7 Secondary screens | stats, history, profile, daily, leaderboard |
| 1.8 CLI commands | `typefaster`, `race --ghost/--time`, profile, stats, history, daily |
| 1.9 Polish & docs | README quickstart, docs, coverage ≥85% on domain/services |

**Done when:** fresh `pip install -e .` → `typefaster` launches a playable race,
ghosts work, stats/history/daily persist in SQLite, all screens keyboard-navigable, CI green.

## Phase 2 — Online multiplayer ✅ (delivered)

- **Server:** FastAPI + asyncio + WebSockets + Pydantic.
- **Storage:** Redis (users, sessions, lobby/race state, leaderboards, ghost runs).
- **Client:** add `websockets` + `httpx`; reuse all Phase 1 domain/services.
- **Auth:** `register` / `login` / `logout`, username+password, JWT, bcrypt. No OAuth.
- **Lobbies:** public (browse/join) + private (join code, e.g. `ABC123`); host transfer, leave, destruction.
- **Race flow:** server-authoritative start, countdown, live progress broadcast.
- **Anti-cheat:** server validates results with the shared domain calculators —
  detect paste, impossible WPM, impossible completion times, suspicious bursts.
- **Leaderboards:** global, daily, rolling weekly.
- **Infra:** Docker + Docker Compose, deployable to a single Linux VM; Nginx reverse
  proxy + SSL; Redis persistence; backups; health checks; structured logs; graceful shutdown.
- **Deliverables:** API spec, WebSocket protocol (PLAYER_JOINED, RACE_START,
  RACE_PROGRESS, RACE_FINISHED, LOBBY_CREATED, CHAT_MESSAGE, DAILY_CHALLENGE_UPDATE, …),
  Redis key-structure docs, deployment guide (docs only — no live deploy).

## Phase 3+ — ideas (not committed)

- Achievements & streaks, friend ghosts, themed quote packs, code-typing mode,
  custom text import, replay export/share, accessibility options.
