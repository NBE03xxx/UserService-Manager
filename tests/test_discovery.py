from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile
import unittest

from user_service_manager.adapters.filesystem_scanner import UserUnitFileScanner
from user_service_manager.adapters.registration_repositories import MemoryRegistrationRepository
from user_service_manager.application.discovery_service import DiscoveryService, FragmentPathPolicy
from user_service_manager.domain.discovery import ResolutionState, UnitSnapshot
from user_service_manager.domain.models import (
    AccessMode,
    ActiveState,
    LoadState,
    RegistrationState,
    UnitId,
)
from user_service_manager.ports.discovery import UnitQueryError


class FakeQuery:
    def __init__(self, failures: frozenset[UnitId] = frozenset()) -> None:
        self.failures = failures

    async def query(self, unit_id: UnitId) -> UnitSnapshot:
        if unit_id in self.failures:
            raise UnitQueryError(unit_id, "intentional query failure")
        return UnitSnapshot(
            unit_id,
            f"Description for {unit_id.value}",
            LoadState.LOADED,
            ActiveState.INACTIVE,
            "dead",
            "disabled",
            f"/query/{unit_id.value}",
        )


class DiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.origin = self.home / ".config/systemd/user"
        self.origin.mkdir(parents=True)
        self.outside = self.root / "outside"
        self.outside.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_unit(self, name: str, directory: Path | None = None) -> Path:
        target = (directory or self.origin) / name
        target.write_text("[Service]\nExecStart=/usr/bin/true\n", encoding="utf-8")
        return target

    def service(
        self,
        query: FakeQuery | None = None,
        registrations: MemoryRegistrationRepository | None = None,
    ) -> DiscoveryService:
        return DiscoveryService(
            UserUnitFileScanner(self.origin),
            query or FakeQuery(),
            registrations or MemoryRegistrationRepository(),
            FragmentPathPolicy(self.home),
        )

    def test_scanner_only_uses_origin_and_sorts_candidates(self) -> None:
        self.write_unit("z-last.service")
        self.write_unit("a-first.service")
        self.write_unit("outside.service", self.outside)
        (self.origin / "ignored.timer").write_text("", encoding="utf-8")
        (self.origin / ".hidden.service").write_text("", encoding="utf-8")

        candidates = UserUnitFileScanner(self.origin).scan()
        self.assertEqual(
            [candidate.unit_id.value for candidate in candidates],
            ["a-first.service", "z-last.service"],
        )

    def test_scanner_keeps_broken_symlink_as_candidate(self) -> None:
        (self.origin / "broken.service").symlink_to(self.home / "missing.service")
        candidate = UserUnitFileScanner(self.origin).scan()[0]
        self.assertEqual(candidate.resolution_state, ResolutionState.MISSING)
        self.assertIsNone(candidate.resolved_path)

    def test_scanner_keeps_circular_symlink_as_unsafe_candidate(self) -> None:
        first = self.origin / "circle.service"
        second = self.origin / "circle-target.service"
        first.symlink_to(second)
        second.symlink_to(first)

        candidates = UserUnitFileScanner(self.origin).scan()

        by_name = {candidate.unit_id.value: candidate for candidate in candidates}
        self.assertEqual(
            by_name["circle.service"].resolution_state,
            ResolutionState.CIRCULAR,
        )

    def test_home_symlink_is_discovered_but_not_yet_manageable(self) -> None:
        target = self.write_unit("target.service", self.home)
        (self.origin / "alias.service").symlink_to(target)
        records = asyncio.run(self.service().scan())
        record = next(item for item in records if item.unit_id == UnitId("alias.service"))
        self.assertEqual(record.access_mode, AccessMode.UNKNOWN)
        self.assertEqual(record.registration_state, RegistrationState.DISCOVERED)

    def test_outside_symlink_is_read_only(self) -> None:
        target = self.write_unit("target.service", self.outside)
        (self.origin / "alias.service").symlink_to(target)
        record = asyncio.run(self.service().scan())[0]
        self.assertEqual(record.access_mode, AccessMode.READ_ONLY)

    def test_query_failure_becomes_visible_read_only_error(self) -> None:
        self.write_unit("bad.service")
        record = asyncio.run(
            self.service(FakeQuery(frozenset({UnitId("bad.service")}))).scan()
        )[0]
        self.assertEqual(record.load_state, LoadState.ERROR)
        self.assertEqual(record.access_mode, AccessMode.READ_ONLY)
        self.assertEqual(record.diagnostic_details, "intentional query failure")

    def test_registration_missing_reappearance_and_unregister(self) -> None:
        target = self.write_unit("remembered.service")
        repository = MemoryRegistrationRepository()
        service = self.service(registrations=repository)

        first = asyncio.run(service.scan())[0]
        self.assertEqual(first.registration_state, RegistrationState.DISCOVERED)

        registered = asyncio.run(service.register(UnitId("remembered.service")))[0]
        self.assertEqual(registered.registration_state, RegistrationState.REGISTERED)

        target.unlink()
        missing = asyncio.run(service.scan())[0]
        self.assertEqual(missing.registration_state, RegistrationState.MISSING)
        self.assertEqual(missing.load_state, LoadState.NOT_FOUND)

        target = self.write_unit("remembered.service")
        restored = asyncio.run(service.scan())[0]
        self.assertEqual(restored.registration_state, RegistrationState.REGISTERED)

        target.unlink()
        asyncio.run(service.scan())
        empty = asyncio.run(service.unregister(UnitId("remembered.service")))
        self.assertEqual(empty, ())
        self.assertEqual(repository.load(), frozenset())

    def test_cannot_register_undiscovered_unit(self) -> None:
        with self.assertRaises(ValueError):
            asyncio.run(self.service().register(UnitId("absent.service")))

    def test_register_rechecks_a_candidate_that_disappeared(self) -> None:
        target = self.write_unit("vanished.service")
        service = self.service()
        asyncio.run(service.scan())
        target.unlink()

        with self.assertRaises(ValueError):
            asyncio.run(service.register(UnitId("vanished.service")))


if __name__ == "__main__":
    unittest.main()
