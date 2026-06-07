"""Injectable clock so timing stays out of the pure domain and tests stay
deterministic."""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    def now_ms(self) -> int:
        """Monotonic milliseconds. Only differences are meaningful."""
        ...


class SystemClock:
    """Production clock backed by ``time.monotonic``."""

    def now_ms(self) -> int:
        return int(time.monotonic() * 1000)


class FakeClock:
    """Manually advanced clock for tests."""

    def __init__(self, start_ms: int = 0) -> None:
        self._t = start_ms

    def now_ms(self) -> int:
        return self._t

    def advance(self, ms: int) -> None:
        self._t += ms

    def set(self, ms: int) -> None:
        self._t = ms
