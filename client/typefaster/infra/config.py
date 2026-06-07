"""User settings persistence.

Settings (not gameplay data) are stored as a small JSON file in the OS config
dir. Gameplay data lives in SQLite per the project's storage policy.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import config_path


@dataclass(slots=True)
class Settings:
    theme: str = "dark"
    default_time: int = 60
    allow_backspace: bool = True
    default_ghost: str = "personal-best"
    sound: bool = False

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        path = path or config_path()
        if not path.exists():
            settings = cls()
            settings.save(path)
            return settings
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        known = set(cls.__slots__)
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: Path | None = None) -> None:
        path = path or config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
