"""Health and readiness endpoints for load balancers and Docker."""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness — process is up."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    """Readiness — Redis is reachable."""
    try:
        await request.app.state.redis.ping()
    except Exception:  # noqa: BLE001 - report any backend failure as not-ready
        return JSONResponse(
            {"status": "not-ready", "redis": "unreachable"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return JSONResponse({"status": "ready", "redis": "ok"})
