# CLAUDE.md

Guidance for working in this repo. TYPEFASTER is a terminal-first typing game:
an offline TUI plus an online real-time multiplayer server. Distributed via PyPI
(`typefaster-cli`) and a Homebrew tap. Hosted at $0 on an Oracle Always-Free VM.

## Repo layout

```
client/typefaster/   the CLI/TUI app  (domain · services · infra · ui · net · assets)
server/app/          online server (FastAPI · WebSockets · Redis · routers · ws)
shared/typefaster_shared/   schemas (dto), WS events, scoring, anti-cheat — used by both
tests/               client tests (unit/ + integration/)
server/tests/        server tests (fakeredis + Starlette TestClient)
docs/                architecture, schemas, WS protocol, deploy, security, releasing
Formula lives in a SEPARATE repo: Anoshor/homebrew-typefaster (the tap).
```

## Architecture & layering (do not violate)

Clean layering, enforced by convention:

- **`domain/`** is pure: dataclasses, enums, and deterministic logic. It must NOT
  import Rich/Textual/SQLite/httpx. Time is injected (`Clock`), so logic is
  unit-testable without a real clock.
- **`services/`** orchestrate domain + repositories. UI-free, reusable headlessly.
- **`infra/`** (SQLite, config, paths, quote loader) and **`ui/`** (Textual)
  depend inward only.
- **Repository port**: `infra/repository.py` is a `typing.Protocol`; the SQLite
  impl satisfies it. Services depend on the Protocol, not SQLite.
- **Server is authoritative**: the WS server re-scores every race from raw inputs
  using `shared/typefaster_shared/scoring.py` (the SAME math as the client's
  `domain/calculators.py`) and never trusts client-reported WPM/accuracy.

When adding code, put it in the right layer and keep `domain/` pure.

## Commands

Client (from repo root; uses `client/` on PYTHONPATH via the Makefile):
```bash
make install     # editable install + dev deps into a venv
make play        # launch the TUI (offline)
make check       # ruff + mypy --strict + pytest  ← run before every PR
make test        # pytest only
make up / down   # start/stop the online stack (redis + server) via Docker
```

Server (separate package; mirror CI exactly):
```bash
cd server && pytest                                   # server suite (fakeredis)
ruff check server shared --select E,F,I,UP,B --ignore UP042   # the server lint gate
```

Notes:
- The package lives at `client/typefaster`; `make` sets `PYTHONPATH=client`. If
  running tools directly, prefix with `PYTHONPATH=client`.
- Client gate = ruff + black + mypy --strict + pytest. **Server CI runs ruff +
  pytest only — no mypy** (the server has known pre-existing mypy noise from the
  untyped `typefaster_shared` import; don't chase it).
- Tests use markers: `unit`, `integration`, `ui` (Textual pilot smoke tests).

## Conventions

- Add/adjust tests for any behavior change. UI gets Textual pilot smoke tests in
  `tests/integration/test_ui_smoke.py`; logic gets unit/integration tests.
- Adding a TUI screen: create it under `ui/screens/`, register it in `_PANELS`
  in `ui/app.py`, and add a menu row in `ui/screens/main_menu.py`. Read-only
  panels subclass `PanelScreen` (`ui/screens/_base.py`); override `body()`.
- Adding a SQLite migration: append a `(version, sql)` tuple to `_MIGRATIONS` in
  `infra/migrations.py` (use `IF NOT EXISTS`; never edit a shipped migration).
- Adding quotes: edit `scripts/seed_quotes.py`, run it, commit the regenerated
  `client/typefaster/assets/quotes.json`.
- Conventional, focused commits. Don't commit generated artifacts (git-ignored).

## Release flow (automated)

Per release, edit the version in **two** files that must stay in sync:
`pyproject.toml` and `client/typefaster/__init__.py`. Then:
```bash
git tag vX.Y.Z && git push origin vX.Y.Z
```
The tag triggers `.github/workflows/release.yml`, which: builds → publishes to
PyPI (OIDC Trusted Publishing, gated by the `pypi` environment approval) →
creates a GitHub Release → **auto-bumps the Homebrew tap formula** (needs the
`HOMEBREW_TAP_TOKEN` secret) → pushes the server image to GHCR.

## Git / PR workflow

`main` is protected: PRs require a passing CI + a CODEOWNERS review before merge;
no force-push/deletion. As repo admin you can bypass for your own pushes, but
prefer feature branches. Branch from `main`; do not commit directly unless asked.

## Key facts / gotchas

- **Public server**: client default `server_url` lives in
  `client/typefaster/net/token_store.py` (`DEFAULT_SERVER_URL`). It self-heals a
  dead `*.trycloudflare.com` URL to the default on load.
- **Online is server-authoritative** with per-IP rate limiting on auth/oauth and
  app-layer flood guards (see `docs/ddos-protection.md`). A true volumetric DDoS
  needs an upstream edge (Cloudflare) — app code can't stop it.
- **Daily challenge** is keyed by UTC date (`datetime.now(UTC).date()`), matching
  how results are filed — don't switch it to local `date.today()`.
- **Secrets are never committed.** JWT secret + OAuth client IDs/secret live only
  in `/opt/typefaster/.env` on the VM. `.env` and `docs/MARKETING.md` are
  git-ignored.
- **Two repos by design**: the code repo and the mandatory `homebrew-typefaster`
  tap (one formula file, auto-bumped by CI). The tap is not a second project to
  maintain.
- The TUI footer credits "Anoshor Paul" intentionally; keep it.
- $0 hosting is a project goal — prefer free tiers; flag anything that adds cost.
