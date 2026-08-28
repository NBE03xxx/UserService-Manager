"""Bounded python-systemd journal adapter for one user service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
from typing import Any, Callable

from systemd import journal

from user_service_manager.domain.journal import JournalEntry, JournalPage
from user_service_manager.domain.models import UnitId
from user_service_manager.ports.journal import JournalReadError


class SystemdJournalReader:
    MAX_LIMIT = 200
    MAX_MESSAGE_CHARS = 8_192

    def __init__(self, reader_factory: Callable[[], Any] = journal.Reader) -> None:
        self._reader_factory = reader_factory

    async def read(
        self, unit_id: UnitId, limit: int, before_cursor: str | None = None
    ) -> JournalPage:
        safe_limit = max(1, min(limit, self.MAX_LIMIT))
        return await asyncio.to_thread(
            self._read_sync, unit_id, safe_limit, before_cursor
        )

    def _read_sync(
        self, unit_id: UnitId, limit: int, before_cursor: str | None
    ) -> JournalPage:
        try:
            reader = self._reader_factory()
            uid = os.getuid()
            reader.add_match(_UID=uid, _SYSTEMD_USER_UNIT=unit_id.value)
            reader.add_disjunction()
            reader.add_match(_UID=uid, USER_UNIT=unit_id.value)
            if before_cursor:
                reader.seek_cursor(before_cursor)
            else:
                reader.seek_tail()

            entries: list[JournalEntry] = []
            attempts = 0
            max_attempts = limit + 2
            while len(entries) <= limit and attempts < max_attempts:
                attempts += 1
                raw = reader.get_previous()
                if not raw:
                    break
                cursor = str(raw.get("__CURSOR") or "")
                if before_cursor and cursor == before_cursor:
                    continue
                entries.append(self._normalize(raw))
        except Exception as error:
            raise JournalReadError(str(error)) from error

        has_more = len(entries) > limit
        visible = tuple(entries[:limit])
        return JournalPage(
            entries=visible,
            older_cursor=visible[-1].cursor if visible else None,
            has_more=has_more,
        )

    def _normalize(self, raw: dict[str, object]) -> JournalEntry:
        value = raw.get("MESSAGE", "")
        if isinstance(value, bytes):
            message = value.decode("utf-8", errors="replace")
        else:
            message = str(value)
        truncated = len(message) > self.MAX_MESSAGE_CHARS
        if truncated:
            message = message[: self.MAX_MESSAGE_CHARS] + "…"

        timestamp = raw.get("__REALTIME_TIMESTAMP")
        if not isinstance(timestamp, datetime):
            timestamp = datetime.now(timezone.utc)
        priority_value = raw.get("PRIORITY", 6)
        try:
            priority = int(priority_value)
        except (TypeError, ValueError):
            priority = 6
        priority = min(7, max(0, priority))
        return JournalEntry(
            timestamp=timestamp,
            priority=priority,
            message=message,
            cursor=str(raw.get("__CURSOR") or ""),
            truncated=truncated,
        )
