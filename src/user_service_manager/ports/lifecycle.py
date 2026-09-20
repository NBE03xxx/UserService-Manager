"""Ports for drop-in and reversible service lifecycle storage."""

from __future__ import annotations

from typing import Protocol

from user_service_manager.domain.lifecycle import (
    DropInSnapshot,
    ServiceBackup,
    ServiceLifecycleSnapshot,
)
from user_service_manager.domain.models import UnitId


class UnitLifecycleStore(Protocol):
    async def list_drop_ins(self, unit_id: UnitId) -> tuple[DropInSnapshot, ...]: ...

    async def load_drop_in(self, unit_id: UnitId, name: str) -> DropInSnapshot: ...

    async def save_drop_in(
        self,
        unit_id: UnitId,
        name: str,
        content: str,
        expected_revision: str | None,
    ) -> None: ...

    async def delete_drop_in(self, snapshot: DropInSnapshot) -> None: ...

    async def load_service_lifecycle(self, unit_id: UnitId) -> ServiceLifecycleSnapshot: ...

    async def archive_and_delete(self, snapshot: ServiceLifecycleSnapshot) -> ServiceBackup: ...

    async def list_backups(self, unit_id: UnitId) -> tuple[ServiceBackup, ...]: ...

    async def restore(self, backup: ServiceBackup) -> None: ...


class DropInVerifier(Protocol):
    async def verify_drop_in(self, unit_id: UnitId, name: str, content: str) -> str: ...
