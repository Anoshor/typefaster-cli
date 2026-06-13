# ⌨ TYPEFASTER

[![CI](https://github.com/Anoshor/typefaster-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Anoshor/typefaster-cli/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/typefaster-cli)](https://pypi.org/project/typefaster-cli/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A **terminal-first** typing game inspired by MonkeyType and TypeRacer — race
quotes, beat your ghost, climb leaderboards, and play **live multiplayer** with
friends. Pure TUI, no browser, no GUI.

```bash
brew install Anoshor/typefaster/typefaster   # or: pipx install typefaster-cli
typefaster
```

---

## Install

**Homebrew** (macOS / Linux)
```bash
brew install Anoshor/typefaster/typefaster
```

**pipx** (any OS with Python 3.11+) — fastest
```bash
pipx install typefaster-cli
```

Verify: `typefaster version`

## Play (offline — no account, no internet)

Just run it:
```bash
typefaster
```
Keyboard-only menu:
- **Quick Race** — a fresh random quote each time; race your personal-best ghost.
- **Time Attack** — type for 30 / 60 / 120s (←/→ to change the duration inline).
- **Practice** — pick a mode/ghost.
- **Daily Challenge** — same quote for everyone each day, local leaderboard.
- **Stats / History / Profile / Leaderboard / Settings**.

Live WPM, accuracy, progress, and an animated ghost bar. Backspace corrects
mistakes (original errors still count, MonkeyType-style). All progress is saved
locally in SQLite.

Direct commands too:
```bash
typefaster race                      # quote race
typefaster race --mode time --time 60
typefaster daily
typefaster stats   |   typefaster history
```

## Play online (multiplayer lobbies)

It works out of the box against the public server — **no setup**. From the main
menu pick **Account** to register/login, then **Play Online**:

```text
Account      → Register / Login (password, GitHub, or Google)
Play Online  → ➕ Create a lobby  → share the join code
             → or type a friend's code + Enter to join
```
In the waiting room press **R** to ready; the **server** runs the countdown,
sends everyone the same quote, shows live progress bars, and scores results
authoritatively (with anti-cheat). **Esc** leaves.

Prefer the CLI?
```bash
typefaster register <name>      # or: typefaster login --github / --google
typefaster lobby create --name "Friday" --time 60
typefaster lobby join ABC123
typefaster leaderboard global   # global | daily | weekly
```

## Self-host the server (optional)

The game ships pointing at a public server, but you can run your own:
```bash
git clone https://github.com/Anoshor/typefaster-cli && cd typefaster-cli
cp .env.example .env            # set TYPEFASTER_JWT_SECRET
make up                         # Redis + FastAPI server on :8000 (Docker)
typefaster config set-server http://localhost:8000
```
Deploy guides: [`docs/deploy-oracle.md`](docs/deploy-oracle.md) (free 24/7 VM) ·
[`docs/deploy-fly.md`](docs/deploy-fly.md) · TLS + hardening in
[`docs/SECURITY-REVIEW.md`](docs/SECURITY-REVIEW.md).

## How it works

- **Client**: Python · Typer (CLI) · Textual + Rich (TUI) · SQLite (local
  progress) · httpx + websockets (online).
- **Server**: FastAPI · WebSockets · Redis · Pydantic — **server-authoritative**
  race timing and scoring.
- Deep dive: [`docs/DEEPDIVE.md`](docs/DEEPDIVE.md) · architecture:
  [`docs/architecture.md`](docs/architecture.md).

## Develop

```bash
make install     # editable install + dev deps
make play        # run it
make check       # ruff + mypy + pytest
```
Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE). Crafted by **Anoshor Paul**.
