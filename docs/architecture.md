# Architecture — TYPEFASTER-CLI

This document describes the Phase 1 (offline) architecture and the seams that let
Phase 2 (online multiplayer) drop in without rewrites.

## Guiding principles

| Principle | Consequence for Phase 1 |
|---|---|
| **Offline-first** | Zero network, zero account, zero Docker required to play. Works on a plane. |
| **Clean architecture** | Domain logic never imports Rich, Textual, or SQLite. UI and storage are swappable adapters. |
| **Online-ready seams** | Phase 1 defines interfaces (`Repository`, `GhostSource`, `Clock`) that Phase 2 implements over the network. |
| **Pure, testable core** | The typing engine and stats math are pure functions with no I/O — high coverage, reusable server-side later. |

## Layered design

```
┌─────────────────────────────────────────────────────────┐
│  PRESENTATION  (Typer commands + Textual screens + Rich) │
│  knows about: keypresses, layout, colors                 │
└───────────────┬─────────────────────────────────────────┘
                │ calls services, never touches SQL/widgets directly
┌───────────────▼─────────────────────────────────────────┐
│  SERVICES  (application / use-cases)                      │
│  RaceService, ProfileService, GhostService,              │
│  DailyService, StatsService                              │
└───────────────┬─────────────────────────────────────────┘
                │ depends on domain + repository INTERFACES
┌───────────────▼─────────────────────────────────────────┐
│  DOMAIN  (pure Python, no third-party deps)             │
│  TypingEngine, WpmCalculator, AccuracyCalculator,        │
│  models: Race, Keystroke, Result, Ghost, Quote, Profile  │
└───────────────┬─────────────────────────────────────────┘
                │ implemented by
┌───────────────▼─────────────────────────────────────────┐
│  INFRASTRUCTURE  (adapters)                              │
│  SQLiteRepository, QuoteLoader, ReplayStore,             │
│  DailyQuotePicker, Clock, ConfigStore                    │
└──────────────────────────────────────────────────────────┘
```

**Dependency rule:** arrows point inward. Domain depends on nothing. Infrastructure
and Presentation depend on Domain. Services orchestrate. This is what makes the
Phase 2 server (FastAPI/Redis) a matter of providing new adapters for the same ports.

## Key components

### Domain (pure)
- **TypingEngine** — given target text and a stream of `Keystroke`s (char + timestamp),
  produces correctness state, completion %, and a replay timeline. Deterministic; time is injected.
- **WpmCalculator / AccuracyCalculator** — MonkeyType-style math:
  - `WPM = (correct_chars / 5) / minutes`
  - `raw_wpm` includes errors
  - `accuracy = correct_keystrokes / total_keystrokes` (0..1)
- **GhostSource (Protocol)** — returns a replay timeline to race against.

### Services
- **RaceService** — pick quote → run engine against UI events → compute `Result` → persist → return summary. Accepts an optional `GhostSource`.
- **GhostService** — builds `personal-best`, `last`, `random` ghost sources from the repository.
- **ProfileService / StatsService** — read/update aggregates, render-ready stats.
- **DailyService** — deterministic daily quote + local daily leaderboard.

### Infrastructure (adapters)
- **SQLiteRepository** — the only Phase 1 `Repository` implementation. Parameterized SQL, no ORM.
- **QuoteLoader** — seeds `assets/quotes.json` into the `quote` table on startup (idempotent). Runtime selection (random, daily, by difficulty) is handled by `SQLiteRepository`.
- **ReplayStore** — serialize/deserialize replay timelines (`[{"t":1000,"p":5}, ...]`).
- **Clock** — `SystemClock` for prod, `FakeClock` for tests (keeps the engine pure).
- **ConfigStore** — persisted settings (theme, default time, backspace toggle, ghost default).

## Backspace model (locked decision)

Backspace is **allowed** (MonkeyType-style): players may correct mistakes, but the
original error still counts toward accuracy. The engine tracks *keystroke history*
(every keypress, including corrections) separately from the *current buffer state*.
Accuracy is computed from keystroke history; completion/progress from the buffer.
A Settings toggle can switch to strict (no-backspace) mode.

## Data & control flow — one offline race

```
typefaster race --time 60 --ghost personal-best
        │
   Typer cmd  ──► RaceService.start(mode=60, ghost="personal-best")
        │              │
        │         GhostService.load("personal-best") ──► Repository
        │         Repository.random_quote()         ──► SQLite quote table
        │              │
        ▼              ▼
   Textual RaceScreen  ◄── runs TypingEngine, feeds keystrokes
        │   (live WPM / accuracy / progress / ghost bar / timer)
        ▼
   Result ──► RaceService.finish() ──► Repository.save_race(+replay)
        │
        ▼
   Textual ResultsScreen (Rich panels/tables)
```

## Storage location

SQLite DB lives in the OS data dir via `platformdirs`:
- Linux: `~/.local/share/typefaster/typefaster.db`
- macOS: `~/Library/Application Support/typefaster/typefaster.db`

WAL journal mode for durability and concurrent reads. Config in the OS config dir.

## Technology rationale

- **Typer** — typed subcommand parsing, auto help.
- **Textual** — full-screen interactive app: event loop, keyboard, focus, resize.
- **Rich** — tables, progress bars, panels for stats/history and result rendering.
- **SQLite (stdlib)** — single-file durable storage, transactions, migrations; no ORM to keep the domain clean and dependencies light.

## Phase 2 seams (no rewrites required)

| Phase 1 port | Phase 2 implementation |
|---|---|
| `Repository` | `RedisRepository` (online state) alongside SQLite (local cache) |
| `GhostSource` | `RemoteGhostSource` streaming opponents over WebSocket |
| `Clock` | server-authoritative race timing |
| `RaceService` | reused on the **server** to validate results (anti-cheat) |
| Domain calculators | reused server-side — never trust client numbers |

See [`roadmap.md`](roadmap.md) for the Phase 2 plan.
