"""Application use cases for viewing journal entries without persisting them."""

from __future__ import annotations

from user_service_manager.application.discovery_service import DiscoveryService
from user_service_manager.domain.journal import JournalPage
from user_service_manager.domain.models import UnitId
from user_service_manager.ports.journal import JournalPort


class JournalService:
    DEFAULT_LIMIT = 100

    def __init__(self, discovery: DiscoveryService, journal: JournalPort) -> None:
        self._discovery = discovery
        self._journal = journal

    async def read(
        self,
        unit_id: UnitId,
        limit: int = DEFAULT_LIMIT,
        before_cursor: str | None = None,
    ) -> JournalPage:
        records = await self._discovery.scan()
        if not any(record.unit_id == unit_id for record in records):
            raise ValueError(f"Cannot read logs for an undiscovered unit: {unit_id.value}")
        return await self._journal.read(unit_id, limit, before_cursor)
