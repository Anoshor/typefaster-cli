"""Typer commands for online play: auth, lobbies, leaderboards.

Kept in the net package so the offline CLI core stays free of network concerns.
The online race UI is launched via the Textual app.
"""

from __future__ import annotations

import contextlib
import getpass
import time
import webbrowser

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


def login(
    username: str | None = typer.Argument(None, help="Your username (password login)."),
    github: bool = typer.Option(False, "--github", help="Log in with GitHub (browser)."),
    google: bool = typer.Option(False, "--google", help="Log in with Google (browser)."),
) -> None:
    """Log in to the server (password, or --github / --google)."""
    if github or google:
        _oauth_login("github" if github else "google")
        return
    if not username:
        console.print("[red]Provide a username, or use[/] --github / --google.")
        raise typer.Exit(1)
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


def _oauth_login(provider: str) -> None:
    """Run the OAuth device flow: show a code, open the browser, poll for token."""
    client, session = _client()
    try:
        try:
            start = client.oauth_start(provider)
        except ApiError as exc:
            console.print(f"[red]{provider.title()} login unavailable:[/] {exc.detail}")
            raise typer.Exit(1) from exc

        uri = start["verification_uri"]
        code = start["user_code"]
        device = start["device_code"]
        interval = int(start.get("interval", 5))
        deadline = time.time() + int(start.get("expires_in", 900))

        console.print(
            f"\n  Open [bold underline]{uri}[/]\n" f"  Enter code: [bold cyan]{code}[/]\n"
        )
        with contextlib.suppress(Exception):
            webbrowser.open(uri)
        console.print("[grey58]Waiting for authorization…[/] (Ctrl-C to cancel)")

        while time.time() < deadline:
            time.sleep(interval)
            try:
                r = client.oauth_poll(provider, device)
            except ApiError as exc:
                console.print(f"[red]Login failed:[/] {exc.detail}")
                raise typer.Exit(1) from exc
            status_ = r.get("status")
            if status_ == "pending":
                continue
            if status_ == "slow_down":
                interval += 5
                continue
            session.token = r["access_token"]
            session.username = r["username"]
            session.save()
            console.print(f"[green]Logged in as[/] [bold]{session.username}[/]")
            return
        console.print("[red]Login timed out — please try again.[/]")
        raise typer.Exit(1)
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


# ── config subcommands ────────────────────────────────────────────────
config_app = typer.Typer(help="Client configuration (server URL, etc).", no_args_is_help=True)


@config_app.command("set-server")
def config_set_server(
    url: str = typer.Argument(..., help="Server base URL, e.g. https://abc.trycloudflare.com"),
) -> None:
    """Point this client at a server (local, tunnel, or deployed)."""
    session = Session.load()
    new_url = url.rstrip("/")
    if new_url != session.server_url:
        # Tokens are server-specific — clear on change to avoid stale auth.
        session.token = None
        session.username = None
    session.server_url = new_url
    session.save()
    console.print(f"[green]Server set to[/] [bold]{session.server_url}[/]. Now log in or register.")


@config_app.command("show")
def config_show() -> None:
    """Show the current client configuration."""
    s = Session.load()
    table = Table(show_header=False)
    table.add_column(style="grey58", justify="right")
    table.add_column()
    table.add_row("Server URL", s.server_url)
    table.add_row("Logged in as", s.username or "[grey58]not logged in[/]")
    console.print(table)


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
