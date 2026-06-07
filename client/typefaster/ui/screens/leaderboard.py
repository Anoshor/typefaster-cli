"""Leaderboard screen — local top runs (online tiers arrive in Phase 2)."""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from ._base import PanelScreen


class LeaderboardScreen(PanelScreen):
    title_text = "LEADERBOARD (local)"

    def body(self) -> RenderableType:
        stats = self.app.services.stats  # type: ignore[attr-defined]
        blocks: list[RenderableType] = []

        for seconds in (30, 60, 120):
            runs = stats.top_time_runs(seconds, limit=5)
            table = Table(title=f"Time Attack · {seconds}s", title_style="bold", expand=True)
            table.add_column("#", justify="right")
            table.add_column("WPM", justify="right")
            table.add_column("Acc", justify="right")
            table.add_column("Date")
            if not runs:
                table.add_row("—", "—", "—", "no runs yet")
            for i, r in enumerate(runs, 1):
                table.add_row(str(i), f"{r.wpm:.0f}", f"{r.accuracy * 100:.0f}%", r.started_at[:10])
            blocks.append(table)

        quote_runs = stats.top_quote_runs(limit=5)
        qt = Table(title="Quote · top WPM", title_style="bold", expand=True)
        qt.add_column("#", justify="right")
        qt.add_column("WPM", justify="right")
        qt.add_column("Acc", justify="right")
        qt.add_column("Time", justify="right")
        if not quote_runs:
            qt.add_row("—", "—", "—", "no runs yet")
        for i, r in enumerate(quote_runs, 1):
            qt.add_row(
                str(i), f"{r.wpm:.0f}", f"{r.accuracy * 100:.0f}%", f"{r.duration_ms / 1000:.1f}s"
            )
        blocks.append(qt)

        blocks.append(
            Text(
                "\n🌐 Global / Daily / Weekly leaderboards arrive with online mode (Phase 2).",
                style="grey58",
            )
        )
        return Group(*blocks)
