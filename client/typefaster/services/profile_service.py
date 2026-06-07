"""Profile read/repair operations."""

from __future__ import annotations

from ..domain.models import Profile
from ..infra.repository import Repository


class ProfileService:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def get(self) -> Profile:
        return self._repo.get_profile()

    def repair(self) -> Profile:
        """Recompute denormalized aggregates from the race table."""
        return self._repo.recompute_profile()
