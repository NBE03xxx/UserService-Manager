"""Use cases for loading, validating, and atomically saving service files."""

from __future__ import annotations

from user_service_manager.application.discovery_service import DiscoveryService
from user_service_manager.domain.editing import (
    PreparedUnitChange,
    UnitFileSnapshot,
    UnitReloadError,
)
from user_service_manager.domain.models import UnitId, UnitRecord
from user_service_manager.ports.commands import UnitCommandPort
from user_service_manager.ports.editing import UnitFileStore, UnitFileVerifier


class UnitEditingService:
    def __init__(
        self,
        store: UnitFileStore,
        verifier: UnitFileVerifier,
        commands: UnitCommandPort,
        discovery: DiscoveryService,
    ) -> None:
        self._store = store
        self._verifier = verifier
        self._commands = commands
        self._discovery = discovery

    async def load(self, unit_id: UnitId) -> UnitFileSnapshot:
        return await self._store.load(unit_id)

    async def prepare(
        self,
        unit_id: UnitId,
        content: str,
        expected_revision: str | None,
    ) -> PreparedUnitChange:
        if expected_revision is not None:
            current = await self._store.load(unit_id)
            if current.revision != expected_revision:
                from user_service_manager.domain.editing import EditConflictError

                raise EditConflictError("The service file changed after it was loaded.")
        details = await self._verifier.verify(unit_id, content)
        return PreparedUnitChange(
            unit_id,
            content,
            expected_revision,
            expected_revision is None,
            details,
        )

    async def apply(
        self,
        change: PreparedUnitChange,
        create_backup: bool,
    ) -> tuple[UnitRecord, ...]:
        await self._store.save(
            change.unit_id,
            change.content,
            change.expected_revision,
            create_backup,
        )
        try:
            await self._commands.reload()
        except Exception as error:
            raise UnitReloadError(
                "The service file was saved, but the user manager could not be reloaded. "
                "Fix the reported problem and reload the user manager before operating it. "
                f"Details: {error}"
            ) from error
        return await self._discovery.scan()
