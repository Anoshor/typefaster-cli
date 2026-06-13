"""In-TUI lobby browser: list public lobbies, create, or join by code.

OptionList-driven (Create / Refresh are list items so there are no single-letter
key collisions with the join-code Input). Joining/creating launches the
OnlineRaceScreen on the app stack, so leaving a race returns here. Network calls
run in worker threads.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from ...net.api import ApiClient, ApiError, ws_url
from ...net.token_store import Session
from .online_race import OnlineRaceScreen


class LobbyBrowserScreen(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        with Vertical(id="panel-wrap"):
            yield Static(Text("PLAY ONLINE — LOBBIES", justify="center"), id="title")
            yield Static("", id="lobby-status")
            yield Input(placeholder="join code — type it and press Enter", id="code")
            yield OptionList(id="lobby-list")
            yield Static(
                Text("⏎ select · type a code + Enter to join · esc back", justify="center"),
                classes="dim",
            )
            yield Static("", id="lobby-msg")

    def on_mount(self) -> None:
        self._refresh()

    def on_screen_resume(self) -> None:
        self._refresh()

    def _session(self) -> Session:
        return Session.load()

    def _msg(self, markup: str) -> None:
        self.query_one("#lobby-msg", Static).update(Text.from_markup(markup))

    # ── listing ────────────────────────────────────────────────────────
    def _refresh(self) -> None:
        s = self._session()
        self.query_one("#lobby-status", Static).update(
            Text.from_markup(
                f"server: [bold]{s.server_url}[/] · [bold cyan]{s.username or 'not logged in'}[/]"
            )
        )
        ol = self.query_one("#lobby-list", OptionList)
        ol.clear_options()
        ol.add_option(Option("➕  Create a lobby", id="__create__"))
        ol.add_option(Option("🔄  Refresh list", id="__refresh__"))
        if not s.logged_in:
            self._msg("[red]Not logged in.[/] esc → Account to log in first.")
            return
        self._msg("Loading lobbies…")
        self.run_worker(self._load, thread=True, name="load")

    def _load(self) -> None:
        client = ApiClient(self._session())
        try:
            lobbies = client.list_lobbies()
            self.app.call_from_thread(self._show_lobbies, lobbies)
        except ApiError as exc:
            self.app.call_from_thread(self._msg, f"[red]{exc.detail}[/]")
        finally:
            client.close()

    def _show_lobbies(self, lobbies: list[dict[str, Any]]) -> None:
        ol = self.query_one("#lobby-list", OptionList)
        for lob in lobbies:
            label = (
                f"{lob['code']}  ·  {lob['name'][:24]}  ·  host {lob['host'][:12]}  "
                f"·  {lob['mode_seconds']}s  ·  {lob['player_count']} players"
            )
            ol.add_option(Option(label, id=f"join:{lob['code']}:{lob['mode_seconds']}"))
        if lobbies:
            self._msg(f"{len(lobbies)} public lobby(ies). ⏎ to join the highlighted one.")
        else:
            self._msg("No public lobbies yet — pick 'Create a lobby'.")

    # ── actions ────────────────────────────────────────────────────────
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        oid = event.option.id or ""
        if oid == "__create__":
            self._create()
        elif oid == "__refresh__":
            self._refresh()
        elif oid.startswith("join:"):
            _, code, mode = oid.split(":")
            self._join(code, int(mode))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        code = event.value.strip().upper()
        if code:
            self._join(code, 0)  # mode learned from the join response

    def _create(self) -> None:
        if not self._session().logged_in:
            self._msg("[red]Log in first (esc → Account).[/]")
            return
        self._msg("[grey58]Creating lobby…[/]")
        self.run_worker(self._do_create, thread=True, name="create")

    def _do_create(self) -> None:
        s = self._session()
        client = ApiClient(s)
        try:
            lob = client.create_lobby(f"{s.username}'s lobby", is_public=True, mode_seconds=60)
            self.app.call_from_thread(self._enter, lob["code"], int(lob["mode_seconds"]))
        except ApiError as exc:
            self.app.call_from_thread(self._msg, f"[red]{exc.detail}[/]")
        finally:
            client.close()

    def _join(self, code: str, mode_hint: int) -> None:
        if not self._session().logged_in:
            self._msg("[red]Log in first (esc → Account).[/]")
            return
        self._msg(f"[grey58]Joining {code}…[/]")
        self.run_worker(lambda: self._do_join(code), thread=True, name="join")

    def _do_join(self, code: str) -> None:
        client = ApiClient(self._session())
        try:
            lob = client.join_lobby(code)
            self.app.call_from_thread(self._enter, lob["code"], int(lob["mode_seconds"]))
        except ApiError as exc:
            self.app.call_from_thread(self._msg, f"[red]{exc.detail}[/]")
        finally:
            client.close()

    def _enter(self, code: str, mode_seconds: int) -> None:
        s = self._session()
        url = ws_url(s.server_url, code, s.token or "")
        self.app.push_screen(OnlineRaceScreen(url, s.username or "you", mode_seconds))

    def action_back(self) -> None:
        self.app.pop_screen()
