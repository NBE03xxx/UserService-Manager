"""Deterministic backend used by phase-one UI and tests."""

from __future__ import annotations

from dataclasses import replace

from user_service_manager.domain.models import (
    AccessMode,
    ActiveState,
    Capability,
    LoadState,
    RegistrationState,
    UnitId,
    UnitRecord,
)


class MockServiceBackend:
    def __init__(self, units: tuple[UnitRecord, ...] | None = None) -> None:
        initial = units if units is not None else self.sample_units()
        self._units = {unit.unit_id: unit for unit in initial}

    @staticmethod
    def sample_units() -> tuple[UnitRecord, ...]:
        common = frozenset(
            {
                Capability.START,
                Capability.STOP,
                Capability.RESTART,
                Capability.ENABLE,
                Capability.DISABLE,
                Capability.STATUS,
                Capability.LOGS,
            }
        )
        return (
            UnitRecord(
                UnitId("evening-coffee.service"),
                "Coffee notes sync",
                LoadState.LOADED,
                ActiveState.ACTIVE,
                "running",
                "enabled",
                "/home/demo/.config/systemd/user/evening-coffee.service",
                AccessMode.MANAGEABLE,
                RegistrationState.REGISTERED,
                common,
            ),
            UnitRecord(
                UnitId("quiet-backup.service"),
                "Quiet workspace backup",
                LoadState.LOADED,
                ActiveState.INACTIVE,
                "dead",
                "disabled",
                "/home/demo/.config/systemd/user/quiet-backup.service",
                AccessMode.MANAGEABLE,
                RegistrationState.REGISTERED,
                common,
            ),
            UnitRecord(
                UnitId("shared-runtime.service"),
                "Shared runtime observer",
                LoadState.LOADED,
                ActiveState.INACTIVE,
                "dead",
                "static",
                "/home/demo/.config/systemd/user/shared-runtime.service",
                AccessMode.READ_ONLY,
                RegistrationState.REGISTERED,
                frozenset({Capability.STATUS, Capability.LOGS}),
                ("A user-managed workload is outside the allowed area.",),
            ),
        )

    async def list_units(self) -> tuple[UnitRecord, ...]:
        return tuple(sorted(self._units.values(), key=lambda unit: unit.unit_id.value))

    async def refresh_unit(self, unit_id: UnitId) -> UnitRecord:
        return self._units[unit_id]

    async def operate(self, unit_id: UnitId, capability: Capability) -> UnitRecord:
        unit = self._units[unit_id]
        if not unit.supports(capability):
            raise PermissionError(f"Capability {capability} is not allowed for {unit_id.value}")

        if capability is Capability.START:
            unit = replace(unit, active_state=ActiveState.ACTIVE, sub_state="running")
        elif capability is Capability.STOP:
            unit = replace(unit, active_state=ActiveState.INACTIVE, sub_state="dead")
        elif capability is Capability.RESTART:
            unit = replace(unit, active_state=ActiveState.ACTIVE, sub_state="running")
        elif capability is Capability.ENABLE:
            unit = replace(unit, unit_file_state="enabled")
        elif capability is Capability.DISABLE:
            unit = replace(unit, unit_file_state="disabled")

        self._units[unit_id] = unit
        return unit
