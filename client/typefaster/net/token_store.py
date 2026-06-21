"""Local persistence of the auth token and server URL."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit

from ..infra.paths import config_dir

# Single source of truth for the public TYPEFASTER server. A fresh install can
# register/play with zero config; override with `typefaster config set-server`
# (e.g. a local server or your own deployment).
DEFAULT_SERVER_URL = "https://140.245.248.113.sslip.io"


def _auth_path() -> Path:
    return config_dir() / "auth.json"


def _is_ephemeral_host(url: str) -> bool:
    """True for throwaway tunnel hosts that never persist (e.g. Cloudflare
    quick-tunnels). A saved URL like these is always stale and safe to reset."""
    host = (urlsplit(url).hostname or "").lower()
    return host.endswith(".trycloudflare.com")


@dataclass(slots=True)
class Session:
    server_url: str = DEFAULT_SERVER_URL
    token: str | None = None
    username: str | None = None

    @property
    def logged_in(self) -> bool:
        return bool(self.token)

    @classmethod
    def load(cls, path: Path | None = None) -> Session:
        path = path or _auth_path()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        known = set(cls.__slots__)
        session = cls(**{k: v for k, v in data.items() if k in known})
        # Self-heal: a saved ephemeral-tunnel URL (from early testing) is dead and
        # can never come back. Reset it to the default so online play works again
        # without the user having to run `config set-server`.
        if _is_ephemeral_host(session.server_url):
            session.server_url = DEFAULT_SERVER_URL
            session.save(path)
        return session

    def save(self, path: Path | None = None) -> None:
        path = path or _auth_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def clear(self, path: Path | None = None) -> None:
        self.token = None
        self.username = None
        self.save(path)
