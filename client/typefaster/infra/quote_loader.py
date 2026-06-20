"""Load the bundled quote dataset and select quotes.

``quotes.json`` ships inside the package (``typefaster/assets``). Each entry:
``{"id": "...", "text": "...", "source": "..."}``.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import date
from functools import lru_cache
from importlib.resources import files

from ..domain.errors import NoQuotesError
from ..domain.models import Difficulty, Quote


@lru_cache(maxsize=1)
def _load_raw() -> list[dict[str, str]]:
    resource = files("typefaster.assets").joinpath("quotes.json")
    data: list[dict[str, str]] = json.loads(resource.read_text(encoding="utf-8"))
    if not data:
        raise NoQuotesError("quotes.json is empty")
    return data


def all_quotes() -> list[Quote]:
    return [Quote(ext_id=q["id"], text=q["text"], source=q.get("source")) for q in _load_raw()]


def random_quote(rng: random.Random | None = None) -> Quote:
    quotes = all_quotes()
    if not quotes:
        raise NoQuotesError("no quotes available")
    r = rng or random
    return r.choice(quotes)


def quotes_by_difficulty(difficulty: Difficulty) -> list[Quote]:
    return [q for q in all_quotes() if q.difficulty == difficulty]


@lru_cache(maxsize=1)
def corpus_words() -> tuple[str, ...]:
    """Distinct lowercase alphabetic words from the quote corpus, for building
    typing drills. Cached since the corpus is static."""
    seen: set[str] = set()
    for quote in all_quotes():
        for raw in quote.text.split():
            word = "".join(c for c in raw if c.isalpha()).lower()
            if 2 <= len(word) <= 12:
                seen.add(word)
    return tuple(sorted(seen))


def daily_quote(day: date | None = None) -> Quote:
    """Deterministically pick the same quote for everyone on a given UTC day."""
    quotes = all_quotes()
    if not quotes:
        raise NoQuotesError("no quotes available")
    day = day or date.today()
    digest = hashlib.sha256(day.isoformat().encode("utf-8")).hexdigest()
    index = int(digest, 16) % len(quotes)
    return quotes[index]
