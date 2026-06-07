"""Renders the target text with per-character correctness coloring + caret."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from .. import theme


class TypingField(Static):
    """Displays the quote, coloring each character by typed state."""

    def show(self, target: str, states: list[bool | None], cursor: int) -> None:
        text = Text()
        for i, ch in enumerate(target):
            if i == cursor:
                text.append(ch, style=theme.CARET)
            elif i < cursor:
                state = states[i]
                if state is True:
                    text.append(ch, style=theme.CORRECT)
                else:
                    # Wrong char: keep the *target* glyph visible, mark it red.
                    text.append(ch, style=theme.INCORRECT)
            else:
                text.append(ch, style=theme.PENDING)
        self.update(text)
