"""Serialize/deserialize replay timelines to the compact ``{t, p}`` JSON form."""

from __future__ import annotations

import json

from ..domain.models import ReplayPoint


def serialize(timeline: list[ReplayPoint]) -> str:
    return json.dumps([{"t": p.t_ms, "p": p.progress_pct} for p in timeline])


def deserialize(blob: str) -> list[ReplayPoint]:
    raw = json.loads(blob)
    return [ReplayPoint(t_ms=int(item["t"]), progress_pct=float(item["p"])) for item in raw]
