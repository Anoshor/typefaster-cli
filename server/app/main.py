"""FastAPI application: lifespan, routers, and the lobby WebSocket endpoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import from_url

from .abuse import GlobalRateLimitMiddleware, MessageRateLimiter, client_ip
from .config import get_settings
from .deps import resolve_token
from .logging_config import configure_logging
from .repositories import RedisRepository
from .routers import auth, health, leaderboards, lobbies, oauth
from .ws.manager import Hub

log = logging.getLogger("typefaster.server")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = getattr(app.state, "settings", None) or get_settings()
    configure_logging()
    # Tests may preset app.state.redis (e.g. a fake) before startup.
    redis = getattr(app.state, "redis", None) or from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True
    )
    await redis.ping()
    app.state.settings = settings
    app.state.redis = redis
    app.state.hub = Hub(RedisRepository(redis), settings)
    log.info("server started; redis=%s", settings.redis_url)
    try:
        yield
    finally:
        # Graceful shutdown: cancel in-flight races, close Redis.
        hub: Hub = app.state.hub
        for room in hub.rooms.values():
            if room.race_task:
                room.race_task.cancel()
        await redis.aclose()
        log.info("server stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="TYPEFASTER Server", version="0.1.0", lifespan=lifespan)
    # Order: CORS outermost, then the per-IP flood guard (added last = runs first).
    app.add_middleware(GlobalRateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(oauth.router)
    app.include_router(lobbies.router)
    app.include_router(leaderboards.router)

    @app.websocket("/ws/lobby/{code}")
    async def lobby_ws(websocket: WebSocket, code: str) -> None:
        settings = websocket.app.state.settings
        token = websocket.query_params.get("token", "")
        repo = RedisRepository(websocket.app.state.redis)
        username = await resolve_token(token, repo, settings)
        if username is None:
            await websocket.close(code=4401)  # unauthorized
            return

        # Cap concurrent sockets per IP so one host can't exhaust connections.
        ip = client_ip(websocket.client.host if websocket.client else None)
        if await repo.incr_ws_connections(ip) > settings.ws_max_connections_per_ip:
            await repo.decr_ws_connections(ip)
            await websocket.close(code=4429)  # too many connections
            return

        try:
            await websocket.accept()
            hub: Hub = websocket.app.state.hub
            joined = await hub.join(code, username, websocket)
            if not joined:
                await websocket.close(code=4404)  # lobby not found
                return
            limiter = MessageRateLimiter(
                settings.ws_max_messages_per_window, settings.ws_message_window_seconds
            )
            try:
                while True:
                    raw = await websocket.receive_json()
                    if not limiter.allow():
                        await websocket.close(code=4429)  # message flood
                        break
                    await hub.handle(code, username, raw)
            except WebSocketDisconnect:
                pass
            finally:
                await hub.leave(code, username)
        finally:
            await repo.decr_ws_connections(ip)

    return app


app = create_app()
