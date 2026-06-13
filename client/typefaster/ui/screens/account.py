"""In-TUI account screen: register, login (password / GitHub / Google), logout.

Actions are an OptionList (not single-letter keys, which would collide with the
username/password Inputs). Network calls (blocking httpx) run in worker threads
and post results back via ``call_from_thread``.
"""

from __future__ import annotations

import contextlib
import time
import webbrowser

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from ...net.api import ApiClient, ApiError
from ...net.token_store import Session

_ACTIONS = [
    ("register", "Register (username + password)"),
    ("login", "Login (username + password)"),
    ("github", "Login with GitHub (browser)"),
    ("google", "Login with Google (browser)"),
    ("setserver", "Set server URL (from field above)"),
    ("logout", "Logout"),
]


class AccountScreen(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        with Vertical(id="panel-wrap"):
            yield Static(Text("ACCOUNT", justify="center"), id="title")
            yield Static(self._status_text(), id="acct-status")
            yield Input(placeholder="username", id="user")
            yield Input(placeholder="password", password=True, id="pw")
            yield Input(placeholder="server url", id="server", value=Session.load().server_url)
            yield OptionList(*[Option(label, id=key) for key, label in _ACTIONS])
            yield Static(
                Text("Tab between fields · pick an action below · esc back", justify="center"),
                classes="dim",
            )
            yield Static("", id="acct-msg")

    def on_mount(self) -> None:
        self.query_one("#user", Input).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        match event.option.id:
            case "register":
                self._auth("register")
            case "login":
                self._auth("login")
            case "github":
                self._oauth("github")
            case "google":
                self._oauth("google")
            case "setserver":
                self._set_server()
            case "logout":
                self._logout()

    # ── helpers ────────────────────────────────────────────────────────
    def _status_text(self) -> Text:
        s = Session.load()
        who = s.username or "not logged in"
        return Text.from_markup(f"server: [bold]{s.server_url}[/]   ·   [bold cyan]{who}[/]")

    def _msg(self, markup: str) -> None:
        self.query_one("#acct-msg", Static).update(Text.from_markup(markup))

    def _refresh_status(self) -> None:
        self.query_one("#acct-status", Static).update(self._status_text())

    def _field(self, wid: str) -> str:
        return self.query_one(f"#{wid}", Input).value.strip()

    # ── password auth ──────────────────────────────────────────────────
    def _auth(self, kind: str) -> None:
        user, pw = self._field("user"), self._field("pw")
        if not user or not pw:
            self._msg("[red]Enter a username and password first.[/]")
            return
        self._msg(f"[grey58]{kind.title()}ing…[/]")
        self.run_worker(lambda: self._do_auth(kind, user, pw), thread=True, name="auth")

    def _do_auth(self, kind: str, user: str, pw: str) -> None:
        session = Session.load()
        client = ApiClient(session)
        try:
            data = client.register(user, pw) if kind == "register" else client.login(user, pw)
            session.token = data["access_token"]
            session.username = data["username"]
            session.save()
            self.app.call_from_thread(self._on_auth_ok, session.username)
        except ApiError as exc:
            self.app.call_from_thread(self._msg, f"[red]{exc.detail}[/]")
        finally:
            client.close()

    def _on_auth_ok(self, username: str) -> None:
        self._refresh_status()
        self._msg(f"[green]Logged in as[/] [bold]{username}[/]. Press esc, then 'Play Online'.")

    # ── logout / server ────────────────────────────────────────────────
    def _logout(self) -> None:
        self.run_worker(self._do_logout, thread=True, name="logout")

    def _do_logout(self) -> None:
        session = Session.load()
        client = ApiClient(session)
        with contextlib.suppress(ApiError):
            if session.logged_in:
                client.logout()
        client.close()
        session.clear()
        self.app.call_from_thread(self._after_logout)

    def _after_logout(self) -> None:
        self._refresh_status()
        self._msg("[green]Logged out.[/]")

    def _set_server(self) -> None:
        url = self._field("server")
        if not url:
            return
        session = Session.load()
        if url.rstrip("/") != session.server_url:
            session.token = None
            session.username = None
        session.server_url = url.rstrip("/")
        session.save()
        self._refresh_status()
        self._msg(f"[green]Server set to[/] [bold]{session.server_url}[/]")

    # ── OAuth device flow ──────────────────────────────────────────────
    def _oauth(self, provider: str) -> None:
        self._msg(f"[grey58]Starting {provider.title()} login…[/]")
        self.run_worker(lambda: self._do_oauth(provider), thread=True, name="oauth")

    def _do_oauth(self, provider: str) -> None:
        session = Session.load()
        client = ApiClient(session)
        try:
            start = client.oauth_start(provider)
        except ApiError as exc:
            self.app.call_from_thread(
                self._msg, f"[red]{provider.title()} unavailable: {exc.detail}[/]"
            )
            client.close()
            return

        uri, code, device = start["verification_uri"], start["user_code"], start["device_code"]
        interval = int(start.get("interval", 5))
        deadline = time.time() + int(start.get("expires_in", 900))
        self.app.call_from_thread(
            self._msg,
            f"Open [bold underline]{uri}[/] · enter code [bold cyan]{code}[/] · waiting…",
        )
        with contextlib.suppress(Exception):
            webbrowser.open(uri)

        try:
            while time.time() < deadline:
                time.sleep(interval)
                try:
                    r = client.oauth_poll(provider, device)
                except ApiError as exc:
                    self.app.call_from_thread(self._msg, f"[red]Login failed: {exc.detail}[/]")
                    return
                st = r.get("status")
                if st == "pending":
                    continue
                if st == "slow_down":
                    interval += 5
                    continue
                session.token = r["access_token"]
                session.username = r["username"]
                session.save()
                self.app.call_from_thread(self._on_auth_ok, session.username)
                return
            self.app.call_from_thread(self._msg, "[red]Login timed out.[/]")
        finally:
            client.close()

    def action_back(self) -> None:
        self.app.pop_screen()
