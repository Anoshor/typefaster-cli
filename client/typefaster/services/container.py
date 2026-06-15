"""Composition root — wires settings, repository, and services together."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..infra.config import Settings
from ..infra.sqlite_repository import SQLiteRepository
from .coach_service import CoachService
from .daily_service import DailyService
from .ghost_service import GhostService
from .profile_service import ProfileService
from .race_service import RaceService
from .stats_service import StatsService


@dataclass(slots=True)
class App:
    settings: Settings
    repo: SQLiteRepository
    race: RaceService
    profile: ProfileService
    stats: StatsService
    daily: DailyService
    ghosts: GhostService
    coach: CoachService

    def close(self) -> None:
        self.repo.close()


def build_app(db_path: Path | str | None = None) -> App:
    settings = Settings.load()
    repo = SQLiteRepository(db_path)
    return App(
        settings=settings,
        repo=repo,
        race=RaceService(
            repo,
            allow_backspace=settings.allow_backspace,
            lowercase_only=settings.lowercase_only,
            words_only=settings.words_only,
        ),
        profile=ProfileService(repo),
        stats=StatsService(repo),
        daily=DailyService(repo),
        ghosts=GhostService(repo),
        coach=CoachService(repo),
    )
