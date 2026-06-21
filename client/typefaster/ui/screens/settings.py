"""Settings screen — toggle/cycle options; changes persist immediately."""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from ...infra.config import Settings


class SettingsScreen(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    _THEMES = ["dark", "light"]
    _TIMES = [30, 60, 120]
    _GHOSTS = ["personal-best", "last", "random"]

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-wrap"):
            yield Static(Text("SETTINGS", justify="center"), id="title")
            yield OptionList(id="settings-list")
            yield Static("⏎ change value    esc back (auto-saves)", classes="dim")

    def on_mount(self) -> None:
        self._refresh()
        self.query_one(OptionList).focus()

    def _settings(self) -> Settings:
        return self.app.services.settings  # type: ignore[attr-defined,no-any-return]

    def _refresh(self) -> None:
        s = self._settings()
        ol = self.query_one(OptionList)
        ol.clear_options()
        rows = [
            ("theme", f"Theme           ‹ {s.theme} ›"),
            ("default_time", f"Default race    ‹ {s.default_time}s ›"),
            (
                "allow_backspace",
                f"Backspace       ‹ {'allowed' if s.allow_backspace else 'strict'} ›",
            ),
            ("default_ghost", f"Default ghost   ‹ {s.default_ghost} ›"),
            ("sound", f"Sound (bell)    ‹ {'on' if s.sound else 'off'} ›"),
            ("lowercase_only", f"Lowercase only  ‹ {'on' if s.lowercase_only else 'off'} ›"),
            ("words_only", f"Words only      ‹ {'on' if s.words_only else 'off'} ›"),
        ]
        for key, label in rows:
            ol.add_option(Option(label, id=key))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        s = self._settings()
        key = event.option.id
        if key == "theme":
            s.theme = self._cycle(self._THEMES, s.theme)
        elif key == "default_time":
            s.default_time = self._cycle(self._TIMES, s.default_time)
        elif key == "allow_backspace":
            s.allow_backspace = not s.allow_backspace
        elif key == "default_ghost":
            s.default_ghost = self._cycle(self._GHOSTS, s.default_ghost)
        elif key == "sound":
            s.sound = not s.sound
        elif key == "lowercase_only":
            s.lowercase_only = not s.lowercase_only
        elif key == "words_only":
            s.words_only = not s.words_only
        s.save()
        # Apply text-modifier changes to the live race service immediately.
        if key in ("lowercase_only", "words_only"):
            self.app.services.race.set_modifiers(  # type: ignore[attr-defined]
                lowercase_only=s.lowercase_only, words_only=s.words_only
            )
        idx = event.option_index
        self._refresh()
        self.query_one(OptionList).highlighted = idx

    @staticmethod
    def _cycle(values: list[Any], current: Any) -> Any:
        try:
            i = values.index(current)
        except ValueError:
            i = -1
        return values[(i + 1) % len(values)]

    def action_back(self) -> None:
        self.app.pop_screen()
