"""Service-list use cases."""

from __future__ import annotations

from user_service_manager.domain.models import Capability, UnitId, UnitRecord
from user_service_manager.ports.service_backend import ServiceBackend


class ServiceCatalog:
    def __init__(self, backend: ServiceBackend) -> None:
        self._backend = backend

    async def load(self) -> tuple[UnitRecord, ...]:
        return tuple(await self._backend.list_units())

    async def operate(self, unit_id: UnitId, capability: Capability) -> UnitRecord:
        result = await self._backend.operate(unit_id, capability)
        return await self._backend.refresh_unit(result.unit_id)
