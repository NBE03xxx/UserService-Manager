"""Use cases for drop-ins and reversible service lifecycle changes."""

from __future__ import annotations

import asyncio

from user_service_manager.application.discovery_service import DiscoveryService
from user_service_manager.domain.lifecycle import (
    DropInSnapshot,
    LifecycleConflictError,
    LifecycleReloadError,
    LifecycleSafetyError,
    PreparedDropInChange,
    PreparedServiceDeletion,
    PreparedServiceRestore,
    unified_preview,
    validate_drop_in_content,
    validate_drop_in_name,
)
from user_service_manager.domain.models import ActiveState, UnitId, UnitRecord
from user_service_manager.ports.commands import UnitCommandPort
from user_service_manager.ports.lifecycle import DropInVerifier, UnitLifecycleStore


class UnitLifecycleService:
    def __init__(
        self,
        store: UnitLifecycleStore,
        verifier: DropInVerifier,
        commands: UnitCommandPort,
        discovery: DiscoveryService,
    ) -> None:
        self._store = store
        self._verifier = verifier
        self._commands = commands
        self._discovery = discovery
        self._locks: dict[UnitId, asyncio.Lock] = {}

    async def list_drop_ins(self, unit_id: UnitId) -> tuple[DropInSnapshot, ...]:
        return await self._store.list_drop_ins(unit_id)

    async def load_drop_in(self, unit_id: UnitId, name: str) -> DropInSnapshot:
        return await self._store.load_drop_in(unit_id, name)

    async def prepare_drop_in(
        self,
        unit_id: UnitId,
        name: str,
        content: str,
        expected_revision: str | None,
    ) -> PreparedDropInChange:
        validate_drop_in_name(name)
        validate_drop_in_content(content)
        before = ""
        if expected_revision is not None:
            current = await self._store.load_drop_in(unit_id, name)
            if current.revision != expected_revision:
                raise LifecycleConflictError("The drop-in changed after it was loaded.")
            before = current.content
        details = await self._verifier.verify_drop_in(unit_id, name, content)
        return PreparedDropInChange(
            unit_id,
            name,
            content,
            expected_revision,
            expected_revision is None,
            details,
            unified_preview(
                before,
                content,
                "/dev/null" if expected_revision is None else f"a/{name}",
                f"b/{name}",
            ),
        )

    async def apply_drop_in(
        self, change: PreparedDropInChange
    ) -> tuple[UnitRecord, ...]:
        async with self._lock(change.unit_id):
            await self._store.save_drop_in(
                change.unit_id,
                change.name,
                change.content,
                change.expected_revision,
            )
            return await self._reload_after_change("The drop-in was saved")

    async def delete_drop_in(
        self, snapshot: DropInSnapshot
    ) -> tuple[UnitRecord, ...]:
        async with self._lock(snapshot.unit_id):
            await self._store.delete_drop_in(snapshot)
            return await self._reload_after_change("The drop-in was deleted")

    async def prepare_delete(self, unit_id: UnitId) -> PreparedServiceDeletion:
        records = await self._discovery.scan()
        record = next((item for item in records if item.unit_id == unit_id), None)
        if record is None:
            raise LifecycleSafetyError("The service is no longer discoverable.")
        if record.active_state not in {ActiveState.INACTIVE, ActiveState.FAILED}:
            raise LifecycleSafetyError("Stop the service before deleting its file.")
        if record.unit_file_state.startswith("enabled"):
            raise LifecycleSafetyError("Disable the service before deleting its file.")
        snapshot = await self._store.load_service_lifecycle(unit_id)
        preview = unified_preview(
            snapshot.service_content,
            "",
            f"a/{unit_id.value}",
            "/dev/null",
        )
        for drop_in in snapshot.drop_ins:
            preview += "\n" + unified_preview(
                drop_in.content,
                "",
                f"a/{unit_id.value}.d/{drop_in.name}",
                "/dev/null",
            )
        return PreparedServiceDeletion(snapshot, preview)

    async def apply_delete(
        self, change: PreparedServiceDeletion
    ) -> tuple[UnitRecord, ...]:
        async with self._lock(change.snapshot.unit_id):
            await self._store.archive_and_delete(change.snapshot)
            return await self._reload_after_change(
                "The service was backed up and deleted"
            )

    async def prepare_restore(self, unit_id: UnitId) -> PreparedServiceRestore:
        backups = await self._store.list_backups(unit_id)
        if not backups:
            raise FileNotFoundError(f"No restorable backup exists for {unit_id.value}.")
        backup = backups[0]
        names = "\n".join(f"  + {name}" for name in backup.drop_in_names)
        preview = f"Restore {unit_id.value} from {backup.created_at.isoformat()}\n"
        if names:
            preview += f"Drop-ins:\n{names}\n"
        return PreparedServiceRestore(backup, preview)

    async def apply_restore(
        self, change: PreparedServiceRestore
    ) -> tuple[UnitRecord, ...]:
        async with self._lock(change.backup.unit_id):
            await self._store.restore(change.backup)
            return await self._reload_after_change("The service backup was restored")

    def _lock(self, unit_id: UnitId) -> asyncio.Lock:
        lock = self._locks.setdefault(unit_id, asyncio.Lock())
        if lock.locked():
            raise LifecycleConflictError(
                f"A lifecycle change is already running for {unit_id.value}."
            )
        return lock

    async def _reload_after_change(self, completed: str) -> tuple[UnitRecord, ...]:
        try:
            await self._commands.reload()
        except Exception as error:
            raise LifecycleReloadError(
                f"{completed}, but the user manager could not be reloaded. "
                f"Reload it before operating the service. Details: {error}"
            ) from error
        return await self._discovery.scan()
