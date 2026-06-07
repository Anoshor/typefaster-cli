"""Practice mode — pick a race configuration, then race."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from ...domain.models import GhostKind, RaceKind, RaceMode
from ...services.race_service import RaceConfig


class PracticeScreen(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    _ITEMS: list[tuple[str, str, RaceConfig]] = [
        ("q_rand", "Quote · random", RaceConfig(kind=RaceKind.QUOTE)),
        (
            "q_pb",
            "Quote · vs Personal Best ghost",
            RaceConfig(kind=RaceKind.QUOTE, ghost_kind=GhostKind.PERSONAL_BEST),
        ),
        (
            "q_last",
            "Quote · vs Last race ghost",
            RaceConfig(kind=RaceKind.QUOTE, ghost_kind=GhostKind.LAST),
        ),
        (
            "q_rng",
            "Quote · vs Random ghost",
            RaceConfig(kind=RaceKind.QUOTE, ghost_kind=GhostKind.RANDOM),
        ),
        ("t30", "Time Attack · 30s", RaceConfig(kind=RaceKind.TIME, mode=RaceMode.SHORT)),
        ("t60", "Time Attack · 60s", RaceConfig(kind=RaceKind.TIME, mode=RaceMode.NORMAL)),
        ("t120", "Time Attack · 120s", RaceConfig(kind=RaceKind.TIME, mode=RaceMode.LONG)),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-wrap"):
            yield Static(Text("PRACTICE", justify="center"), id="title")
            yield OptionList(*[Option(label, id=key) for key, label, _ in self._ITEMS])
            yield Static("esc back", classes="dim")

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        for key, _, config in self._ITEMS:
            if key == event.option.id:
                self.app.start_race(config)  # type: ignore[attr-defined]
                return

    def action_back(self) -> None:
        self.app.pop_screen()
