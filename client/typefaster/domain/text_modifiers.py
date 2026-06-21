"""MonkeyType-style text modifiers — pure transforms applied to race text.

These reshape the *target text* a player types (e.g. strip everything down to
lowercase words) without touching the original quote that gets persisted. Kept
dependency-free and deterministic so they're trivially unit-testable.
"""

from __future__ import annotations

import re

_NON_WORD = re.compile(r"[^A-Za-z ]+")
_WHITESPACE = re.compile(r"\s+")


def apply_modifiers(text: str, *, lowercase: bool, words_only: bool) -> str:
    """Apply the active modifiers to ``text``.

    - ``words_only`` keeps only ``[a-z]`` and single spaces (implies lowercase).
    - ``lowercase`` (when words_only is off) just lowercases.

    Never returns an empty string: if a transform would empty the text (e.g. a
    quote made entirely of digits/punctuation), the original is returned, since
    ``TypingEngine`` rejects an empty target.
    """
    out = text
    if words_only:
        out = _WHITESPACE.sub(" ", out)  # tabs/newlines become separators first
        out = _NON_WORD.sub("", out)  # drop punctuation/digits, keep letters + space
        out = _WHITESPACE.sub(" ", out).strip()  # collapse any doubled spaces
        out = out.lower()
    elif lowercase:
        out = out.lower()
    return out or text
