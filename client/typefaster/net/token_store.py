"""Local persistence of the auth token and server URL."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..infra.paths import config_dir


def _auth_path() -> Path:
    return config_dir() / "auth.json"


@dataclass(slots=True)
class Session:
    # Default points at the public TYPEFASTER server so a fresh install can
    # register/play with zero config. Override with `typefaster config set-server`
    # (e.g. a local server or your own deployment).
    server_url: str = "https://typefaster-cli.fly.dev"
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
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: Path | None = None) -> None:
        path = path or _auth_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def clear(self, path: Path | None = None) -> None:
        self.token = None
        self.username = None
        self.save(path)
