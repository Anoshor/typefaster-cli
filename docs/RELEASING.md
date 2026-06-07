# Releasing TYPEFASTER — GitHub → PyPI → Homebrew

End-to-end runbook for shipping the **client CLI** as an open-source package.
(The multiplayer **server** is deployed separately with Docker — see
[deployment.md](deployment.md). It is not part of the PyPI/Homebrew package.)

What ships in the package: the `typefaster` command and the `typefaster`
Python package (built from `client/typefaster`, quotes bundled). The wheel is
produced by the root `pyproject.toml` via Hatchling.

---

## 0. Pre-flight (once)

1. **Pick a distribution name.** `pyproject.toml` uses `typefaster-cli`. Check
   it's free: https://pypi.org/project/typefaster-cli/ — if taken, change
   `[project].name` (the import name `typefaster` and command stay the same).
2. **Fill in metadata** in `pyproject.toml`: real `authors`, and the
   `[project.urls]` (point `Homepage`/`Repository` at your GitHub repo).
3. **Edit `LICENSE`** — replace "TYPEFASTER-CLI authors" with your name.
4. **Green build locally:**
   ```bash
   make check            # ruff + mypy + tests   (or: PYTHONPATH=client pytest)
   python -m pip install build twine
   python -m build       # -> dist/typefaster_cli-0.1.0-py3-none-any.whl + .tar.gz
   twine check dist/*
   ```
5. **Smoke-test the built wheel in a clean env:**
   ```bash
   pipx install dist/typefaster_cli-0.1.0-py3-none-any.whl   # or python -m venv ...
   typefaster version
   ```

---

## 1. Push to GitHub

```bash
cd typefaster-cli
git init -b main
git add -A
git commit -m "Initial commit: TYPEFASTER offline + online"

# Create the repo and push (public = open source). Uses the gh CLI.
gh repo create typefaster-cli --public --source=. --remote=origin --push \
  --description "Terminal-first typing game with ghosts and multiplayer"
```
Then on the repo page add **topics** (`cli`, `tui`, `typing-game`, `textual`,
`python`, `monkeytype`, `typeracer`) and confirm the **About** description.

CI (`.github/workflows/ci.yml`) runs automatically on every PR/push.

---

## 2. Open-source polish (recommended)

- `LICENSE` ✓ (MIT, already added).
- Add a CI badge to `README.md`:
  `![CI](https://github.com/<you>/typefaster-cli/actions/workflows/ci.yml/badge.svg)`
- Optional: `CONTRIBUTING.md`, a `CODE_OF_CONDUCT.md`, and GitHub issue
  templates under `.github/`.
- Enable branch protection on `main` (require CI to pass).

---

## 3. Publish to PyPI

### One-time: configure Trusted Publishing (no tokens needed)
1. Create accounts on https://test.pypi.org and https://pypi.org.
2. On **PyPI → Your projects → Publishing → Add a pending publisher**:
   - PyPI Project Name: `typefaster-cli`
   - Owner: `<your-github-user>`  · Repository: `typefaster-cli`
   - Workflow name: `release.yml`  · Environment: `pypi`
3. (Optional but recommended) In GitHub repo **Settings → Environments**, create
   an environment named `pypi` and add required reviewers for a manual approval
   gate before publish.

### Dry run on TestPyPI (optional)
```bash
twine upload --repository testpypi dist/*
pipx install --index-url https://test.pypi.org/simple/ \
  --pip-args="--extra-index-url https://pypi.org/simple" typefaster-cli
```

### Production release (automated)
Publishing is wired to **version tags** via `.github/workflows/release.yml`:
```bash
# bump version in pyproject.toml first (e.g. 0.1.0 -> 0.1.1), commit, then:
git tag v0.1.0
git push origin v0.1.0
```
The workflow builds, `twine check`s, **publishes to PyPI** (Trusted Publishing),
and creates a **GitHub Release** with the wheel/sdist attached and auto-generated
notes.

> Manual fallback (if you prefer tokens): create a PyPI API token and
> `twine upload dist/*` after `python -m build`.

After it lands, anyone can:
```bash
pipx install typefaster-cli     # recommended for CLI tools
# or: pip install typefaster-cli
typefaster
```

---

## 4. Homebrew

Two options. **pipx** is simplest; a **tap** gives the `brew install` experience.

### Option A — quickest (no formula)
Document this in your README:
```bash
brew install pipx
pipx install typefaster-cli
```

### Option B — your own tap (`brew install <you>/typefaster/typefaster`)
1. **Create the tap repo** (must be named `homebrew-<tap>`):
   ```bash
   gh repo create homebrew-typefaster --public --clone
   cd homebrew-typefaster && mkdir -p Formula
   ```
2. **Scaffold the formula from the PyPI sdist** (publish to PyPI first):
   ```bash
   # grab the sdist URL from https://pypi.org/project/typefaster-cli/#files
   brew create --python --set-name typefaster \
     https://files.pythonhosted.org/.../typefaster_cli-0.1.0.tar.gz
   ```
   Or copy `packaging/homebrew/typefaster.rb` from this repo into
   `Formula/typefaster.rb` and set `url` + `sha256` (sha256 of the sdist:
   `shasum -a 256 dist/typefaster_cli-0.1.0.tar.gz`).
3. **Auto-fill dependency resources** (typer, rich, textual, httpx, websockets, …):
   ```bash
   brew update-python-resources Formula/typefaster.rb
   ```
4. **Test + audit, then push:**
   ```bash
   brew install --build-from-source ./Formula/typefaster.rb
   brew test typefaster
   brew audit --new --formula ./Formula/typefaster.rb
   git add -A && git commit -m "typefaster 0.1.0" && git push
   ```
5. Users install with:
   ```bash
   brew tap <you>/typefaster
   brew install typefaster
   ```

> Submitting to **homebrew-core** (so plain `brew install typefaster` works) has
> a high bar (notability, stable releases). Start with your own tap.

---

## 5. Cutting future releases

1. Update `version` in `pyproject.toml` (follow SemVer).
2. `git commit` + `git tag vX.Y.Z` + `git push --tags` → CI publishes to PyPI and
   makes the GitHub Release.
3. Bump the Homebrew formula: update `url`/`sha256` to the new sdist and run
   `brew update-python-resources` again, then push the tap.
   - Tip: `brew bump-formula-pr` can automate the url/sha bump.

---

## Notes specific to this repo
- The wheel includes only the **client** (`client/typefaster` + `quotes.json`);
  `server/`, `shared/`, `infra/` are not packaged for end users.
- Online play needs a running server; point the client at it via `server_url`
  in `~/.config/typefaster/auth.json` (or ship a default in a future build).
- The Python floor is **3.11+** (`requires-python`), so the Homebrew formula
  depends on `python@3.12`.
