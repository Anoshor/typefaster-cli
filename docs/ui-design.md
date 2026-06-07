# Terminal UI Design — TYPEFASTER-CLI

Textual drives a screen stack; Rich renders content. Keyboard-only, resize-aware.

## Global conventions

- **Navigation:** `↑/↓` or `j/k` move · `Enter` select · `Esc` back · `q` quit · `?` help overlay.
- **Footer:** always shows the current screen's keybindings.
- **Theme (dark default, configurable):** accent = cyan · correct = green ·
  error = red on subtle bg · pending text = dim grey · caret = inverse block.
- **Resize:** layouts use Textual `Grid`/`fr` units; the typing field reflows; bars rescale to width.

## Screen map

```
                        ┌──────────────┐
                        │  MAIN MENU   │
                        └──────┬───────┘
   ┌──────┬──────────┬─────────┼─────────┬──────────┬─────────┐
 Practice  Race    Daily     Stats    History   Profile   Leaderboard  Settings
   │        │        │
   └────────┴────────┴──► RACE SCREEN ──► RESULTS SCREEN ──► (back to menu)
```

## Main Menu

```
┌─ TYPEFASTER ───────────────────────────── v0.1 (offline) ─┐
│                                                            │
│     ⌨   T Y P E F A S T E R                                │
│                                                            │
│      ▸ Quick Race            (30s)                         │
│        Practice                                            │
│        Daily Challenge       ● not played today            │
│        Stats                                               │
│        History                                             │
│        Profile                                             │
│        Leaderboard                                         │
│        Settings                                            │
│                                                            │
│  best wpm 92  ·  races 134  ·  streak 3🔥                  │
└ ↑↓ move  ⏎ select  q quit  ? help ─────────────────────────┘
```

## Countdown (before race)

```
        Get ready…

             3
```

Large centered digit, 1s cadence, then auto-start. Server-controlled in Phase 2.

## Race Screen (centerpiece)

```
┌─ RACE · 60s ──────────────────── ⏱ 42s ──┐
│  WPM 78   ACC 96%   ▓▓▓▓▓▓░░░░ 58%        │   ← live_stats header
├───────────────────────────────────────────┤
│                                           │
│  The quick brown fox jumps over the       │   ← typing_field
│  lazy dog while the ▏clock keeps ticking  │     green=correct red=wrong
│  steadily toward the finish line.         │     dim=upcoming  ▏=caret
│                                           │
├───────────────────────────────────────────┤
│  You    [###########-------] 58%          │   ← progress_bars
│  Ghost  [##############----] 71%  (PB)     │     ghost from replay timeline
└ esc quit  ⏎ restart ───────────────────────┘
```

- Per-char coloring; **backspace allowed** (correct mistakes, original errors still count).
- Caret is an inverse block; mistyped chars highlight in place.
- Ghost bar advances by sampling the stored replay timeline against the live clock.
- Race ends at time-up **or** quote completion.

## Results Screen

```
┌─ RESULTS ─────────────────────────────────┐
│  ✓ You beat your Personal Best ghost!      │
│                                           │
│   WPM       82   (raw 88)                  │
│   Accuracy  97.4%                          │
│   Chars     410 correct · 11 wrong         │
│   Time      60.0s                          │
│                                           │
│   PB  78  →  82  ▲ new best                │
│                                           │
│   You    [##################] 100%         │
│   Ghost  [###############---] 86%          │
└ ⏎ race again   g change ghost   esc menu ──┘
```

## Stats Screen

Rich tables + a sparkline of recent WPM.

```
┌─ STATS ───────────────────────────────────┐
│  Lifetime                                  │
│   Races played   134     Races won   88    │
│   Best WPM        92     Avg WPM     74    │
│   Best accuracy 99.1%    Avg acc   95.2%   │
│   Total chars  248,300   Time   3h 12m     │
│                                           │
│  Per mode      30s    60s    120s          │
│   Best WPM      96     92      89          │
│   Avg  WPM      79     74      71          │
│                                           │
│  Recent WPM  ▁▂▃▅▄▆▇▆█▇                    │
└ esc back ──────────────────────────────────┘
```

## History Screen

Paginated table; `Enter` opens a single race's replay summary.

```
┌─ HISTORY ─────────────────────────────────┐
│  Date         Mode  WPM   Acc   Source     │
│  2026-06-07   60s    82  97.4%  Twain       │
│  2026-06-07   30s    88  98.0%  Austen      │
│  2026-06-06   120s   76  94.1%  Shakespeare │
│  …                                         │
│                              page 1 / 9    │
└ ↑↓ move  ⏎ view  ←→ page  esc back ─────────┘
```

## Profile Screen

```
┌─ PROFILE ─────────────────────────────────┐
│  you                                       │
│  member since  2026-01-14                  │
│                                           │
│  races 134 · best 92 wpm · 95.2% avg acc  │
│  total time 3h 12m · 248,300 chars         │
│                                           │
│  Achievements                              │
│   (online achievements arrive in Phase 2)  │
└ esc back ──────────────────────────────────┘
```

## Daily Challenge Screen

```
┌─ DAILY CHALLENGE · 2026-06-07 ────────────┐
│  Today's quote (same for everyone)         │
│  "It was the best of times…" — Dickens     │
│                                           │
│  Your best today   84 wpm   attempts 3     │
│                                           │
│  Local daily leaderboard                   │
│   1.  84 wpm  97.0%                         │
│   2.  81 wpm  96.2%                         │
│   3.  79 wpm  95.5%                         │
│                                           │
│         ▸ Play today's challenge           │
└ ⏎ play  esc back ──────────────────────────┘
```

## Leaderboard Screen

Phase 1 shows **local** rankings; a banner signals online tiers arriving in Phase 2,
so the screen stays structurally stable.

```
┌─ LEADERBOARD (local) ─────────────────────┐
│  Top runs · 60s                            │
│   1.  92 wpm  98.1%  2026-05-30             │
│   2.  90 wpm  97.4%  2026-06-02             │
│   3.  88 wpm  96.9%  2026-06-07             │
│                                           │
│  🌐 Global / Daily / Weekly leaderboards    │
│     arrive with online mode (Phase 2).     │
└ ←→ mode  esc back ─────────────────────────┘
```

## Settings Screen

```
┌─ SETTINGS ────────────────────────────────┐
│   Theme            ‹ dark ›                │
│   Default race     ‹ 60s ›                 │
│   Backspace        ‹ allowed ›             │
│   Default ghost    ‹ personal-best ›       │
│   Sound (bell)     ‹ off ›                 │
│                                           │
│   Changes save automatically.              │
└ ↑↓ move  ←→ change  esc back ──────────────┘
```

## Widgets

| Widget | Responsibility |
|---|---|
| `typing_field` | live text, per-char coloring, caret, backspace handling |
| `progress_bars` | you-vs-ghost bars, rescale on resize |
| `live_stats` | WPM / accuracy / progress / timer header |
| `countdown` | 3-2-1 pre-race animation |
