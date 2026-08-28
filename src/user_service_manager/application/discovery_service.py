"""Discovery, explicit registration, and missing-unit use cases."""

from __future__ import annotations

import asyncio
from pathlib import Path

from user_service_manager.adapters.path_policy import ServicePathPolicy
from user_service_manager.domain.discovery import (
    PathAssessment,
    ResolutionState,
    UnitFileCandidate,
    UnitSnapshot,
)
from user_service_manager.domain.models import (
    AccessMode,
    ActiveState,
    Capability,
    LoadState,
    RegistrationState,
    UnitId,
    UnitRecord,
)
from user_service_manager.ports.discovery import UnitFileScanner, UnitQuery, UnitQueryError
from user_service_manager.ports.registration import RegistrationRepository


class FragmentPathPolicy:
    def __init__(self, home: Path | None = None) -> None:
        self.home = (home if home is not None else Path.home()).resolve()

    def assess(
        self, candidate: UnitFileCandidate, _snapshot: UnitSnapshot | None = None
    ) -> PathAssessment:
        if candidate.resolution_state is not ResolutionState.RESOLVED:
            return PathAssessment(
                False,
                True,
                (f"Unit file resolution is {candidate.resolution_state.value}.",),
            )
        assert candidate.resolved_path is not None
        try:
            candidate.resolved_path.relative_to(self.home)
        except ValueError:
            return PathAssessment(False, True, ("Unit file target is outside the home directory.",))
        return PathAssessment(
            True,
            False,
            ("Unit file is within home; workload references are not assessed yet.",),
        )


class DiscoveryService:
    def __init__(
        self,
        scanner: UnitFileScanner,
        query: UnitQuery,
        registrations: RegistrationRepository,
        path_policy: FragmentPathPolicy | ServicePathPolicy | None = None,
    ) -> None:
        self._scanner = scanner
        self._query = query
        self._registrations = registrations
        self._path_policy = path_policy or ServicePathPolicy()
        self._last_discovered: frozenset[UnitId] = frozenset()

    async def scan(self) -> tuple[UnitRecord, ...]:
        candidates = tuple(self._scanner.scan())
        registered = self._registrations.load()
        queried = await asyncio.gather(
            *(self._query_candidate(candidate) for candidate in candidates)
        )
        records = [
            self._record(candidate, snapshot, registered)
            for candidate, snapshot in zip(candidates, queried, strict=True)
        ]
        discovered = frozenset(candidate.unit_id for candidate in candidates)
        self._last_discovered = discovered
        for missing_id in sorted(registered - discovered, key=lambda item: item.value):
            records.append(self._missing_record(missing_id))
        return tuple(sorted(records, key=lambda record: record.unit_id.value))

    async def register(self, unit_id: UnitId) -> tuple[UnitRecord, ...]:
        # Registration is a state-changing decision. Never trust a previous
        # scan here: the entry may have disappeared or changed in between.
        await self.scan()
        if unit_id not in self._last_discovered:
            raise ValueError(f"Cannot register an undiscovered unit: {unit_id.value}")
        self._registrations.save(self._registrations.load() | {unit_id})
        return await self.scan()

    async def unregister(self, unit_id: UnitId) -> tuple[UnitRecord, ...]:
        self._registrations.save(self._registrations.load() - {unit_id})
        return await self.scan()

    async def _query_candidate(self, candidate: UnitFileCandidate) -> UnitSnapshot:
        try:
            return await self._query.query(candidate.unit_id)
        except UnitQueryError as error:
            return UnitSnapshot(
                candidate.unit_id,
                candidate.unit_id.value,
                LoadState.ERROR,
                ActiveState.UNKNOWN,
                "unknown",
                "unknown",
                str(candidate.entry_path),
                diagnostic_details=str(error),
            )

    def _record(
        self,
        candidate: UnitFileCandidate,
        snapshot: UnitSnapshot,
        registered: frozenset[UnitId],
    ) -> UnitRecord:
        assessment = self._path_policy.assess(candidate, snapshot)
        if snapshot.load_state is not LoadState.LOADED or not assessment.fragment_allowed:
            access_mode = AccessMode.READ_ONLY
        elif not assessment.conclusive:
            access_mode = AccessMode.UNKNOWN
        else:
            access_mode = AccessMode.MANAGEABLE
        registration = (
            RegistrationState.REGISTERED
            if candidate.unit_id in registered
            else RegistrationState.DISCOVERED
        )
        capabilities = {Capability.STATUS, Capability.LOGS}
        if access_mode is AccessMode.MANAGEABLE and snapshot.load_state is LoadState.LOADED:
            capabilities.update(
                {
                    Capability.START,
                    Capability.STOP,
                    Capability.RESTART,
                    Capability.ENABLE,
                    Capability.DISABLE,
                }
            )
        return UnitRecord(
            snapshot.unit_id,
            snapshot.description,
            snapshot.load_state,
            snapshot.active_state,
            snapshot.sub_state,
            snapshot.unit_file_state,
            snapshot.fragment_path,
            access_mode,
            registration,
            frozenset(capabilities),
            assessment.reasons,
            snapshot.exec_commands,
            snapshot.working_directory,
            snapshot.environment_files,
            snapshot.diagnostic_details,
        )

    @staticmethod
    def _missing_record(unit_id: UnitId) -> UnitRecord:
        return UnitRecord(
            unit_id,
            unit_id.value,
            LoadState.NOT_FOUND,
            ActiveState.INACTIVE,
            "dead",
            "unknown",
            None,
            AccessMode.UNKNOWN,
            RegistrationState.MISSING,
            frozenset(),
            ("The registered unit is not currently present at the discovery origin.",),
        )
