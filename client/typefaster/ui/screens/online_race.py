"""Online multiplayer race screen.

Connects to the server over WebSocket, auto-readies, and lets the **server**
drive countdown/start/finish. The client only renders state, reports progress,
and submits a final result for server-side validation.
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
from ..widgets.live_stats import LiveStats
from ..widgets.typing_field import TypingField


def _bar(pct: float, width: int = 24) -> str:
    filled = max(0, min(width, round(pct / 100.0 * width)))
    return "#" * filled + "-" * (width - filled)


class OnlineRaceScreen(Screen[None]):
    BINDINGS = [("escape", "leave", "Leave")]

    def __init__(self, ws_url: str, username: str, mode_seconds: int) -> None:
        super().__init__()
        self.ws_url = ws_url
        self.username = username
        self.mode_seconds = mode_seconds
        self.engine: TypingEngine | None = None
        self._ws: Any = None
        self._start_ms: int | None = None
        self._typing = False
        self._finished = False
        self._opponents: dict[str, dict[str, float]] = {}
        self._status = "Connecting…"
        self._standings: list[dict[str, Any]] | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="race-wrap"):
            yield Static("", id="net-status", classes="dim")
            yield LiveStats()
            yield TypingField()
            with VerticalScroll():
                yield Static("", id="bars")
            yield Static("esc to leave", classes="dim")

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
                self._status = "Connected. Waiting for players to ready up…"
                self._render_status()
                await ws.send(json.dumps({"type": "SET_READY", "data": {"ready": True}}))
                async for raw in ws:
                    self._handle(json.loads(raw))
        except Exception as exc:
            self._status = f"Disconnected: {exc}"
            self._render_status()

    async def _send(self, type_: str, **data: Any) -> None:
        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.send(json.dumps({"type": type_, "data": data}))

    def _handle(self, msg: dict[str, Any]) -> None:
        etype = msg.get("type")
        data = msg.get("data", {})
        if etype == "RACE_COUNTDOWN":
            self._status = f"Race starts in {data.get('count')}…"
            self._render_status()
        elif etype == "RACE_START":
            self._begin(data["text"])
        elif etype == "RACE_PROGRESS":
            user = data.get("username")
            if user and user != self.username:
                self._opponents[user] = {
                    "progress": float(data.get("progress", 0)),
                    "wpm": float(data.get("wpm", 0)),
                }
                self._render_bars()
        elif etype == "RACE_FINISHED":
            if data.get("final"):
                self._standings = data.get("standings", [])
                self._show_standings()
            else:
                user = data.get("username")
                if user and user != self.username:
                    self._opponents.setdefault(user, {})["progress"] = 100.0
                    self._render_bars()
        elif etype == "CHAT_MESSAGE":
            pass  # chat panel could render here

    # ── race lifecycle ─────────────────────────────────────────────────
    def _begin(self, text: str) -> None:
        self.engine = TypingEngine(text)
        self._start_ms = int(time.time() * 1000)
        self._typing = True
        self._status = "GO!"
        self.query_one("#net-status", Static).display = False
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
        # Report progress to the server.
        self.run_worker(
            self._send(
                "PROGRESS",
                progress=self.engine.progress * 100.0,
                wpm=round(self.engine.live_wpm(max(elapsed, 1)), 1),
            ),
            name="progress",
        )
        if (elapsed >= self.mode_seconds * 1000 or self.engine.finished) and not self._finished:
            self._submit_finish()

    def on_key(self, event: events.Key) -> None:
        if not self._typing or self._finished or self.engine is None:
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
        self.query_one("#net-status", Static).update(Text(self._status, justify="center"))

    def _render_field(self) -> None:
        if self.engine is not None:
            self.query_one(TypingField).show(
                self.engine.target, self.engine.states, self.engine.cursor
            )

    def _render_bars(self) -> None:
        text = Text()
        me_pct = self.engine.progress * 100.0 if self.engine else 0.0
        text.append("You    ", style="bold")
        text.append(f"[{_bar(me_pct)}] {me_pct:3.0f}%\n", style="cyan")
        for name, st in sorted(self._opponents.items()):
            pct = st.get("progress", 0.0)
            text.append(f"{name[:7]:<7}", style="bold")
            text.append(f"[{_bar(pct)}] {pct:3.0f}%\n", style="magenta")
        self.query_one("#bars", Static).update(text)

    def _show_standings(self) -> None:
        self._typing = False
        table = Table(title="Final Standings", title_style="bold")
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
        self.query_one("#net-status", Static).display = True
        self.query_one(TypingField).display = False
        self.query_one(LiveStats).display = False
        self.query_one("#bars", Static).update(Group(table, Text("\nesc to leave", style="grey58")))

    # ── exit ───────────────────────────────────────────────────────────
    def action_leave(self) -> None:
        self.run_worker(self._send("LEAVE"), name="leave")
        if self._ws is not None:
            self.run_worker(self._close_ws(), name="close")
        self.app.pop_screen()

    async def _close_ws(self) -> None:
        with contextlib.suppress(Exception):
            await self._ws.close()
