"""Resolve OS-appropriate data/config locations via platformdirs.

Honors ``TYPEFASTER_DATA_DIR`` for tests and portable installs.
"""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

_APP = "typefaster"


def data_dir() -> Path:
    override = os.environ.get("TYPEFASTER_DATA_DIR")
    base = Path(override) if override else Path(user_data_dir(_APP, appauthor=False))
    base.mkdir(parents=True, exist_ok=True)
    return base


def config_dir() -> Path:
    override = os.environ.get("TYPEFASTER_CONFIG_DIR")
    base = Path(override) if override else Path(user_config_dir(_APP, appauthor=False))
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return data_dir() / "typefaster.db"


def config_path() -> Path:
    return config_dir() / "settings.json"
