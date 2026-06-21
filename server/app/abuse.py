"""Application-layer abuse / flood mitigation.

This is *not* DDoS protection — a volumetric flood must be absorbed upstream
(e.g. Cloudflare). These guards stop spam and amateur floods cheaply: a global
per-IP HTTP request cap and a per-connection WebSocket message cap. Both lean on
the same Redis fixed-window counter used elsewhere.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .repositories import RedisRepository

# Health/readiness probes must never be throttled (monitoring + load balancers).
_EXEMPT_PATHS = frozenset({"/healthz", "/readyz"})


def client_ip(scope_host: str | None) -> str:
    """Normalize a possibly-missing client host into a stable bucket key.

    The real client IP is available because uvicorn runs with --proxy-headers,
    so request.client.host / websocket.client.host reflect X-Forwarded-For.
    """
    return scope_host or "unknown"


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP fixed-window cap across all HTTP requests (a coarse flood guard on
    top of the stricter per-route auth limits)."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)
        settings = request.app.state.settings
        repo = RedisRepository(request.app.state.redis)
        ip = client_ip(request.client.host if request.client else None)
        count = await repo.incr_rate(f"rl:global:{ip}", settings.global_rate_window)
        if count > settings.global_rate_limit:
            return JSONResponse(
                {"detail": "Too many requests — please slow down."}, status_code=429
            )
        return await call_next(request)


class MessageRateLimiter:
    """In-memory fixed-window message cap for a single WebSocket connection.

    Kept off Redis deliberately: a per-message round-trip would add latency to
    the hot race loop, and a connection-local counter is enough to stop one
    socket from flooding the server.
    """

    def __init__(
        self,
        max_messages: int,
        window_seconds: float,
        *,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max = max_messages
        self._window = window_seconds
        self._now = now
        self._window_start = now()
        self._count = 0

    def allow(self) -> bool:
        """Record a message; return False if this connection is over its cap."""
        t = self._now()
        if t - self._window_start >= self._window:
            self._window_start = t
            self._count = 0
        self._count += 1
        return self._count <= self._max
