"""Post-race results screen."""

from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from ...domain.models import RaceResult
from ...services.race_service import RaceSetup, RaceSummary
from ..widgets import bigtext


class ResultsScreen(Screen[str]):
    """Shows the outcome. Dismisses with an action string: 'again' or 'menu'.

    ``summary`` is ``None`` when the run was implausible (paste/auto-input) and
    therefore not recorded.
    """

    BINDINGS = [
        ("enter", "again", "Race again"),
        ("escape", "menu", "Menu"),
    ]

    def __init__(
        self, result: RaceResult, setup: RaceSetup, summary: RaceSummary | None = None
    ) -> None:
        super().__init__()
        self.result = result
        self.setup = setup
        self.summary = summary

    def compose(self) -> ComposeResult:
        r = self.result
        with Vertical(id="panel-wrap"):
            yield Static(Text("RESULTS", justify="center"), id="title")

            banner = self._banner()
            if banner:
                yield Static(banner)

            # Big, prominent WPM number.
            yield Static(Text(bigtext.render(f"{r.wpm:.0f}"), justify="center", style="bold cyan"))
            yield Static(Text("WPM", justify="center", style="grey58"))

            table = Table.grid(padding=(0, 2))
            table.add_column(justify="right", style="grey58")
            table.add_column(justify="left")
            table.add_row("Raw WPM", f"{r.raw_wpm:.0f}")
            table.add_row("Accuracy", f"[bold green]{r.accuracy * 100:.1f}%[/]")
            table.add_row("Chars", f"{r.correct_chars} correct · {r.incorrect_chars} wrong")
            table.add_row("Completion", f"{r.progress * 100:.0f}%")
            table.add_row("Time", f"{r.duration_ms / 1000:.1f}s")
            if self.summary and self.summary.new_personal_best:
                table.add_row(
                    "Personal best",
                    f"[grey58]{self.summary.previous_best_wpm:.0f}[/] → "
                    f"[bold yellow]{r.wpm:.0f}[/]  ▲ new best",
                )
            yield Static(table)
            yield Static("", classes="dim")
            yield Static("⏎ race again    esc menu", classes="dim")

    def _banner(self) -> Text | None:
        r = self.result
        if r.suspicious:
            reasons = ", ".join(r.flags) if r.flags else "implausible result"
            return Text(
                f"⚠ Not recorded — {reasons}.\n"
                "Type the text yourself (no pasting) for a valid result.",
                style="bold red",
            )
        if r.ghost_won is True:
            return Text("✓ You beat your ghost!", style="bold green")
        if r.ghost_won is False:
            return Text("✗ The ghost won this time.", style="bold red")
        if self.summary and self.summary.new_personal_best:
            return Text("🏆 New personal best!", style="bold yellow")
        return None

    def action_again(self) -> None:
        self.dismiss("again")

    def action_menu(self) -> None:
        self.dismiss("menu")
