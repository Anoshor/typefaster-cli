"""Header line: live WPM / accuracy / progress / timer."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static


class LiveStats(Static):
    def show(self, *, wpm: float, accuracy: float, progress: float, seconds_left: float) -> None:
        text = Text()
        text.append(f"WPM {wpm:5.0f}", style="bold cyan")
        text.append("   ")
        text.append(f"ACC {accuracy * 100:4.0f}%", style="bold green")
        text.append("   ")
        text.append(f"{progress * 100:3.0f}%", style="bold")
        text.append("   ")
        text.append(f"⏱ {max(0, int(seconds_left)):>3}s", style="bold yellow")
        self.update(text)
