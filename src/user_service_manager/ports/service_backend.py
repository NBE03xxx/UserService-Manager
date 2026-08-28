"""Port implemented by systemd and mock adapters."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from user_service_manager.domain.models import Capability, UnitId, UnitRecord


class ServiceBackend(Protocol):
    async def list_units(self) -> Sequence[UnitRecord]: ...

    async def refresh_unit(self, unit_id: UnitId) -> UnitRecord: ...

    async def operate(self, unit_id: UnitId, capability: Capability) -> UnitRecord: ...
