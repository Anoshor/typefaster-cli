# Launch posts

Swap in your real handles/links. The public install line is the hook.

---

## X / Twitter

**Single tweet (≈270 chars):**

> I built TYPEFASTER ⌨️ — a typing game that lives entirely in your terminal.
>
> Race quotes, chase your ghost, and play **live multiplayer** with friends — no browser, no GUI.
>
> ```
> brew install Anoshor/typefaster/typefaster
> typefaster
> ```
>
> Python · Textual · FastAPI · WebSockets · Redis
> ⭐ github.com/Anoshor/typefaster-cli

**Optional thread (if you want reach):**

1/ I built a multiplayer typing game that runs 100% in the terminal — TYPEFASTER. MonkeyType/TypeRacer vibes, but it's a TUI. `pipx install typefaster-cli` and you're racing in seconds. 🧵

2/ Offline-first: quotes, ghost races (beat your own replay), Time Attack, a daily challenge, stats — all local in SQLite. No account needed.

3/ Online is the fun part: a FastAPI + WebSocket server runs the lobby. It's **server-authoritative** — it owns the countdown, sends everyone the same quote at the same instant, and re-scores results (so no cheating).

4/ Stack: Python, Typer + Textual (the TUI), FastAPI + websockets + Redis (realtime), Docker. Shipped to PyPI + a Homebrew tap, hosted free 24/7 on an Oracle Always-Free VM with auto-TLS.

5/ Try it: `brew install Anoshor/typefaster/typefaster` → `typefaster` → Account → Play Online. Code's open source 👉 github.com/Anoshor/typefaster-cli ⭐

---

## LinkedIn

> **I built a multiplayer typing game that runs entirely in your terminal — TYPEFASTER.** ⌨️
>
> No browser, no GUI. You install it with one command and you're racing in seconds:
>
> `brew install Anoshor/typefaster/typefaster` (or `pipx install typefaster-cli`)
>
> What it does:
> • Offline-first single-player — quote races, "ghost" races against your own best run, Time Attack, a daily challenge, full stats — all stored locally in SQLite.
> • Real-time **multiplayer lobbies** — create a lobby, share a code, and race friends live with on-screen progress bars and leaderboards.
>
> What I learned building it (and why it was fun):
> • **TUI engineering** with Textual + Rich — building an app, not a script, in the terminal.
> • **Server-authoritative real-time** over WebSockets — the server controls timing and re-scores every result, so the game is fair by design. Backed by FastAPI + Redis.
> • **Clean architecture** — pure, testable game logic with zero UI/DB coupling.
> • **Shipping it for real** — packaged to PyPI and a Homebrew tap (automated via GitHub Actions + PyPI Trusted Publishing), containerized with Docker, and hosted 24/7 for $0 on an Oracle Always-Free VM with automatic HTTPS.
>
> It's open source — would love feedback, stars, and a race or two:
> 👉 github.com/Anoshor/typefaster-cli
>
> #Python #OpenSource #WebSockets #FastAPI #DeveloperTools #CLI
