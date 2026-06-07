# ⌨ TYPEFASTER-CLI

A **terminal-first** typing game inspired by MonkeyType and TypeRacer.

> Not a web app. Not a browser game. Not a desktop GUI.
> A polished **Python terminal application** that works offline first, then scales to internet multiplayer.

```bash
typefaster
```

…and you're racing within seconds. No login, no server, no Docker, no internet required.

---

## Status

| Phase | Scope | State |
|-------|-------|-------|
| **Phase 1** | Offline experience: races, ghosts, profile, stats, history, daily challenge | ✅ **Implemented & tested** |
| **Phase 2** | Online multiplayer: FastAPI + Redis + WebSockets, auth, lobbies, leaderboards, anti-cheat, Docker | ✅ **Implemented & tested** |

Both phases are implemented. Offline play needs only `pip install`; online play
adds a Dockerized server (see [Online play](#online-play-phase-2)).

---

## What Phase 1 delivers

- **Instant offline races** — random quote, live WPM / accuracy / progress / timer.
- **30 / 60 / 120 second** race modes.
- **Ghost races** against your `personal-best`, `last`, or a `random` historical run, animated live.
- **Local profile & stats** in SQLite — races played/won, best/avg WPM, best/avg accuracy, total chars, total time, full history.
- **Daily challenge** — same quote for everyone each day, with a local daily leaderboard.
- **Polished TUI** built on **Textual** + **Rich**, keyboard-only, resize-aware.

## Planned CLI

```bash
typefaster                                   # launch straight into the game
typefaster race --time 60 --ghost personal-best
typefaster race --ghost last
typefaster race --ghost random
typefaster daily
typefaster profile
typefaster stats
typefaster history
```

---

## Tech stack

**Client (Phase 1):** Python 3.11+, Typer, Rich, Textual, SQLite (stdlib), platformdirs.
**Server (Phase 2):** FastAPI, asyncio, WebSockets, Pydantic, Redis, Docker Compose.

## Repository layout

```
typefaster-cli/
├── client/typefaster/   # CLI app: domain · services · infra · ui · net · assets
├── server/app/          # FastAPI server: routers · ws · repositories · security
├── shared/              # shared schemas, WS protocol, scoring, anti-cheat
├── infra/               # redis.conf · nginx.conf (TLS + WS proxy)
├── docs/                # architecture, schemas, protocol, deployment, roadmap
├── tests/               # client unit · integration · UI smoke
├── scripts/             # quote dataset tooling
├── docker-compose.yml   # redis + server (+ nginx via --profile proxy)
├── pyproject.toml · Makefile · README.md
```

See [`docs/architecture.md`](docs/architecture.md) for the full design.

## Online play (Phase 2)

Run the server stack (Redis + FastAPI + WebSockets) with Docker:

```bash
cp .env.example .env       # set TYPEFASTER_JWT_SECRET
make up                    # redis + server on :8000  (make up-proxy adds nginx TLS)
```

Then, from the client:

```bash
typefaster register alice          # create an account
typefaster login alice
typefaster lobby create --name "Friday Sprint" --time 60
typefaster lobby join ABC123       # join a friend's private lobby
typefaster lobby list              # browse public lobbies
typefaster leaderboard global      # global | daily | weekly
typefaster logout
```

The server is **authoritative**: it controls race start/finish, re-scores every
result, and runs anti-cheat before writing leaderboards. See the docs:

- [API specification](docs/api-spec.md)
- [WebSocket protocol](docs/websocket-protocol.md)
- [Redis schema](docs/redis-schema.md)
- [Deployment guide (single Linux VM)](docs/deployment.md)

The client points at `http://localhost:8000` by default; set `server_url` in
`~/.config/typefaster/auth.json` to target a deployed server.

## Development

```bash
make install   # editable install + dev deps
make play      # launch the game
make test      # pytest
make lint      # ruff
make typecheck # mypy
make format    # black + ruff --fix
make check     # lint + typecheck + test (CI parity)
```

> **Note on the monorepo layout:** the importable package lives at
> `client/typefaster`. A normal install (`pip install .`, used by Docker and end
> users) places it on the path automatically. For local development the
> `Makefile` exports `PYTHONPATH=client`, so `make play` / `make test` always
> work. If you invoke tools directly, prefix with `PYTHONPATH=client` (e.g.
> `PYTHONPATH=client python -m typefaster`).

## Design preferences locked for Phase 1

- **Quotes:** curated public-domain set, tagged `short` / `medium` / `long` for difficulty buckets and 30/60/120s fit.
- **Backspace:** allowed (MonkeyType-style) — corrections permitted, original errors still count toward accuracy; exposed as a Settings toggle.

## License

MIT.
