"""Ports used by the service-file editing application service."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from user_service_manager.domain.editing import UnitFileSnapshot
from user_service_manager.domain.models import UnitId


class UnitFileStore(Protocol):
    async def load(self, unit_id: UnitId) -> UnitFileSnapshot: ...

    async def save(
        self,
        unit_id: UnitId,
        content: str,
        expected_revision: str | None,
        create_backup: bool,
    ) -> Path | None: ...


class UnitFileVerifier(Protocol):
    async def verify(self, unit_id: UnitId, content: str) -> str: ...

