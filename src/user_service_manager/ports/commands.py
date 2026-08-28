"""Ports for changes to the systemd user manager."""

from __future__ import annotations

from typing import Protocol

from user_service_manager.domain.models import Capability, UnitId


class UnitCommandPort(Protocol):
    async def operate(self, unit_id: UnitId, capability: Capability) -> None: ...

    async def reload(self) -> None: ...


class UnitCommandError(RuntimeError):
    pass
