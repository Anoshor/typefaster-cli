"""Shared color tokens and the Textual CSS for the app."""

from __future__ import annotations

# Semantic colors used by Rich renderables (widgets render their own text).
CORRECT = "bold green"
INCORRECT = "bold white on dark_red"
PENDING = "grey42"
CARET = "reverse"
ACCENT = "bold cyan"
MUTED = "grey58"

APP_CSS = """
Screen {
    background: $surface;
    align: center middle;
}

/* Menus/panels: fill most of the terminal instead of a tiny centered box. */
#menu-wrap, #panel-wrap {
    width: 100%;
    height: 100%;
    border: round $primary;
    padding: 2 4;
}

#title {
    content-align: center middle;
    color: $accent;
    text-style: bold;
    padding-bottom: 1;
}

#subtitle {
    content-align: center middle;
    color: $text-muted;
    padding-bottom: 1;
}

OptionList {
    height: auto;
    border: none;
    background: $surface;
}

/* Race: full-bleed so the quote and bars are as large as the terminal allows. */
#race-wrap {
    width: 100%;
    height: 100%;
    border: round $primary;
    padding: 2 4;
}

LiveStats {
    height: 1;
    color: $accent;
    text-style: bold;
    padding-bottom: 1;
}

TypingField {
    height: 1fr;
    min-height: 6;
    padding: 2 2;
    border-top: solid $primary-darken-2;
    border-bottom: solid $primary-darken-2;
}

ProgressBars {
    height: auto;
    padding-top: 1;
}

#countdown {
    content-align: center middle;
    height: 1fr;
    color: $accent;
    text-style: bold;
}

.dim { color: $text-muted; }
"""
