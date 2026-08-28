"""Safety-gated use cases for systemd user-manager changes."""

from __future__ import annotations

import asyncio

from user_service_manager.application.discovery_service import DiscoveryService
from user_service_manager.domain.models import Capability, UnitId, UnitRecord
from user_service_manager.ports.commands import UnitCommandPort


class CommandRejected(PermissionError):
    pass


class UnitCommandService:
    CHANGE_CAPABILITIES = frozenset(
        {
            Capability.START,
            Capability.STOP,
            Capability.RESTART,
            Capability.ENABLE,
            Capability.DISABLE,
        }
    )

    def __init__(self, discovery: DiscoveryService, commands: UnitCommandPort) -> None:
        self._discovery = discovery
        self._commands = commands
        self._locks: dict[UnitId, asyncio.Lock] = {}
        self._reload_lock = asyncio.Lock()

    async def operate(
        self, unit_id: UnitId, capability: Capability
    ) -> tuple[UnitRecord, ...]:
        if capability not in self.CHANGE_CAPABILITIES:
            raise CommandRejected(f"Unsupported change operation: {capability.value}")
        lock = self._locks.setdefault(unit_id, asyncio.Lock())
        if lock.locked():
            raise CommandRejected(f"An operation is already running for {unit_id.value}")
        async with lock:
            records = await self._discovery.scan()
            record = next((item for item in records if item.unit_id == unit_id), None)
            if record is None or not record.supports(capability):
                raise CommandRejected(
                    f"The latest safety assessment does not allow {capability.value} "
                    f"for {unit_id.value}"
                )
            await self._commands.operate(unit_id, capability)
            return await self._discovery.scan()

    async def reload(self) -> tuple[UnitRecord, ...]:
        if self._reload_lock.locked():
            raise CommandRejected("A user-manager reload is already running")
        async with self._reload_lock:
            await self._commands.reload()
            return await self._discovery.scan()
