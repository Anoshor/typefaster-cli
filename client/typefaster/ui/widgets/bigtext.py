"""Tiny block-font renderer for big, prominent numbers/words (countdown, WPM).

A terminal can't enlarge its own font, so we draw oversized glyphs out of block
characters instead. Supports digits, a few letters, and basic punctuation.
"""

from __future__ import annotations

_H = 5  # rows per glyph
_FONT: dict[str, list[str]] = {
    "0": ["█████", "█   █", "█   █", "█   █", "█████"],
    "1": ["  ██ ", "   █ ", "   █ ", "   █ ", "  ███"],
    "2": ["█████", "    █", "█████", "█    ", "█████"],
    "3": ["█████", "    █", " ████", "    █", "█████"],
    "4": ["█   █", "█   █", "█████", "    █", "    █"],
    "5": ["█████", "█    ", "█████", "    █", "█████"],
    "6": ["█████", "█    ", "█████", "█   █", "█████"],
    "7": ["█████", "    █", "   █ ", "  █  ", "  █  "],
    "8": ["█████", "█   █", "█████", "█   █", "█████"],
    "9": ["█████", "█   █", "█████", "    █", "█████"],
    "G": ["█████", "█    ", "█  ██", "█   █", "█████"],
    "O": ["█████", "█   █", "█   █", "█   █", "█████"],
    "W": ["█   █", "█   █", "█ █ █", "██ ██", "█   █"],
    "P": ["█████", "█   █", "█████", "█    ", "█    "],
    "M": ["█   █", "██ ██", "█ █ █", "█   █", "█   █"],
    "!": ["  █  ", "  █  ", "  █  ", "     ", "  █  "],
    "%": ["█   █", "   █ ", "  █  ", " █   ", "█   █"],
    " ": ["     ", "     ", "     ", "     ", "     "],
    ".": ["     ", "     ", "     ", "     ", "  █  "],
}


def render(text: str) -> str:
    """Render ``text`` as multi-line block art (unsupported chars are skipped)."""
    glyphs = [_FONT.get(ch.upper(), _FONT[" "]) for ch in text]
    rows = []
    for r in range(_H):
        rows.append("  ".join(g[r] for g in glyphs))
    return "\n".join(rows)
