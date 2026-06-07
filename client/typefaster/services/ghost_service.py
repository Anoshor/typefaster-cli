"""Build ghost opponents from stored replays."""

from __future__ import annotations

from ..domain.errors import GhostUnavailableError
from ..domain.models import Ghost, GhostKind
from ..infra.repository import Repository

_LABELS = {
    GhostKind.PERSONAL_BEST: "PB",
    GhostKind.LAST: "Last",
    GhostKind.RANDOM: "Random",
}


class GhostService:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def load(self, kind: GhostKind) -> Ghost:
        """Return a ghost for the requested kind, or raise if no data exists."""
        if kind is GhostKind.PERSONAL_BEST:
            data = self._repo.personal_best_replay()
        elif kind is GhostKind.LAST:
            data = self._repo.last_replay()
        else:
            data = self._repo.random_replay()

        if data is None:
            raise GhostUnavailableError(
                f"No historical run available for ghost '{kind.value}'. Finish a race first!"
            )
        timeline, wpm, quote = data
        return Ghost(kind=kind, label=_LABELS[kind], timeline=timeline, wpm=wpm, quote=quote)

    def best_for_quote(self, ext_id: str) -> Ghost | None:
        """A ghost recorded on a specific quote (e.g. your best daily run)."""
        data = self._repo.best_replay_for_quote(ext_id)
        if data is None:
            return None
        timeline, wpm, quote = data
        return Ghost(
            kind=GhostKind.PERSONAL_BEST, label="PB", timeline=timeline, wpm=wpm, quote=quote
        )

    def try_load(self, kind: GhostKind) -> Ghost | None:
        try:
            return self.load(kind)
        except GhostUnavailableError:
            return None
