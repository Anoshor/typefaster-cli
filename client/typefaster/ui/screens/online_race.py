"""Online multiplayer lobby + race screen.

Flow: connect → wait in the lobby (press R to ready) → the **server** starts the
race when everyone is ready, sends the same quote to all, relays progress, and
re-scores results server-side. The client only renders state and reports input.
"""

from __future__ import annotations

import contextlib
import json
import time
from typing import Any

import websockets
from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from ...domain.typing_engine import TypingEngine
from ..widgets import bigtext
from ..widgets.live_stats import LiveStats
from ..widgets.typing_field import TypingField


def _bar(pct: float, width: int = 28) -> str:
    filled = max(0, min(width, round(pct / 100.0 * width)))
    return "█" * filled + "─" * (width - filled)


class OnlineRaceScreen(Screen[None]):
    BINDINGS = [("escape", "leave", "Leave")]

    def __init__(self, ws_url: str, username: str, mode_seconds: int) -> None:
        super().__init__()
        self.ws_url = ws_url
        self.username = username
        self.mode_seconds = mode_seconds
        # Extract the lobby code from .../ws/lobby/<code>?token=...
        self.code = ws_url.split("/ws/lobby/", 1)[-1].split("?", 1)[0]
        self.engine: TypingEngine | None = None
        self._ws: Any = None
        self._start_ms: int | None = None
        self._phase = "lobby"  # lobby | racing | results
        self._typing = False
        self._finished = False
        self._ready = False
        self._roster: list[dict[str, Any]] = []
        self._opponents: dict[str, dict[str, float]] = {}
        self._status = "Connecting…"
        self._standings: list[dict[str, Any]] | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="race-wrap"):
            yield Static("", id="net-status")
            yield LiveStats()
            yield TypingField()
            with VerticalScroll():
                yield Static("", id="bars")
            yield Static("R ready   ·   esc leave", classes="dim")

    def on_mount(self) -> None:
        self.query_one(LiveStats).display = False
        self.query_one(TypingField).display = False
        self._render_status()
        self.run_worker(self._net_loop(), exclusive=True, name="ws")
        self.set_interval(0.2, self._tick)

    # ── network ────────────────────────────────────────────────────────
    async def _net_loop(self) -> None:
        try:
            async with websockets.connect(self.ws_url) as ws:
                self._ws = ws
                self._status = "In lobby — press [bold]R[/] when ready."
                self._render_status()
                async for raw in ws:
                    self._handle(json.loads(raw))
        except Exception as exc:
            self._status = f"[red]Disconnected:[/] {exc}"
            self._render_status()

    async def _send(self, type_: str, **data: Any) -> None:
        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.send(json.dumps({"type": type_, "data": data}))

    def _handle(self, msg: dict[str, Any]) -> None:
        etype = msg.get("type")
        data = msg.get("data", {})
        if etype == "LOBBY_UPDATE":
            self._roster = data.get("players", [])
            # Only repaint the lobby in the lobby phase — never clobber the
            # results screen with the post-race "reset to waiting" update.
            if self._phase == "lobby":
                self._render_lobby(data)
        elif etype == "RACE_COUNTDOWN":
            self._status = f"Race starts in {data.get('count')}…"
            self._render_status()
        elif etype == "RACE_START":
            self._phase = "racing"
            self._begin(data["text"])
        elif etype == "RACE_PROGRESS":
            user = data.get("username")
            if user and user != self.username:
                self._opponents[user] = {
                    "progress": float(data.get("progress", 0)),
                    "wpm": float(data.get("wpm", 0)),
                }
                if self._typing:
                    self._render_bars()
        elif etype == "RACE_FINISHED":
            if data.get("final"):
                self._phase = "results"
                self._standings = data.get("standings", [])
                self._show_standings()
            else:
                user = data.get("username")
                if user and user != self.username:
                    self._opponents.setdefault(user, {})["progress"] = 100.0
                    self._render_bars()
        elif etype == "ERROR":
            self._status = f"[red]{data.get('message', 'error')}[/]"
            self._render_status()

    # ── race lifecycle ─────────────────────────────────────────────────
    def _begin(self, text: str) -> None:
        self.engine = TypingEngine(text)
        self._start_ms = int(time.time() * 1000)
        self._typing = True
        self.query_one("#net-status", Static).update(
            Text(bigtext.render("GO!"), justify="center", style="bold green")
        )
        self.query_one(LiveStats).display = True
        self.query_one(TypingField).display = True
        self._render_field()

    def _elapsed(self) -> int:
        return 0 if self._start_ms is None else int(time.time() * 1000) - self._start_ms

    def _tick(self) -> None:
        if not self._typing or self.engine is None:
            return
        elapsed = self._elapsed()
        seconds_left = (self.mode_seconds * 1000 - elapsed) / 1000.0
        self.query_one(LiveStats).show(
            wpm=self.engine.live_wpm(max(elapsed, 1)),
            accuracy=self.engine.live_accuracy(),
            progress=self.engine.progress,
            seconds_left=seconds_left,
        )
        self._render_bars()
        self.run_worker(
            self._send(
                "PROGRESS",
                progress=self.engine.progress * 100.0,
                wpm=round(self.engine.live_wpm(max(elapsed, 1)), 1),
            ),
            name="progress",
        )
        if (
            self._start_ms is not None
            and elapsed >= self.mode_seconds * 1000
            and not self._finished
        ):
            self._submit_finish()

    def on_key(self, event: events.Key) -> None:
        # Lobby phase: R toggles ready.
        if self._phase == "lobby":
            if event.key.lower() == "r":
                self._ready = not self._ready
                self.run_worker(self._send("SET_READY", ready=self._ready), name="ready")
                event.stop()
            return
        # Results phase: R re-arms for another round.
        if self._phase == "results":
            if event.key.lower() == "r":
                self._play_again()
                event.stop()
            return
        # Race phase: type.
        if self._finished or self.engine is None:
            return
        t = self._elapsed()
        if event.key == "backspace":
            self.engine.backspace(t)
            event.stop()
        elif event.character is not None and event.character.isprintable():
            self.engine.type_char(event.character, t)
            event.stop()
        else:
            return
        self._render_field()
        if self.engine.finished:
            self._submit_finish()

    def _submit_finish(self) -> None:
        if self._finished or self.engine is None:
            return
        self._finished = True
        self._typing = False
        eng = self.engine
        self.run_worker(
            self._send(
                "FINISH",
                duration_ms=self._elapsed(),
                correct_chars=eng.correct_chars,
                incorrect_chars=eng.incorrect_chars,
                total_keystrokes=eng.total_keystrokes,
                correct_keystrokes=eng.correct_keystrokes,
                pasted=False,
            ),
            name="finish",
        )
        self._status = "Finished — waiting for other racers…"
        self.query_one("#net-status", Static).display = True
        self._render_status()

    # ── rendering ──────────────────────────────────────────────────────
    def _render_status(self) -> None:
        self.query_one("#net-status", Static).update(
            Text.from_markup(self._status, justify="center")
        )

    def _render_lobby(self, data: dict[str, Any]) -> None:
        name = data.get("name", "Lobby")
        host = data.get("host", "")
        table = Table(title=f"{name}  ({self.mode_seconds}s)", title_style="bold", expand=True)
        table.add_column("Player")
        table.add_column("Ready", justify="center")
        for p in self._roster:
            who = p["username"] + (" 👑" if p["username"] == host else "")
            who += "  (you)" if p["username"] == self.username else ""
            ready = "[green]✓[/]" if p.get("ready") else "[grey58]…[/]"
            table.add_row(who, ready)
        ready_n = sum(1 for p in self._roster if p.get("ready"))
        hint = Text.from_markup(
            f"\n{ready_n}/{len(self._roster)} ready   ·   "
            f"press [bold]R[/] to {'unready' if self._ready else 'ready'}   ·   "
            "race starts when everyone is ready",
            justify="center",
        )
        self.query_one("#bars", Static).update(Group(table, hint))
        self.query_one("#net-status", Static).update(
            Text.from_markup(
                f"WAITING ROOM   ·   join code: [bold cyan]{self.code}[/]\n"
                f"[grey58]share:[/] typefaster lobby join {self.code}",
                justify="center",
            )
        )

    def _render_field(self) -> None:
        if self.engine is not None:
            self.query_one(TypingField).show(
                self.engine.target, self.engine.states, self.engine.cursor
            )

    def _render_bars(self) -> None:
        text = Text()
        me_pct = self.engine.progress * 100.0 if self.engine else 0.0
        text.append(f"{self.username[:9]:<9} ", style="bold cyan")
        text.append(f"{_bar(me_pct)} {me_pct:3.0f}%\n", style="cyan")
        for name, st in sorted(self._opponents.items()):
            pct = st.get("progress", 0.0)
            text.append(f"{name[:9]:<9} ", style="bold magenta")
            text.append(f"{_bar(pct)} {pct:3.0f}%\n", style="magenta")
        self.query_one("#bars", Static).update(text)

    def _show_standings(self) -> None:
        self._typing = False
        table = Table(title="Final Standings", title_style="bold", expand=True)
        table.add_column("#", justify="right")
        table.add_column("Player")
        table.add_column("WPM", justify="right")
        table.add_column("Acc", justify="right")
        for i, row in enumerate(self._standings or [], 1):
            flag = " ⚑" if row.get("suspicious") else ""
            table.add_row(
                str(i),
                f"{row.get('username', '?')}{flag}",
                f"{row.get('wpm', 0):.0f}",
                f"{row.get('accuracy', 0) * 100:.0f}%",
            )
        self.query_one("#net-status", Static).update(
            Text("RACE COMPLETE", justify="center", style="bold green")
        )
        self.query_one("#net-status", Static).display = True
        self.query_one(TypingField).display = False
        self.query_one(LiveStats).display = False
        self.query_one("#bars", Static).update(
            Group(table, Text("\nR play again   ·   esc leave", style="grey58"))
        )

    def _play_again(self) -> None:
        """Re-arm for another round from the results screen."""
        self._phase = "lobby"
        self._typing = False
        self._finished = False
        self.engine = None
        self._start_ms = None
        self._opponents = {}
        self._ready = True
        self.query_one(LiveStats).display = False
        self.query_one(TypingField).display = False
        self._status = "Ready for next race — waiting for other players…"
        self._render_status()
        self.run_worker(self._send("SET_READY", ready=True), name="ready")

    # ── exit ───────────────────────────────────────────────────────────
    def action_leave(self) -> None:
        # Tell the server we're leaving (it also detects the socket close).
        self.run_worker(self._send("LEAVE"), name="leave")
        # If launched from the menu (screen underneath), pop back to it;
        # if standalone (CLI `lobby join`), exit the app — popping the only
        # screen would leave a blank screen.
        if len(self.app.screen_stack) > 2:  # base + this (+ any) → safe to pop
            self.app.pop_screen()
        else:
            self.app.exit()
