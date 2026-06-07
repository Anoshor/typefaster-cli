"""Profile screen."""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from ._base import PanelScreen
from .stats import _fmt_ms


class ProfileScreen(PanelScreen):
    title_text = "PROFILE"

    def body(self) -> RenderableType:
        p = self.app.services.profile.get()  # type: ignore[attr-defined]
        grid = Table.grid(padding=(0, 3))
        grid.add_column(justify="right", style="grey58")
        grid.add_column(justify="left")
        grid.add_row("Name", p.display_name)
        grid.add_row("Member since", (p.created_at or "—")[:10])
        grid.add_row("Races", str(p.races_played))
        grid.add_row("Best WPM", f"{p.best_wpm:.0f}")
        grid.add_row("Total time", _fmt_ms(p.total_time_ms))
        grid.add_row("Total chars", f"{p.total_chars:,}")
        note = Text("\nAchievements & online profile arrive in Phase 2.", style="grey58")
        return Group(grid, note)
