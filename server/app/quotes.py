"""Server-side quote selection for multiplayer races.

A compact embedded set keeps the server self-contained. The daily pick is
deterministic (same quote for everyone on a given UTC day), mirroring the
client's offline daily challenge.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import date

_QUOTES: list[tuple[str, str]] = [
    ("q-srv-001", "The quick brown fox jumps over the lazy dog near the riverbank."),
    ("q-srv-002", "Practice makes progress, and progress compounds into mastery over time."),
    ("q-srv-003", "A smooth keyboard rhythm beats a frantic burst of speed every single time."),
    ("q-srv-004", "Type with intent, breathe with calm, and let accuracy lead your pace."),
    ("q-srv-005", "Small consistent gains turn an ordinary typist into a remarkable one."),
    ("q-srv-006", "Focus on the next word, not the whole paragraph, and the speed will follow."),
    ("q-srv-007", "Every champion was once a beginner who refused to give up too early."),
    ("q-srv-008", "The race is long, but in the end it is only with yourself."),
    ("q-srv-009", "Clean fingers, steady wrists, and a quiet mind make a fast keyboard."),
    ("q-srv-010", "Speed is built on the quiet foundation of relentless, careful repetition."),
    ("q-srv-011", "Read ahead, trust your hands, and never look back at a finished word."),
    ("q-srv-012", "Consistency is the secret ingredient that separates good from great."),
    ("q-srv-013", "When the countdown ends, let your training take over and simply flow."),
    ("q-srv-014", "Mistakes are data; correct them calmly and keep moving toward the finish."),
    ("q-srv-015", "A relaxed hand travels faster than a tense one across the home row."),
    ("q-srv-016", "The finish line rewards rhythm far more than it rewards raw panic."),
    ("q-srv-017", "Great typists make it look easy because they made it hard in practice."),
    ("q-srv-018", "Keep your eyes on the text and let your fingers remember the rest."),
    ("q-srv-019", "Momentum is fragile; protect it by keeping every keystroke deliberate."),
    ("q-srv-020", "Win the next word, then the next, and the race quietly wins itself."),
]


def random_quote() -> tuple[str, str]:
    return secrets.choice(_QUOTES)


def daily_quote(day: date | None = None) -> tuple[str, str]:
    day = day or date.today()
    digest = hashlib.sha256(day.isoformat().encode()).hexdigest()
    return _QUOTES[int(digest, 16) % len(_QUOTES)]


def get_quote(quote_id: str) -> tuple[str, str] | None:
    for qid, text in _QUOTES:
        if qid == quote_id:
            return qid, text
    return None
