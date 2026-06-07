"""Statistics screen."""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from ._base import PanelScreen

_SPARK = "▁▂▃▄▅▆▇█"


def _sparkline(values: list[float]) -> str:
    if not values:
        return "—"
    lo, hi = min(values), max(values)
    span = hi - lo or 1.0
    return "".join(_SPARK[min(7, int((v - lo) / span * 7))] for v in values)


class StatsScreen(PanelScreen):
    title_text = "STATS"

    def body(self) -> RenderableType:
        s = self.app.services.stats.summary()  # type: ignore[attr-defined]
        p = s.profile

        lifetime = Table.grid(padding=(0, 3))
        lifetime.add_column(justify="right", style="grey58")
        lifetime.add_column(justify="left")
        lifetime.add_row("Races played", str(p.races_played))
        lifetime.add_row("Races won", str(p.races_won))
        lifetime.add_row("Best WPM", f"{p.best_wpm:.0f}")
        lifetime.add_row("Avg WPM", f"{s.avg_wpm:.0f}")
        lifetime.add_row("Best accuracy", f"{p.best_accuracy * 100:.1f}%")
        lifetime.add_row("Avg accuracy", f"{s.avg_accuracy * 100:.1f}%")
        lifetime.add_row("Total chars", f"{p.total_chars:,}")
        lifetime.add_row("Total time", _fmt_ms(p.total_time_ms))

        time_tbl = Table(title="Time Attack · best WPM", title_style="bold")
        time_tbl.add_column("Duration")
        time_tbl.add_column("Best WPM", justify="right")
        for seconds in (30, 60, 120):
            time_tbl.add_row(f"{seconds}s", f"{s.time_best_by_mode.get(seconds, 0.0):.0f}")

        quote_tbl = Table(title="Quote · personal bests", title_style="bold")
        quote_tbl.add_column("Metric")
        quote_tbl.add_column("Value", justify="right")
        quote_tbl.add_row("Best WPM", f"{s.quote_best_wpm:.0f}")
        quote_tbl.add_row("Fastest finish", _fmt_ms(s.quote_best_ms) if s.quote_best_ms else "—")

        spark = Text(f"Recent WPM  {_sparkline(s.recent_wpm)}", style="cyan")
        return Group(lifetime, Text(""), time_tbl, Text(""), quote_tbl, Text(""), spark)


def _fmt_ms(ms: int) -> str:
    secs = ms // 1000
    h, rem = divmod(secs, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {sec}s"
    return f"{sec}s"
