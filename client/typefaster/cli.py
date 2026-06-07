"""Typer entry point.

``typefaster`` launches straight into the game. Subcommands cover direct race
launches and non-interactive stats output.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .domain.errors import InvalidRaceModeError
from .domain.models import GhostKind, RaceMode
from .services.container import build_app

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="TYPEFASTER — a terminal-first typing game.",
)
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Launch the game when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        from .ui.app import run

        run()


def _parse_ghost(value: str | None) -> GhostKind | None:
    if value is None:
        return None
    try:
        return GhostKind(value)
    except ValueError as exc:
        raise typer.BadParameter("ghost must be one of: personal-best, last, random") from exc


@app.command()
def race(
    mode: str = typer.Option(
        "quote", "--mode", "-m", help="quote (finish one text) or time (type for N seconds)."
    ),
    time: int = typer.Option(60, "--time", "-t", help="TIME mode duration: 30, 60, or 120."),
    ghost: str | None = typer.Option(
        None, "--ghost", "-g", help="QUOTE mode ghost: personal-best | last | random."
    ),
) -> None:
    """Start a race directly.

    Examples:
      typefaster race                         # quote mode, random text
      typefaster race --ghost personal-best   # quote mode vs your best (same text)
      typefaster race --mode time --time 60   # type for 60 seconds
    """
    from .domain.models import RaceKind
    from .services.race_service import RaceConfig
    from .ui.app import run

    if mode not in ("quote", "time"):
        raise typer.BadParameter("mode must be 'quote' or 'time'")
    if mode == "time":
        try:
            race_mode = RaceMode.from_seconds(time)
        except InvalidRaceModeError as exc:
            raise typer.BadParameter(str(exc)) from exc
        run(initial_race=RaceConfig(kind=RaceKind.TIME, mode=race_mode))
    else:
        run(initial_race=RaceConfig(kind=RaceKind.QUOTE, ghost_kind=_parse_ghost(ghost)))


@app.command()
def daily() -> None:
    """Play today's daily challenge."""
    from .domain.models import RaceKind
    from .services.race_service import RaceConfig
    from .ui.app import run

    run(initial_race=RaceConfig(kind=RaceKind.QUOTE, daily=True))


@app.command()
def profile() -> None:
    """Print your local profile."""
    services = build_app()
    try:
        p = services.profile.get()
        table = Table(title="Profile", show_header=False)
        table.add_column(style="grey58", justify="right")
        table.add_column()
        table.add_row("Name", p.display_name)
        table.add_row("Member since", (p.created_at or "—")[:10])
        table.add_row("Races played", str(p.races_played))
        table.add_row("Races won", str(p.races_won))
        table.add_row("Best WPM", f"{p.best_wpm:.0f}")
        table.add_row("Best accuracy", f"{p.best_accuracy * 100:.1f}%")
        console.print(table)
    finally:
        services.close()


@app.command()
def stats() -> None:
    """Print summary statistics."""
    services = build_app()
    try:
        s = services.stats.summary()
        p = s.profile
        table = Table(title="Stats", show_header=False)
        table.add_column(style="grey58", justify="right")
        table.add_column()
        table.add_row("Races played", str(p.races_played))
        table.add_row("Best WPM", f"{p.best_wpm:.0f}")
        table.add_row("Avg WPM", f"{s.avg_wpm:.0f}")
        table.add_row("Best accuracy", f"{p.best_accuracy * 100:.1f}%")
        table.add_row("Avg accuracy", f"{s.avg_accuracy * 100:.1f}%")
        table.add_row("Total chars", f"{p.total_chars:,}")
        table.add_row("Quote best WPM", f"{s.quote_best_wpm:.0f}")
        for seconds in (30, 60, 120):
            table.add_row(f"Time {seconds}s best WPM", f"{s.time_best_by_mode.get(seconds, 0):.0f}")
        console.print(table)
    finally:
        services.close()


@app.command()
def history(limit: int = typer.Option(20, "--limit", "-n", help="Rows to show.")) -> None:
    """Print recent race history."""
    services = build_app()
    try:
        records = services.stats.history(limit=limit)
        if not records:
            console.print("[grey58]No races yet. Run [bold]typefaster[/] to play![/]")
            return
        table = Table(title="History")
        table.add_column("Date")
        table.add_column("Mode", justify="right")
        table.add_column("WPM", justify="right")
        table.add_column("Acc", justify="right")
        table.add_column("Source")
        for r in records:
            table.add_row(
                r.started_at[:16].replace("T", " "),
                f"{r.mode_seconds}s",
                f"{r.wpm:.0f}",
                f"{r.accuracy * 100:.0f}%",
                (r.quote_source or "—")[:24],
            )
        console.print(table)
    finally:
        services.close()


@app.command()
def reset(
    all: bool = typer.Option(False, "--all", help="Wipe ALL local race history and stats."),
) -> None:
    """Clean up local data. By default removes only impossible (e.g. pasted) runs."""
    services = build_app()
    try:
        if all:
            typer.confirm("Delete ALL local race history and stats?", abort=True)
            services.repo.wipe()
            console.print("[green]All local race data cleared.[/]")
        else:
            removed = services.repo.delete_implausible_races()
            console.print(
                f"[green]Removed {removed} impossible run(s)[/] and recomputed your stats."
            )
    finally:
        services.close()


@app.command()
def version() -> None:
    """Print the version."""
    console.print(f"typefaster {__version__}")


# ── online (Phase 2) commands ──────────────────────────────────────────
from .net import commands as _online  # noqa: E402

app.command("register")(_online.register)
app.command("login")(_online.login)
app.command("logout")(_online.logout)
app.command("leaderboard")(_online.leaderboard)
app.add_typer(_online.lobby_app, name="lobby")
app.add_typer(_online.config_app, name="config")


if __name__ == "__main__":
    app()
