"""Typer commands for online play: auth, lobbies, leaderboards.

Kept in the net package so the offline CLI core stays free of network concerns.
The online race UI is launched via the Textual app.
"""

from __future__ import annotations

import getpass

import typer
from rich.console import Console
from rich.table import Table

from .api import ApiClient, ApiError, ws_url
from .token_store import Session

console = Console()


def _client() -> tuple[ApiClient, Session]:
    session = Session.load()
    return ApiClient(session), session


def register(
    username: str = typer.Argument(..., help="Desired username (3-24 chars)."),
) -> None:
    """Create an account on the server."""
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        console.print("[red]Passwords do not match.[/]")
        raise typer.Exit(1)
    client, session = _client()
    try:
        data = client.register(username, password)
        session.token = data["access_token"]
        session.username = data["username"]
        session.save()
        console.print(f"[green]Registered and logged in as[/] [bold]{session.username}[/]")
    except ApiError as exc:
        console.print(f"[red]Registration failed:[/] {exc.detail}")
        raise typer.Exit(1) from exc
    finally:
        client.close()


def login(username: str = typer.Argument(..., help="Your username.")) -> None:
    """Log in to the server."""
    password = getpass.getpass("Password: ")
    client, session = _client()
    try:
        data = client.login(username, password)
        session.token = data["access_token"]
        session.username = data["username"]
        session.save()
        console.print(f"[green]Logged in as[/] [bold]{session.username}[/]")
    except ApiError as exc:
        console.print(f"[red]Login failed:[/] {exc.detail}")
        raise typer.Exit(1) from exc
    finally:
        client.close()


def logout() -> None:
    """Log out and clear the local token."""
    client, session = _client()
    try:
        if session.logged_in:
            client.logout()
    except ApiError:
        pass
    finally:
        client.close()
    session.clear()
    console.print("[green]Logged out.[/]")


def _require_login(session: Session) -> None:
    if not session.logged_in:
        console.print("[red]Not logged in.[/] Run [bold]typefaster login <user>[/] first.")
        raise typer.Exit(1)


def leaderboard(
    scope: str = typer.Argument("global", help="global | daily | weekly"),
) -> None:
    """Show an online leaderboard."""
    client, session = _client()
    _require_login(session)
    try:
        data = client.leaderboard(scope)
        table = Table(title=f"{scope.title()} Leaderboard")
        table.add_column("#", justify="right")
        table.add_column("Player")
        table.add_column("WPM", justify="right")
        for e in data["entries"]:
            table.add_row(str(e["rank"]), e["username"], f"{e['wpm']:.0f}")
        console.print(table)
    except ApiError as exc:
        console.print(f"[red]Failed:[/] {exc.detail}")
        raise typer.Exit(1) from exc
    finally:
        client.close()


# ── lobby subcommands ─────────────────────────────────────────────────
lobby_app = typer.Typer(help="Multiplayer lobbies.", no_args_is_help=True)


@lobby_app.command("list")
def lobby_list() -> None:
    """Browse public lobbies."""
    client, session = _client()
    _require_login(session)
    try:
        lobbies = client.list_lobbies()
        if not lobbies:
            console.print("[grey58]No public lobbies. Create one with[/] typefaster lobby create")
            return
        table = Table(title="Public Lobbies")
        table.add_column("Code")
        table.add_column("Name")
        table.add_column("Host")
        table.add_column("Mode", justify="right")
        table.add_column("Players", justify="right")
        for lob in lobbies:
            table.add_row(
                lob["code"],
                lob["name"],
                lob["host"],
                f"{lob['mode_seconds']}s",
                str(lob["player_count"]),
            )
        console.print(table)
    except ApiError as exc:
        console.print(f"[red]Failed:[/] {exc.detail}")
        raise typer.Exit(1) from exc
    finally:
        client.close()


@lobby_app.command("create")
def lobby_create(
    name: str = typer.Option("My Lobby", "--name", "-n"),
    private: bool = typer.Option(False, "--private", help="Create a private (code-only) lobby."),
    time: int = typer.Option(60, "--time", "-t", help="30, 60, or 120."),
) -> None:
    """Create a lobby and enter it."""
    client, session = _client()
    _require_login(session)
    try:
        lob = client.create_lobby(name, is_public=not private, mode_seconds=time)
        console.print(
            f"[green]Created lobby[/] [bold]{lob['code']}[/] "
            f"({'private' if private else 'public'}, {time}s). Entering…"
        )
        _enter_lobby(session, lob["code"], time)
    except ApiError as exc:
        console.print(f"[red]Failed:[/] {exc.detail}")
        raise typer.Exit(1) from exc
    finally:
        client.close()


@lobby_app.command("join")
def lobby_join(code: str = typer.Argument(..., help="Lobby join code, e.g. ABC123.")) -> None:
    """Join a lobby by code and enter it."""
    client, session = _client()
    _require_login(session)
    try:
        lob = client.join_lobby(code.upper())
        console.print(f"[green]Joining[/] [bold]{lob['code']}[/] — {lob['name']}…")
        _enter_lobby(session, lob["code"], lob["mode_seconds"])
    except ApiError as exc:
        console.print(f"[red]Failed:[/] {exc.detail}")
        raise typer.Exit(1) from exc
    finally:
        client.close()


def _enter_lobby(session: Session, code: str, mode_seconds: int) -> None:
    """Launch the Textual online race screen for a lobby."""
    from ..ui.online_app import run_online

    url = ws_url(session.server_url, code, session.token or "")
    run_online(url, session.username or "you", mode_seconds)
