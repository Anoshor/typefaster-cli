# Contributing to TYPEFASTER-CLI

Thanks for your interest in improving TYPEFASTER! Contributions of all kinds are
welcome — bug reports, quotes, features, docs, and code.

## Project layout

```
client/typefaster/   the CLI app  (domain · services · infra · ui · net · assets)
server/app/          online server (FastAPI · ws · repositories · security)
shared/              schemas, WS protocol, scoring, anti-cheat
tests/               client tests   ·   server/tests/  server tests
docs/                architecture, schemas, protocol, deployment, releasing
```

Architecture follows clean layering: **domain** (pure) ← **services** ←
**infra**/**ui**. The domain never imports Rich/Textual/SQLite. Please keep new
code in the right layer.

## Development setup

Requires **Python 3.11+** (the repo is developed against 3.12).

```bash
git clone https://github.com/Anoshor/typefaster-cli && cd typefaster-cli
python3.12 -m venv .venv && source .venv/bin/activate
make install            # editable install + dev deps
make play               # launch the game
```

> The package lives at `client/typefaster`. The `Makefile` exports
> `PYTHONPATH=client`, so `make` targets always work regardless of how the
> editable install resolves on your OS. If you run tools directly, prefix with
> `PYTHONPATH=client`.

## Before opening a PR

Run the full check suite — CI runs the same thing:

```bash
make check              # ruff + mypy + pytest   (client)
cd server && pip install -e ".[dev]" && pytest   # if you touched the server
```

Quality gates (all must pass):
- **ruff** — lint + import sorting
- **black** — formatting (`make format` to auto-fix)
- **mypy --strict** — types (the `typefaster` package)
- **pytest** — tests; add/adjust tests for any behavior change

## Guidelines

- **Keep the domain pure** and deterministic (time is injected via `Clock`).
- **Add tests** for new logic. UI gets Textual pilot smoke tests; logic gets
  unit/integration tests.
- **Conventional, focused commits** and small PRs are easier to review.
- **Adding quotes?** Edit `scripts/seed_quotes.py`, run it, and commit the
  regenerated `client/typefaster/assets/quotes.json`
  (`python scripts/seed_quotes.py && python scripts/seed_quotes.py --check`).
- Don't commit generated artifacts (`dist/`, caches) — they're git-ignored.

## Reporting bugs / requesting features

Use the issue templates (Bug report / Feature request). For race-result or
timing bugs, please include your terminal, OS, and the exact steps.

## Code of conduct

Be respectful and constructive. We follow the spirit of the
[Contributor Covenant](https://www.contributor-covenant.org/).

By contributing, you agree your contributions are licensed under the project's
[MIT License](LICENSE).
