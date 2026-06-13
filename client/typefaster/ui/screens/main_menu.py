"""Main menu — keyboard-driven entry point."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from ...domain.models import RaceKind, RaceMode
from ...services.race_service import RaceConfig

_TIMES = [30, 60, 120]


class MainMenu(Screen[None]):
    BINDINGS = [
        ("q", "quit_app", "Quit"),
        ("question_mark", "help", "Help"),
        ("left", "time_change(-1)", "−time"),
        ("right", "time_change(1)", "+time"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._time_seconds = 60

    def _time_label(self) -> str:
        return f"Time Attack  ‹ {self._time_seconds}s ›   (←/→ to change)"

    def _items(self) -> list[tuple[str, str]]:
        return [
            ("quick", "▸ Quick Race  (new quote each time)"),
            ("time", self._time_label()),
            ("practice", "Practice"),
            ("daily", "Daily Challenge"),
            ("stats", "Stats"),
            ("history", "History"),
            ("profile", "Profile"),
            ("leaderboard", "Leaderboard"),
            ("settings", "Settings"),
            ("quit", "Quit"),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-wrap"):
            yield Static(Text("⌨  T Y P E F A S T E R", justify="center"), id="title")
            yield Static(self._tagline(), id="subtitle")
            yield OptionList(*[Option(label, id=key) for key, label in self._items()])
            yield Static(
                Text("crafted by Anoshor Paul", justify="center"),
                id="byline",
                classes="dim",
            )

    def _tagline(self) -> Text:
        p = self.app.services.profile.get()  # type: ignore[attr-defined]
        return Text(
            f"best {p.best_wpm:.0f} wpm  ·  races {p.races_played}  ·  offline mode",
            justify="center",
        )

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    # ── inline duration selector on the Time Attack row ────────────────
    def action_time_change(self, delta: int) -> None:
        ol = self.query_one(OptionList)
        highlighted = ol.highlighted
        # Only adjust when the Time Attack row is the highlighted one.
        if highlighted is None or ol.get_option_at_index(highlighted).id != "time":
            return
        i = (_TIMES.index(self._time_seconds) + delta) % len(_TIMES)
        self._time_seconds = _TIMES[i]
        ol.replace_option_prompt("time", self._time_label())

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        app = self.app
        match event.option.id:
            case "quick":
                app.start_race(  # type: ignore[attr-defined]
                    RaceConfig(kind=RaceKind.QUOTE, ghost_kind=None)
                )
            case "time":
                app.start_race(  # type: ignore[attr-defined]
                    RaceConfig(kind=RaceKind.TIME, mode=RaceMode(self._time_seconds))
                )
            case "quit":
                app.exit()
            case None:
                return
            case name:
                app.open(name)  # type: ignore[attr-defined]

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_help(self) -> None:
        self.app.open("help")  # type: ignore[attr-defined]
