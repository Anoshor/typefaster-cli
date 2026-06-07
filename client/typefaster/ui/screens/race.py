"""The race screen — countdown, live typing, ghost animation.

Drives a pure ``TypingEngine`` from keyboard events and ticks a timer to update
the clock, live stats, and the ghost bar. On finish it dismisses with the
computed ``RaceResult`` so the app can persist it and show results.
"""

from __future__ import annotations

from dataclasses import replace

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Static

from ...domain import anti_cheat
from ...domain.ghost import ghost_won, progress_at
from ...domain.models import RaceKind, RaceResult
from ...domain.typing_engine import TypingEngine
from ...infra.clock import Clock, SystemClock
from ...services.race_service import RaceSetup
from ..widgets import bigtext
from ..widgets.live_stats import LiveStats
from ..widgets.progress_bars import ProgressBars
from ..widgets.typing_field import TypingField

_COUNTDOWN_FROM = 3
_TICK = 1 / 15  # ~15 fps updates


class RaceScreen(Screen[RaceResult | None]):
    BINDINGS = [
        ("escape", "quit_race", "Quit"),
    ]

    def __init__(self, setup: RaceSetup, clock: Clock | None = None) -> None:
        super().__init__()
        self.setup = setup
        self.clock = clock or SystemClock()
        self.engine = TypingEngine(setup.target_text, allow_backspace=setup.allow_backspace)
        # The clock starts on the FIRST keystroke (MonkeyType/TypeRacer style),
        # so _start_ms stays None until the player actually types.
        self._start_ms: int | None = None
        self._typing_enabled = False
        self._finished = False
        self._pasted = False
        self._countdown = _COUNTDOWN_FROM
        self._countdown_timer: Timer | None = None
        self._race_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="race-wrap"):
            yield Static("", id="countdown")
            yield LiveStats()
            yield TypingField()
            yield ProgressBars()
            if self.setup.kind is RaceKind.TIME:
                label = f"TIME mode · {self.setup.mode.value}s"
            else:
                label = f"QUOTE mode · {self.setup.quote.source or 'unknown'}"
            yield Static(f"{label} · esc to quit", classes="dim")

    def on_mount(self) -> None:
        self.query_one(LiveStats).display = False
        self.query_one(TypingField).display = False
        self.query_one(ProgressBars).display = False
        self._render_countdown()
        self._countdown_timer = self.set_interval(1.0, self._tick_countdown)

    # ── countdown ──────────────────────────────────────────────────────
    def _render_countdown(self) -> None:
        big = bigtext.render(str(self._countdown))
        self.query_one("#countdown", Static).update(Text(f"Get ready…\n\n{big}", justify="center"))

    def _tick_countdown(self) -> None:
        self._countdown -= 1
        if self._countdown <= 0:
            # Stop the countdown timer so it can't fire again (and re-run _begin).
            if self._countdown_timer is not None:
                self._countdown_timer.stop()
            self._begin()
            return
        self._render_countdown()

    def _begin(self) -> None:
        if self._typing_enabled:  # guard: only ever begin once
            return
        self.query_one("#countdown", Static).update(
            Text(bigtext.render("GO!"), justify="center", style="bold green")
        )
        self.query_one(LiveStats).display = True
        self.query_one(TypingField).display = True
        self.query_one(ProgressBars).display = True
        self._typing_enabled = True
        # Note: the clock is NOT started here — it starts on the first keystroke.
        self._refresh_field()
        self._race_timer = self.set_interval(_TICK, self._tick_race)

    # ── live loop ──────────────────────────────────────────────────────
    def _elapsed_ms(self) -> int:
        if self._start_ms is None:
            return 0
        return self.clock.now_ms() - self._start_ms

    def _tick_race(self) -> None:
        if self._finished:
            return
        # Before the first keystroke the clock hasn't started: show a full timer.
        if self._start_ms is None:
            self.query_one(LiveStats).show(
                wpm=0.0,
                accuracy=self.engine.live_accuracy(),
                progress=0.0,
                seconds_left=float(self.setup.mode.value),
            )
            self._refresh_bars(0)
            return

        elapsed = self._elapsed_ms()

        if self.setup.kind is RaceKind.TIME:
            limit_ms = self.setup.mode.value * 1000
            seconds_left = (limit_ms - elapsed) / 1000.0
            # TIME mode: progress is how far through the clock we are.
            progress = min(1.0, elapsed / limit_ms) if limit_ms else 0.0
            self.query_one(LiveStats).show(
                wpm=self.engine.live_wpm(max(elapsed, 1)),
                accuracy=self.engine.live_accuracy(),
                progress=progress,
                seconds_left=seconds_left,
            )
            self._refresh_bars(elapsed, player_pct=progress * 100.0)
            if elapsed >= limit_ms or self.engine.finished:
                self._finish(elapsed)
        else:
            # QUOTE mode: no time limit; the clock counts up; end on completion.
            self.query_one(LiveStats).show(
                wpm=self.engine.live_wpm(max(elapsed, 1)),
                accuracy=self.engine.live_accuracy(),
                progress=self.engine.progress,
                seconds_left=elapsed / 1000.0,  # shown as elapsed time
            )
            self._refresh_bars(elapsed, player_pct=self.engine.progress * 100.0)
            if self.engine.finished:
                self._finish(elapsed)

    def _refresh_field(self) -> None:
        self.query_one(TypingField).show(self.engine.target, self.engine.states, self.engine.cursor)

    def _refresh_bars(self, elapsed: int, *, player_pct: float | None = None) -> None:
        ghost = self.setup.ghost
        ghost_pct = None
        ghost_label = ""
        if ghost is not None:
            ghost_pct = progress_at(ghost.timeline, elapsed)
            ghost_label = ghost.label
        if player_pct is None:
            player_pct = self.engine.progress * 100.0
        self.query_one(ProgressBars).show(
            player_pct=player_pct,
            ghost_pct=ghost_pct,
            ghost_label=ghost_label,
        )

    # ── input ──────────────────────────────────────────────────────────
    def on_paste(self, event: events.Paste) -> None:
        # Pasting the quote is not typing — swallow it and flag the race so the
        # result is not recorded.
        if self._typing_enabled and not self._finished:
            self._pasted = True
            event.stop()

    def on_key(self, event: events.Key) -> None:
        if not self._typing_enabled or self._finished:
            return
        if event.key == "backspace":
            if self._start_ms is None:
                return  # nothing typed yet; clock hasn't started
            self.engine.backspace(self._elapsed_ms())
            event.stop()
        elif event.character is not None and event.character.isprintable():
            # The clock starts on the first real keystroke.
            if self._start_ms is None:
                self._start_ms = self.clock.now_ms()
                self.query_one("#countdown", Static).display = False  # hide "GO!"
            self.engine.type_char(event.character, self._elapsed_ms())
            event.stop()
        else:
            return
        self._refresh_field()
        if self.engine.finished:
            self._finish(self._elapsed_ms())

    # ── finish ─────────────────────────────────────────────────────────
    def _finish(self, elapsed: int) -> None:
        if self._finished:
            return
        self._finished = True
        ghost = self.setup.ghost

        # ``ghost_won`` in the result means the *player* beat the ghost: the
        # player completed the quote before the ghost reached 100%. Only
        # meaningful when there is a ghost and the player actually finished.
        player_beat_ghost: bool | None = None
        if ghost is not None and self.engine.finished:
            player_beat_ghost = not ghost_won(ghost.timeline, elapsed)

        mode_seconds = self.setup.mode.value if self.setup.kind is RaceKind.TIME else 0
        result = self.engine.result(
            max(elapsed, 1),
            kind=self.setup.kind,
            mode_seconds=mode_seconds,
            ghost_kind=ghost.kind if ghost else None,
            ghost_won=player_beat_ghost,
        )

        # Reject physically-impossible results (paste, held key, auto-input) so
        # they don't pollute stats or personal bests.
        suspicious, flags = anti_cheat.evaluate(
            wpm=result.wpm,
            raw_wpm=result.raw_wpm,
            duration_ms=result.duration_ms,
            total_keystrokes=self.engine.total_keystrokes,
            quote_length=len(self.setup.quote.text),
            pasted=self._pasted,
        )
        if suspicious:
            result = replace(result, suspicious=True, flags=flags)

        self.dismiss(result)

    def action_quit_race(self) -> None:
        self._finished = True
        self.dismiss(None)
