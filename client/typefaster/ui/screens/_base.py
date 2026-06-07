"""Shared base for read-only panel screens (esc to go back)."""

from __future__ import annotations

from rich.console import RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static


class PanelScreen(Screen[None]):
    """A titled, scrollable panel. Subclasses implement ``body``."""

    title_text: str = "PANEL"
    BINDINGS = [("escape", "back", "Back"), ("q", "back", "Back")]

    def compose(self) -> ComposeResult:
        with Vertical(id="panel-wrap"):
            yield Static(Text(self.title_text, justify="center"), id="title")
            with VerticalScroll():
                yield Static(self.body())
            yield Static("esc back", classes="dim")

    def body(self) -> RenderableType:  # pragma: no cover - overridden
        return Text("")

    def action_back(self) -> None:
        self.app.pop_screen()
