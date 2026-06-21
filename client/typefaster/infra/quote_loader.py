"""Load the bundled quote dataset and seed it into the local database.

``quotes.json`` ships inside the package (``typefaster/assets``). Each entry:
``{"id": "...", "text": "...", "source": "..."}``.

Runtime quote selection (random, daily, by difficulty) is handled by
``SQLiteRepository`` — this module's only runtime role is seeding the DB.
"""

from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from importlib.resources import files

from ..domain.errors import NoQuotesError
from ..domain.models import Difficulty


@lru_cache(maxsize=1)
def _load_raw() -> list[dict[str, str]]:
    resource = files("typefaster.assets").joinpath("quotes.json")
    data: list[dict[str, str]] = json.loads(resource.read_text(encoding="utf-8"))
    if not data:
        raise NoQuotesError("quotes.json is empty")
    return data


def seed_quotes(conn: sqlite3.Connection) -> int:
    """Insert bundled quotes that are not yet in the DB. Idempotent via INSERT OR IGNORE."""
    inserted = 0
    for q in _load_raw():
        text = q["text"]
        cur = conn.execute(
            "INSERT OR IGNORE INTO quote(ext_id, text, source, length, difficulty) VALUES(?, ?, ?, ?, ?)",
            (q["id"], text, q.get("source"), len(text), Difficulty.from_length(len(text)).value),
        )
        inserted += cur.rowcount
    return inserted
