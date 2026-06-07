"""End-to-end WebSocket race flow: join → ready → server-start → finish.

Exercises the server-authoritative race loop and result validation, plus the
leaderboard write-through that a clean finish produces.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from .conftest import auth_header, register


def _drain_until(ws, target: str, max_msgs: int = 25) -> dict:  # type: ignore[no-untyped-def]
    """Read frames until one of ``target`` type is seen; return it."""
    for _ in range(max_msgs):
        msg = ws.receive_json()
        if msg["type"] == target:
            return msg
    raise AssertionError(f"did not receive {target}")


def test_full_race_flow_records_score(client: TestClient) -> None:
    token = register(client, "racer")
    # Host creates a lobby over REST, then plays it over WS.
    code = client.post(
        "/lobbies", json={"name": "WS Race", "mode_seconds": 60}, headers=auth_header(token)
    ).json()["code"]

    with client.websocket_connect(f"/ws/lobby/{code}?token={token}") as ws:
        # Initial join frames arrive (PLAYER_JOINED / LOBBY_UPDATE).
        ws.send_json({"type": "SET_READY", "data": {"ready": True}})

        start = _drain_until(ws, "RACE_START")
        assert start["data"]["text"]
        assert start["data"]["mode_seconds"] == 60
        text = start["data"]["text"]

        # Report a clean, plausible finish.
        ws.send_json(
            {
                "type": "FINISH",
                "data": {
                    "duration_ms": 30_000,
                    "correct_chars": len(text),
                    "incorrect_chars": 0,
                    "total_keystrokes": len(text),
                    "correct_keystrokes": len(text),
                    "pasted": False,
                },
            }
        )

        # Expect a per-player RACE_FINISHED, then a final standings RACE_FINISHED.
        finished = _drain_until(ws, "RACE_FINISHED")
        assert "wpm" in finished["data"] or finished["data"].get("final")

    # Score should now appear on the global leaderboard.
    board = client.get("/leaderboards/global", headers=auth_header(token)).json()
    assert any(e["username"] == "racer" for e in board["entries"])


def test_unauthorized_ws_rejected(client: TestClient) -> None:
    token = register(client, "ghost")
    code = client.post(
        "/lobbies", json={"name": "Closed", "mode_seconds": 30}, headers=auth_header(token)
    ).json()["code"]
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/lobby/{code}?token=not-a-real-token") as ws:
            ws.receive_json()
