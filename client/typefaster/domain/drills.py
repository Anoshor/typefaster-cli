"""Adaptive drill generation — assemble practice text biased toward weak keys.

Pure and deterministic (the word list and RNG are injected). The service layer
supplies words from the quote corpus.
"""

from __future__ import annotations

import random


def build_drill(
    weak_keys: list[str],
    words: list[str],
    *,
    length: int = 30,
    rng: random.Random | None = None,
) -> str:
    """Return a space-joined drill of ``length`` words, weighted so words
    containing the player's weak keys appear more often. Falls back to a plain
    random sample when there are no weak keys or no matching words."""
    rng = rng or random.Random()
    clean = [w.lower() for w in words if w.isalpha()]
    if not clean:
        raise ValueError("no words available to build a drill")

    weak = {c.lower() for c in weak_keys if c.strip()}  # ignore the space key
    if not weak:
        return " ".join(rng.choices(clean, k=length))

    # Weight each word by how many distinct weak keys it exercises.
    scored = [(w, sum(1 for ch in set(w) if ch in weak)) for w in clean]
    weighted = [(w, s) for w, s in scored if s > 0]
    if not weighted:
        weighted = [(w, 1) for w in clean]

    population = [w for w, _ in weighted]
    weights = [s for _, s in weighted]
    return " ".join(rng.choices(population, weights=weights, k=length))
