"""Normalized journal values that do not expose python-systemd objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class JournalEntry:
    timestamp: datetime
    priority: int
    message: str
    cursor: str
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class JournalPage:
    entries: tuple[JournalEntry, ...]
    older_cursor: str | None
    has_more: bool
