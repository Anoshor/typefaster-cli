"""Minimal structured (key=value) logging setup."""

from __future__ import annotations

import logging
import sys


class KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = (
            f'ts={self.formatTime(record, "%Y-%m-%dT%H:%M:%S")} '
            f"level={record.levelname} logger={record.name} "
            f'msg="{record.getMessage()}"'
        )
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"
        return base


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(KeyValueFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
