"""The Textual application — screen orchestration and race flow."""

from __future__ import annotations

from textual.app import App

from ..domain.models import RaceResult
from ..services.container import App as Services
from ..services.container import build_app
from ..services.race_service import RaceConfig, RaceSetup
from .screens.daily import DailyScreen
from .screens.help import HelpScreen
from .screens.history import HistoryScreen
from .screens.leaderboard import LeaderboardScreen
from .screens.main_menu import MainMenu
from .screens.practice import PracticeScreen
from .screens.profile import ProfileScreen
from .screens.race import RaceScreen
from .screens.results import ResultsScreen
from .screens.settings import SettingsScreen
from .screens.stats import StatsScreen
from .theme import APP_CSS

_PANELS = {
    "practice": PracticeScreen,
    "daily": DailyScreen,
    "stats": StatsScreen,
    "history": HistoryScreen,
    "profile": ProfileScreen,
    "leaderboard": LeaderboardScreen,
    "settings": SettingsScreen,
    "help": HelpScreen,
}


class TypefasterApp(App[None]):
    """Offline TYPEFASTER terminal app."""

    CSS = APP_CSS
    TITLE = "TYPEFASTER"

    def __init__(
        self,
        services: Services | None = None,
        *,
        initial_race: RaceConfig | None = None,
    ) -> None:
        super().__init__()
        self.services: Services = services or build_app()
        self._last_config: RaceConfig | None = None
        self._initial_race = initial_race

    def on_mount(self) -> None:
        self.push_screen(MainMenu())
        if self._initial_race is not None:
            self.start_race(self._initial_race)

    # ── navigation helper used by screens ──────────────────────────────
    def open(self, name: str) -> None:
        """Push a fresh panel screen by name so its data is always current."""
        self.push_screen(_PANELS[name]())

    # ── race flow ──────────────────────────────────────────────────────
    def start_race(self, config: RaceConfig) -> None:
        setup = self.services.race.prepare(
            kind=config.kind,
            mode=config.mode,
            ghost_kind=config.ghost_kind,
            daily=config.daily,
        )
        self._last_config = config
        self.push_screen(RaceScreen(setup), lambda result: self._after_race(setup, result))

    def _after_race(self, setup: RaceSetup, result: RaceResult | None) -> None:
        if result is None:
            return  # race quit — return to whatever is underneath
        if result.suspicious:
            # Implausible run (paste/auto-input): show it, but do not record it.
            self.push_screen(ResultsScreen(result, setup, summary=None), self._after_results)
            return
        summary = self.services.race.finish(setup, result)
        self.push_screen(ResultsScreen(result, setup, summary=summary), self._after_results)

    def _after_results(self, action: str | None) -> None:
        if action == "again" and self._last_config is not None:
            self.start_race(self._last_config)

    def on_unmount(self) -> None:
        self.services.close()


def run(initial_race: RaceConfig | None = None) -> None:
    TypefasterApp(initial_race=initial_race).run()
