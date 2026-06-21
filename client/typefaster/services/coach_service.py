"""Typing coach — deterministic analysis over local per-key stats.

Fully offline and free: ranks the keys you miss most and exposes a per-key
accuracy map. No network, no LLM. Reads the running ``key_stats`` aggregate the
repository accumulates after every race.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..infra.repository import Repository


@dataclass(frozen=True, slots=True)
class KeyAccuracy:
    key: str
    attempts: int
    misses: int
    accuracy: float  # 0..1


class CoachService:
    # Below this many total keypresses the data is too thin to coach on.
    MIN_TOTAL_ATTEMPTS = 50

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def enough_data(self) -> bool:
        stats = self._repo.get_key_stats()
        return sum(attempts for attempts, _ in stats.values()) >= self.MIN_TOTAL_ATTEMPTS

    def weakest_keys(self, *, min_attempts: int = 20, limit: int = 10) -> list[KeyAccuracy]:
        """Keys with the worst accuracy, ignoring keys with too few attempts so a
        single typo can't dominate. Worst first; ties broken by more attempts."""
        out: list[KeyAccuracy] = []
        for key, (attempts, misses) in self._repo.get_key_stats().items():
            if attempts < min_attempts:
                continue
            accuracy = (attempts - misses) / attempts
            out.append(KeyAccuracy(key=key, attempts=attempts, misses=misses, accuracy=accuracy))
        out.sort(key=lambda k: (k.accuracy, -k.attempts))
        return out[:limit]

    def heatmap(self) -> dict[str, float]:
        """Per-key accuracy (0..1) for every key seen, for rendering."""
        return {
            key: (attempts - misses) / attempts
            for key, (attempts, misses) in self._repo.get_key_stats().items()
            if attempts > 0
        }
