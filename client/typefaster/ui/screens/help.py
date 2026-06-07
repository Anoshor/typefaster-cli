"""Help overlay."""

from __future__ import annotations

from rich.console import RenderableType
from rich.table import Table

from ._base import PanelScreen


class HelpScreen(PanelScreen):
    title_text = "HELP"

    def body(self) -> RenderableType:
        table = Table.grid(padding=(0, 3))
        table.add_column(style="bold cyan", justify="right")
        table.add_column()
        table.add_row("↑ / ↓ , j / k", "move between options")
        table.add_row("Enter", "select")
        table.add_row("Esc", "go back")
        table.add_row("q", "quit")
        table.add_row("?", "this help")
        table.add_row("", "")
        table.add_row("During a race", "just type; Backspace corrects mistakes")
        table.add_row("", "Esc quits the race")
        return table
