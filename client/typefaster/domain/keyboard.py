"""Static QWERTY touch-typing model — which finger reaches each key and how.

Pure reference data (no I/O), used by the typing coach to give finger-position
guidance and to lay out the per-key heatmap. Keyed by the lowercase character,
matching how ``TypingEngine`` records key stats.
"""

from __future__ import annotations

from dataclasses import dataclass

# Visual rows for the heatmap, left-to-right, top-to-bottom.
ROWS: tuple[str, ...] = ("qwertyuiop", "asdfghjkl", "zxcvbnm")

# Finger assignment for the standard touch-typing layout.
_FINGER: dict[str, str] = {
    **dict.fromkeys("qaz", "left pinky"),
    **dict.fromkeys("wsx", "left ring"),
    **dict.fromkeys("edc", "left middle"),
    **dict.fromkeys("rfvtgb", "left index"),
    **dict.fromkeys("yhnujm", "right index"),
    **dict.fromkeys("ik,", "right middle"),
    **dict.fromkeys("ol.", "right ring"),
    **dict.fromkeys("p;/", "right pinky"),
    " ": "thumb",
}

# The resting (home-row) key for each finger.
_HOME: dict[str, str] = {
    "left pinky": "a",
    "left ring": "s",
    "left middle": "d",
    "left index": "f",
    "right index": "j",
    "right middle": "k",
    "right ring": "l",
    "right pinky": ";",
    "thumb": "space",
}

HOME_ROW: frozenset[str] = frozenset("asdfjkl;")


@dataclass(frozen=True, slots=True)
class KeyInfo:
    finger: str
    home_key: str
    tip: str


def key_info(ch: str) -> KeyInfo | None:
    """Finger/home/tip for a single key, or None if it's not on the model
    (e.g. digits or symbols we don't coach)."""
    ch = ch.lower()
    finger = _FINGER.get(ch)
    if finger is None:
        return None
    home = _HOME[finger]
    if ch == " ":
        tip = "tap with your thumb"
    elif ch in HOME_ROW:
        tip = f"home row — rest your {finger} here"
    elif _row_of(ch) == 0:
        tip = f"reach up from {home.upper()} with your {finger}"
    else:
        tip = f"reach down from {home.upper()} with your {finger}"
    return KeyInfo(finger=finger, home_key=home, tip=tip)


def _row_of(ch: str) -> int:
    for i, row in enumerate(ROWS):
        if ch in row:
            return i
    return 1  # default to home row
