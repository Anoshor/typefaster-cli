"""You-vs-ghost progress bars that rescale to the available width."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

_MIN_WIDTH = 24
_BLOCK = "█"
_EMPTY = "─"


def _bar(progress_pct: float, width: int) -> str:
    filled = max(0, min(width, round(progress_pct / 100.0 * width)))
    return _BLOCK * filled + _EMPTY * (width - filled)


class ProgressBars(Static):
    """You-vs-ghost bars that grow to fill the available width."""

    def _bar_width(self) -> int:
        # Reserve room for the "You  [" prefix + "] 100% (Ghost)" suffix.
        avail = (self.size.width or 60) - 18
        return max(_MIN_WIDTH, avail)

    def show(
        self,
        *,
        player_pct: float,
        ghost_pct: float | None = None,
        ghost_label: str = "",
    ) -> None:
        width = self._bar_width()
        text = Text()
        text.append("You    ", style="bold")
        text.append(f"{_bar(player_pct, width)} ", style="cyan")
        text.append(f"{player_pct:3.0f}%\n", style="bold")
        if ghost_pct is not None:
            text.append("Ghost  ", style="bold")
            text.append(f"{_bar(ghost_pct, width)} ", style="magenta")
            text.append(f"{ghost_pct:3.0f}%", style="bold")
            if ghost_label:
                text.append(f"  ({ghost_label})", style="grey58")
        self.update(text)
