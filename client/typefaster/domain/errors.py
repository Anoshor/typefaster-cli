"""Domain-level exceptions."""

from __future__ import annotations


class TypefasterError(Exception):
    """Base class for all application errors."""


class NoQuotesError(TypefasterError):
    """Raised when the quote dataset is empty or missing."""


class GhostUnavailableError(TypefasterError):
    """Raised when a requested ghost has no historical data to race against."""


class InvalidRaceModeError(TypefasterError):
    """Raised when an unsupported race duration is requested."""
