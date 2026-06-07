"""History screen — most recent races."""

from __future__ import annotations

from rich.console import RenderableType
from rich.table import Table
from rich.text import Text

from ._base import PanelScreen


class HistoryScreen(PanelScreen):
    title_text = "HISTORY"

    def body(self) -> RenderableType:
        records = self.app.services.stats.history(limit=30)  # type: ignore[attr-defined]
        if not records:
            return Text("No races yet. Press esc, then start a Quick Race!", style="grey58")

        table = Table(expand=True)
        table.add_column("Date")
        table.add_column("Mode", justify="right")
        table.add_column("WPM", justify="right")
        table.add_column("Acc", justify="right")
        table.add_column("Source")
        for r in records:
            table.add_row(
                r.started_at[:16].replace("T", " "),
                f"{r.mode_seconds}s",
                f"{r.wpm:.0f}",
                f"{r.accuracy * 100:.0f}%",
                (r.quote_source or "—")[:24],
            )
        return table
