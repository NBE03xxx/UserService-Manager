"""Port for bounded, unit-specific journal reads."""

from __future__ import annotations

from typing import Protocol

from user_service_manager.domain.journal import JournalPage
from user_service_manager.domain.models import UnitId


class JournalPort(Protocol):
    async def read(
        self, unit_id: UnitId, limit: int, before_cursor: str | None = None
    ) -> JournalPage: ...


class JournalReadError(RuntimeError):
    pass
