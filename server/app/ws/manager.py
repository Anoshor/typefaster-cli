"""Connection hub and server-authoritative race orchestration.

The server owns all race timing. Clients never decide when a race starts or
ends; they only report progress and a final result, which the server validates
with shared scoring + anti-cheat before recording it.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import WebSocket
from typefaster_shared import anti_cheat, scoring
from typefaster_shared.events import (
    ClientCommand,
    Envelope,
    PlayerState,
    ServerEvent,
)

from ..config import Settings
from ..quotes import random_quote
from ..repositories import RedisRepository

log = logging.getLogger("typefaster.ws")


class Room:
    def __init__(self, code: str) -> None:
        self.code = code
        self.connections: dict[str, WebSocket] = {}
        self.results: dict[str, dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.race_task: asyncio.Task[None] | None = None
        self.all_finished = asyncio.Event()


class Hub:
    def __init__(self, repo: RedisRepository, settings: Settings) -> None:
        self.repo = repo
        self.settings = settings
        self.rooms: dict[str, Room] = {}

    def room(self, code: str) -> Room:
        return self.rooms.setdefault(code, Room(code))

    # ── send / broadcast ───────────────────────────────────────────────
    async def _send(self, ws: WebSocket, env: Envelope) -> None:
        try:
            await ws.send_text(env.model_dump_json())
        except Exception:  # noqa: BLE001 - socket may be closing
            pass

    async def broadcast(self, code: str, env: Envelope) -> None:
        room = self.rooms.get(code)
        if not room:
            return
        await asyncio.gather(*(self._send(ws, env) for ws in list(room.connections.values())))

    async def _broadcast_lobby(self, code: str) -> None:
        lobby = await self.repo.get_lobby(code)
        if not lobby:
            return
        players = await self.repo.get_players(code)
        await self.broadcast(
            code,
            Envelope.of(
                ServerEvent.LOBBY_UPDATE,
                code=code,
                name=lobby["name"],
                host=lobby["host"],
                status=lobby["status"],
                mode_seconds=int(lobby["mode_seconds"]),
                players=[p.model_dump() for p in players],
            ),
        )

    # ── lifecycle ──────────────────────────────────────────────────────
    async def join(self, code: str, username: str, ws: WebSocket) -> bool:
        lobby = await self.repo.get_lobby(code)
        if lobby is None:
            await self._send(ws, Envelope.of(ServerEvent.ERROR, message="Lobby not found"))
            return False
        room = self.room(code)
        room.connections[username] = ws
        await self.repo.upsert_player(code, PlayerState(username=username))
        await self.broadcast(code, Envelope.of(ServerEvent.PLAYER_JOINED, username=username))
        await self._broadcast_lobby(code)
        return True

    async def leave(self, code: str, username: str) -> None:
        room = self.rooms.get(code)
        if not room:
            return
        room.connections.pop(username, None)
        remaining = await self.repo.remove_player(code, username)
        await self.broadcast(code, Envelope.of(ServerEvent.PLAYER_LEFT, username=username))

        lobby = await self.repo.get_lobby(code)
        if lobby and remaining == 0:
            # Last player left — destroy the lobby.
            if room.race_task:
                room.race_task.cancel()
            await self.repo.delete_lobby(code)
            self.rooms.pop(code, None)
            return
        if lobby and lobby["host"] == username and remaining > 0:
            # Transfer host to the next player.
            players = await self.repo.get_players(code)
            new_host = players[0].username
            await self.repo.set_host(code, new_host)
            await self.broadcast(code, Envelope.of(ServerEvent.HOST_CHANGED, host=new_host))
        await self._broadcast_lobby(code)

    # ── command handling ───────────────────────────────────────────────
    async def handle(self, code: str, username: str, raw: dict[str, Any]) -> None:
        try:
            command = ClientCommand(raw.get("type"))
        except ValueError:
            return
        data = raw.get("data", {}) or {}

        if command is ClientCommand.SET_READY:
            await self._set_ready(code, username, bool(data.get("ready", True)))
        elif command is ClientCommand.PROGRESS:
            await self._progress(code, username, data)
        elif command is ClientCommand.FINISH:
            await self._finish(code, username, data)
        elif command is ClientCommand.CHAT:
            await self.broadcast(
                code,
                Envelope.of(
                    ServerEvent.CHAT_MESSAGE,
                    username=username,
                    message=str(data.get("message", "")),
                ),
            )
        elif command is ClientCommand.LEAVE:
            await self.leave(code, username)

    async def _set_ready(self, code: str, username: str, ready: bool) -> None:
        player = await self.repo.get_player(code, username)
        if not player:
            return
        player.ready = ready
        await self.repo.upsert_player(code, player)
        await self.broadcast(
            code, Envelope.of(ServerEvent.READY_STATE, username=username, ready=ready)
        )
        await self._broadcast_lobby(code)
        await self._maybe_start(code)

    async def _progress(self, code: str, username: str, data: dict[str, Any]) -> None:
        player = await self.repo.get_player(code, username)
        if not player or player.finished:
            return
        player.progress = float(data.get("progress", 0.0))
        player.wpm = float(data.get("wpm", 0.0))
        await self.repo.upsert_player(code, player)
        await self.broadcast(
            code,
            Envelope.of(
                ServerEvent.RACE_PROGRESS,
                username=username,
                progress=player.progress,
                wpm=player.wpm,
            ),
        )

    async def _finish(self, code: str, username: str, data: dict[str, Any]) -> None:
        race = await self.repo.get_race(code)
        if not race:
            return
        duration_ms = int(data.get("duration_ms", 0))
        correct = int(data.get("correct_chars", 0))
        total_ks = int(data.get("total_keystrokes", 0))
        correct_ks = int(data.get("correct_keystrokes", 0))
        pasted = bool(data.get("pasted", False))

        # Server recomputes the score; the client's numbers are ignored.
        wpm = round(scoring.wpm(correct, duration_ms), 2)
        raw = round(scoring.raw_wpm(total_ks, duration_ms), 2)
        acc = round(scoring.accuracy(correct_ks, total_ks), 4)
        report = anti_cheat.evaluate(
            wpm=wpm,
            raw_wpm=raw,
            duration_ms=duration_ms,
            total_keystrokes=total_ks,
            quote_length=len(race["text"]),
            correct_chars=correct,
            pasted=pasted,
        )

        room = self.room(code)
        room.results[username] = {
            "username": username,
            "wpm": wpm,
            "raw_wpm": raw,
            "accuracy": acc,
            "duration_ms": duration_ms,
            "suspicious": report.suspicious,
            "flags": list(report.reasons),
        }
        player = await self.repo.get_player(code, username)
        if player:
            player.finished = True
            player.progress = 100.0
            player.wpm = wpm
            await self.repo.upsert_player(code, player)

        if report.ok:
            await self.repo.record_score(username, wpm)
            await self.repo.bump_user_stats(username, wpm)

        await self.broadcast(
            code,
            Envelope.of(
                ServerEvent.RACE_FINISHED,
                username=username,
                wpm=wpm,
                accuracy=acc,
                suspicious=report.suspicious,
                flags=list(report.reasons),
            ),
        )

        # If everyone connected has finished, end the race early.
        players = await self.repo.get_players(code)
        if players and all(p.finished for p in players):
            room.all_finished.set()

    # ── race orchestration (server-authoritative) ──────────────────────
    async def _maybe_start(self, code: str) -> None:
        lobby = await self.repo.get_lobby(code)
        if not lobby or lobby["status"] != "waiting":
            return
        players = await self.repo.get_players(code)
        if not players or not all(p.ready for p in players):
            return
        room = self.room(code)
        if room.race_task and not room.race_task.done():
            return
        room.race_task = asyncio.create_task(self._run_race(code, int(lobby["mode_seconds"])))

    async def _run_race(self, code: str, mode_seconds: int) -> None:
        room = self.room(code)
        room.results.clear()
        room.all_finished.clear()
        try:
            await self.repo.set_lobby_status(code, "countdown")
            for n in range(self.settings.countdown_seconds, 0, -1):
                await self.broadcast(code, Envelope.of(ServerEvent.RACE_COUNTDOWN, count=n))
                await asyncio.sleep(1)

            quote_id, text = random_quote()
            start_ms = int(time.time() * 1000)
            await self.repo.set_race(
                code, quote_id=quote_id, text=text, mode_seconds=mode_seconds, start_ms=start_ms
            )
            await self.repo.set_lobby_status(code, "racing")
            await self.broadcast(
                code,
                Envelope.of(
                    ServerEvent.RACE_START,
                    quote_id=quote_id,
                    text=text,
                    mode_seconds=mode_seconds,
                    server_start_ms=start_ms,
                ),
            )

            # Run until time expires or everyone finishes.
            try:
                await asyncio.wait_for(room.all_finished.wait(), timeout=mode_seconds)
            except TimeoutError:
                pass

            standings = sorted(room.results.values(), key=lambda r: r["wpm"], reverse=True)
            await self.broadcast(
                code, Envelope.of(ServerEvent.RACE_FINISHED, final=True, standings=standings)
            )
            await self._reset_for_next(code)
        except asyncio.CancelledError:  # lobby destroyed mid-race
            raise
        except Exception:  # noqa: BLE001
            log.exception("race loop failed for lobby %s", code)

    async def _reset_for_next(self, code: str) -> None:
        await self.repo.set_lobby_status(code, "waiting")
        for player in await self.repo.get_players(code):
            await self.repo.upsert_player(code, PlayerState(username=player.username))
        await self._broadcast_lobby(code)
