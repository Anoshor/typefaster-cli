"""Typing Coach screen — most-missed keys, a per-key heatmap, and finger tips.

All local and deterministic: it reads the offline per-key stats the coach service
aggregates. No network, no LLM.
"""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from ...domain import keyboard
from ...services.coach_service import KeyAccuracy
from ._base import PanelScreen


def _key_label(key: str) -> str:
    return "␣" if key == " " else key.upper()


def _heat_style(accuracy: float) -> str:
    if accuracy >= 0.98:
        return "bold green"
    if accuracy >= 0.95:
        return "yellow"
    return "bold red"


class CoachScreen(PanelScreen):
    title_text = "TYPING COACH"
    BINDINGS = [
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
        ("d", "drill", "Drill weak keys"),
    ]

    def action_drill(self) -> None:
        coach = self.app.services.coach  # type: ignore[attr-defined]
        if coach.enough_data():
            self.app.start_drill()  # type: ignore[attr-defined]

    def body(self) -> RenderableType:
        coach = self.app.services.coach  # type: ignore[attr-defined]
        if not coach.enough_data():
            return Text(
                "Play a few races to unlock your coach.\n\n"
                "Once you've typed enough, this shows the keys you miss most, a\n"
                "keyboard heatmap, and how to position your fingers to fix them.",
                justify="center",
                style="grey58",
            )

        weak = coach.weakest_keys()
        return Group(
            self._weak_table(weak),
            Text(""),
            Text("Keyboard heatmap", style="bold"),
            self._heatmap(coach.heatmap()),
            Text("green ≥98%   yellow ≥95%   red <95%   dim = not enough data", style="grey42"),
            Text(""),
            Text("Finger positioning", style="bold"),
            self._tips(weak),
            Text(""),
            Text("press  d  to drill your weak keys", style="bold cyan", justify="center"),
        )

    def _weak_table(self, weak: list[KeyAccuracy]) -> Table:
        tbl = Table(title="Most-missed keys", title_style="bold")
        tbl.add_column("Key", justify="center")
        tbl.add_column("Accuracy", justify="right")
        tbl.add_column("Misses", justify="right")
        tbl.add_column("Attempts", justify="right")
        if not weak:
            tbl.add_row("—", "great!", "0", "—")
        for k in weak:
            tbl.add_row(
                _key_label(k.key),
                Text(f"{k.accuracy * 100:.1f}%", style=_heat_style(k.accuracy)),
                str(k.misses),
                str(k.attempts),
            )
        return tbl

    def _heatmap(self, heat: dict[str, float]) -> Text:
        out = Text()
        for indent, row in enumerate(keyboard.ROWS):
            out.append("  " * indent)
            for ch in row:
                if ch in heat:
                    out.append(f"{ch.upper()} ", style=_heat_style(heat[ch]))
                else:
                    out.append(f"{ch.upper()} ", style="grey37")
            out.append("\n")
        return out

    def _tips(self, weak: list[KeyAccuracy]) -> RenderableType:
        tbl = Table.grid(padding=(0, 2))
        tbl.add_column(justify="center", style="bold cyan")
        tbl.add_column(justify="left")
        shown = 0
        for k in weak:
            info = keyboard.key_info(k.key)
            if info is None:
                continue
            tbl.add_row(_key_label(k.key), info.tip)
            shown += 1
            if shown >= 5:
                break
        if shown == 0:
            return Text("Nothing to fix — your weak keys are all solid.", style="grey58")
        return tbl
