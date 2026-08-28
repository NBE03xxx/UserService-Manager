"""Persistence port for explicitly registered unit IDs."""

from __future__ import annotations

from typing import Protocol

from user_service_manager.domain.models import UnitId


class RegistrationRepository(Protocol):
    def load(self) -> frozenset[UnitId]: ...

    def save(self, unit_ids: frozenset[UnitId]) -> None: ...
