"""Discovery ports implemented by filesystem and systemd adapters."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from user_service_manager.domain.discovery import UnitFileCandidate, UnitSnapshot
from user_service_manager.domain.models import UnitId


class UnitFileScanner(Protocol):
    def scan(self) -> Sequence[UnitFileCandidate]: ...


class UnitQuery(Protocol):
    async def query(self, unit_id: UnitId) -> UnitSnapshot: ...


class UnitQueryError(RuntimeError):
    def __init__(self, unit_id: UnitId, message: str) -> None:
        super().__init__(message)
        self.unit_id = unit_id
