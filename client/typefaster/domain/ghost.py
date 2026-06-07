"""Ghost progress sampling and the GhostSource protocol.

A ghost is a stored replay timeline (list of ``ReplayPoint``). During a live
race the UI asks ``progress_at(timeline, t_ms)`` for the ghost's completion
percentage at the current elapsed time, interpolating linearly between points
for smooth animation.
"""

from __future__ import annotations

from typing import Protocol

from .models import Ghost, ReplayPoint


def progress_at(timeline: list[ReplayPoint], t_ms: int) -> float:
    """Return the ghost's progress percentage (0..100) at time ``t_ms``.

    Linearly interpolates between the two surrounding timeline points. Clamps
    to the first/last point outside the recorded range.
    """
    if not timeline:
        return 0.0
    if t_ms <= timeline[0].t_ms:
        return timeline[0].progress_pct
    if t_ms >= timeline[-1].t_ms:
        return timeline[-1].progress_pct

    # Binary-search-free linear scan is fine for short timelines.
    prev = timeline[0]
    for point in timeline[1:]:
        if t_ms <= point.t_ms:
            span = point.t_ms - prev.t_ms
            if span <= 0:
                return point.progress_pct
            ratio = (t_ms - prev.t_ms) / span
            return prev.progress_pct + ratio * (point.progress_pct - prev.progress_pct)
        prev = point
    return timeline[-1].progress_pct


def ghost_won(ghost_timeline: list[ReplayPoint], player_duration_ms: int) -> bool:
    """Whether the ghost finished (reached 100%) before the player did."""
    if not ghost_timeline:
        return False
    for point in ghost_timeline:
        if point.progress_pct >= 100.0:
            return point.t_ms < player_duration_ms
    return False


class GhostSource(Protocol):
    """A source that can produce a ghost to race against.

    Phase 1 implements ``personal-best``, ``last`` and ``random`` over SQLite.
    Phase 2 adds a remote/network-backed source with the same interface.
    """

    def load(self) -> Ghost | None:
        """Return a ghost, or ``None`` if no historical data is available."""
        ...
