"""A minimal Textual app that hosts the online race screen for one lobby."""

from __future__ import annotations

from textual.app import App

from .screens.online_race import OnlineRaceScreen
from .theme import APP_CSS


class OnlineApp(App[None]):
    CSS = APP_CSS
    TITLE = "TYPEFASTER · online"

    def __init__(self, ws_url: str, username: str, mode_seconds: int) -> None:
        super().__init__()
        self._args = (ws_url, username, mode_seconds)

    def on_mount(self) -> None:
        self.push_screen(OnlineRaceScreen(*self._args))


def run_online(ws_url: str, username: str, mode_seconds: int) -> None:
    OnlineApp(ws_url, username, mode_seconds).run()
