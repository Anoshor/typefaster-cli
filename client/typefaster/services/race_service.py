"""Coordinate a race: choose the text/ghost/mode, then persist the result.

The interactive typing loop lives in the UI layer (Textual), which drives a
``TypingEngine``. This service handles everything around that: setup and
persistence. Keeping it UI-free means the same flow can be reused headlessly
(tests) and adapted server-side in Phase 2.

Two race kinds (see ``RaceKind``):
- QUOTE: one fixed quote, raced to completion. Ghosts (same text) live here.
- TIME: type continuously for N seconds; text streams from many quotes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from ..domain.drills import build_drill
from ..domain.models import Ghost, GhostKind, Quote, RaceKind, RaceMode, RaceResult
from ..domain.text_modifiers import apply_modifiers
from ..infra.repository import Repository
from .ghost_service import GhostService

# Placeholder quote row that TIME-mode races reference (they have no single text).
_TIME_QUOTE = Quote(ext_id="__time_mode__", text="(time mode)", source="Time")

# Synthetic ext_id for coach drills: they feed per-key stats but are not recorded
# as competitive races (no PB, leaderboard, or history).
_DRILL_EXT_ID = "__drill__"


@dataclass(frozen=True, slots=True)
class RaceConfig:
    """A request to start a race (what the UI/CLI chooses)."""

    kind: RaceKind = RaceKind.QUOTE
    mode: RaceMode = RaceMode.NORMAL
    ghost_kind: GhostKind | None = None
    daily: bool = False


@dataclass(slots=True)
class RaceSetup:
    quote: Quote  # the row persisted with the race
    target_text: str  # what the player actually types (streamed for TIME mode)
    kind: RaceKind
    mode: RaceMode  # the time limit for TIME mode (ignored for QUOTE)
    ghost: Ghost | None
    allow_backspace: bool
    is_daily: bool
    started_at: str


@dataclass(slots=True)
class RaceSummary:
    result: RaceResult
    race_id: int
    new_personal_best: bool
    previous_best_wpm: float


class RaceService:
    def __init__(
        self,
        repo: Repository,
        *,
        allow_backspace: bool = True,
        lowercase_only: bool = False,
        words_only: bool = False,
    ) -> None:
        self._repo = repo
        self._ghosts = GhostService(repo)
        self._allow_backspace = allow_backspace
        self._lowercase_only = lowercase_only
        self._words_only = words_only

    def set_modifiers(self, *, lowercase_only: bool, words_only: bool) -> None:
        """Update the active text modifiers live (e.g. from the Settings screen)
        so a toggle applies to the next race without restarting the app."""
        self._lowercase_only = lowercase_only
        self._words_only = words_only

    def _modify(self, text: str) -> str:
        """Apply the active text modifiers to what the player will type. The
        original quote is still persisted; only the target text changes. Ghosts
        stay percentage-based, so they still render over modified text (a
        modified run just isn't apples-to-apples with an unmodified ghost)."""
        return apply_modifiers(text, lowercase=self._lowercase_only, words_only=self._words_only)

    def prepare(
        self,
        *,
        kind: RaceKind = RaceKind.QUOTE,
        mode: RaceMode = RaceMode.NORMAL,
        ghost_kind: GhostKind | None = None,
        daily: bool = False,
    ) -> RaceSetup:
        if kind is RaceKind.TIME:
            return self._prepare_time(mode)
        return self._prepare_quote(mode, ghost_kind, daily)

    def _prepare_quote(
        self, mode: RaceMode, ghost_kind: GhostKind | None, daily: bool
    ) -> RaceSetup:
        ghost: Ghost | None = None
        if daily:
            quote = self._repo.daily_quote(date.today())
            # Daily ghost = your best run on *today's* quote (same text), if any.
            ghost = self._ghosts.best_for_quote(quote.ext_id)
        elif ghost_kind is not None:
            # Explicit "vs PB/Last/Random": race the ghost's exact text for a
            # fair head-to-head.
            ghost = self._ghosts.try_load(ghost_kind)
            quote = ghost.quote if ghost and ghost.quote else self._repo.random_quote()
        else:
            # Quick race: a fresh random quote every time. Attach a ghost only
            # if you've raced this exact quote before.
            quote = self._repo.random_quote()
            ghost = self._ghosts.best_for_quote(quote.ext_id)

        return RaceSetup(
            quote=quote,
            target_text=self._modify(quote.text),
            kind=RaceKind.QUOTE,
            mode=mode,
            ghost=ghost,
            allow_backspace=self._allow_backspace,
            is_daily=daily,
            started_at=datetime.now(UTC).isoformat(),
        )

    def _prepare_time(self, mode: RaceMode) -> RaceSetup:
        # Enough text that even a very fast typist won't run out before time:
        # ~300 WPM * 5 chars = 1500 chars/min, plus a safety buffer.
        target_chars = int(mode.value / 60 * 1500) + 600
        text = self._stream_text(target_chars)
        return RaceSetup(
            quote=_TIME_QUOTE,
            target_text=self._modify(text),
            kind=RaceKind.TIME,
            mode=mode,
            ghost=None,  # ghosts are a QUOTE-mode feature
            allow_backspace=self._allow_backspace,
            is_daily=False,
            started_at=datetime.now(UTC).isoformat(),
        )

    def prepare_drill(self, weak_keys: list[str], *, length: int = 30) -> RaceSetup:
        """Build a practice race whose text is weighted toward the player's weak
        keys. Drills feed the coach's per-key stats but never set records."""
        text = build_drill(weak_keys, list(self._repo.corpus_words()), length=length)
        return RaceSetup(
            quote=Quote(ext_id=_DRILL_EXT_ID, text=text, source="Drill"),
            target_text=text,
            kind=RaceKind.QUOTE,
            mode=RaceMode.NORMAL,
            ghost=None,
            allow_backspace=self._allow_backspace,
            is_daily=False,
            started_at=datetime.now(UTC).isoformat(),
        )

    def finish(self, setup: RaceSetup, result: RaceResult) -> RaceSummary:
        if setup.quote.ext_id == _DRILL_EXT_ID:
            # Practice only: improve the coach heatmap, don't record a race.
            self._repo.record_key_stats(result.key_stats, setup.started_at)
            return RaceSummary(
                result=result, race_id=0, new_personal_best=False, previous_best_wpm=0.0
            )
        # Compare against the best of the *same* kind so the two don't mix.
        previous_best = self._best_wpm_for_kind(result.kind)
        race_id = self._repo.save_race(
            result=result,
            quote=setup.quote,
            started_at=setup.started_at,
            is_daily=setup.is_daily,
        )
        return RaceSummary(
            result=result,
            race_id=race_id,
            new_personal_best=result.wpm > previous_best,
            previous_best_wpm=previous_best,
        )

    def _best_wpm_for_kind(self, kind: RaceKind) -> float:
        if kind is RaceKind.QUOTE:
            best = self._repo.best_quote_run()
            return best[0] if best else 0.0
        return max(self._repo.best_by_mode(RaceKind.TIME).values(), default=0.0)

    def _stream_text(self, min_chars: int) -> str:
        """Concatenate random quotes into one continuous block of >= min_chars."""
        parts: list[str] = []
        total = 0
        while total < min_chars:
            q = self._repo.random_quote()
            parts.append(q.text)
            total += len(q.text) + 1
        return " ".join(parts)
