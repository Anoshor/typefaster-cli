"""Daily challenge screen — shared quote + local daily leaderboard."""

from __future__ import annotations

from datetime import UTC, datetime

from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from ...domain.models import RaceKind
from ...services.race_service import RaceConfig


class DailyScreen(Screen[None]):
    BINDINGS = [
        ("enter", "play", "Play"),
        ("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        day = datetime.now(UTC).date().isoformat()  # UTC — matches how results are filed
        with Vertical(id="panel-wrap"):
            yield Static(Text(f"DAILY CHALLENGE · {day} (UTC)", justify="center"), id="title")
            with VerticalScroll():
                yield Static(self._body(), id="panel-body")
            yield Static("⏎ play today's challenge    esc back", classes="dim")

    def on_screen_resume(self) -> None:
        # Refresh best/attempts/leaderboard after returning from a race.
        self.query_one("#panel-body", Static).update(self._body())

    def _body(self) -> Group:
        svc = self.app.services  # type: ignore[attr-defined]
        challenge = svc.daily.today()
        board = svc.daily.leaderboard(limit=10)

        quote = Text()
        quote.append("Today's quote (same for everyone)\n", style="grey58")
        quote.append(f'"{challenge.quote.text}"\n', style="italic")
        quote.append(f"— {challenge.quote.source or 'unknown'}\n", style="grey58")
        quote.append(
            f"\nYour best today: {challenge.best_wpm:.0f} wpm  ·  attempts {challenge.attempts}\n",
            style="bold",
        )
        streak = svc.daily.streak()
        if streak:
            unit = "day" if streak == 1 else "days"
            quote.append(f"🔥 Streak: {streak} {unit}\n", style="bold yellow")

        table = Table(title="Local daily leaderboard", title_style="bold", expand=True)
        table.add_column("#", justify="right")
        table.add_column("WPM", justify="right")
        table.add_column("Acc", justify="right")
        if not board:
            table.add_row("—", "—", "not played yet")
        for i, r in enumerate(board, 1):
            table.add_row(str(i), f"{r.wpm:.0f}", f"{r.accuracy * 100:.0f}%")
        return Group(quote, table)

    def action_play(self) -> None:
        # Daily is a fixed quote; the ghost (if any) is your best run on it.
        self.app.start_race(RaceConfig(kind=RaceKind.QUOTE, daily=True))  # type: ignore[attr-defined]

    def action_back(self) -> None:
        self.app.pop_screen()
