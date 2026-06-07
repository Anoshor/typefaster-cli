"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from typefaster.domain.models import Quote
from typefaster.infra.clock import FakeClock
from typefaster.infra.sqlite_repository import SQLiteRepository


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def repo(db_path: Path) -> SQLiteRepository:
    r = SQLiteRepository(db_path)
    yield r
    r.close()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def quote() -> Quote:
    return Quote(ext_id="t0001", text="the quick brown fox", source="Test")
