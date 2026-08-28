from __future__ import annotations

import asyncio
import unittest

from user_service_manager.application.command_service import CommandRejected, UnitCommandService
from user_service_manager.domain.models import (
    AccessMode,
    ActiveState,
    Capability,
    LoadState,
    RegistrationState,
    UnitId,
    UnitRecord,
)


UNIT_ID = UnitId("example.service")


def record(
    access: AccessMode = AccessMode.MANAGEABLE,
    registration: RegistrationState = RegistrationState.REGISTERED,
) -> UnitRecord:
    return UnitRecord(
        UNIT_ID,
        "Example",
        LoadState.LOADED,
        ActiveState.INACTIVE,
        "dead",
        "disabled",
        "/home/demo/.config/systemd/user/example.service",
        access,
        registration,
        frozenset(
            {
                Capability.START,
                Capability.STOP,
                Capability.RESTART,
                Capability.ENABLE,
                Capability.DISABLE,
            }
        ),
    )


class FakeDiscovery:
    def __init__(self, records: tuple[UnitRecord, ...]) -> None:
        self.records = records
        self.scans = 0

    async def scan(self) -> tuple[UnitRecord, ...]:
        self.scans += 1
        return self.records


class FakeCommands:
    def __init__(self) -> None:
        self.operations: list[tuple[UnitId, Capability]] = []
        self.reloads = 0
        self.entered: asyncio.Event | None = None
        self.release: asyncio.Event | None = None

    async def operate(self, unit_id: UnitId, capability: Capability) -> None:
        self.operations.append((unit_id, capability))
        if self.entered is not None and self.release is not None:
            self.entered.set()
            await self.release.wait()

    async def reload(self) -> None:
        self.reloads += 1


class CommandServiceTests(unittest.TestCase):
    def test_operation_rechecks_then_refreshes(self) -> None:
        discovery = FakeDiscovery((record(),))
        commands = FakeCommands()
        service = UnitCommandService(discovery, commands)

        result = asyncio.run(service.operate(UNIT_ID, Capability.START))

        self.assertEqual(commands.operations, [(UNIT_ID, Capability.START)])
        self.assertEqual(discovery.scans, 2)
        self.assertEqual(result, (record(),))

    def test_unregistered_or_read_only_unit_is_rejected(self) -> None:
        for unsafe in (
            record(registration=RegistrationState.DISCOVERED),
            record(access=AccessMode.READ_ONLY),
        ):
            with self.subTest(unsafe=unsafe):
                commands = FakeCommands()
                service = UnitCommandService(FakeDiscovery((unsafe,)), commands)
                with self.assertRaises(CommandRejected):
                    asyncio.run(service.operate(UNIT_ID, Capability.START))
                self.assertEqual(commands.operations, [])

    def test_non_change_capability_is_rejected(self) -> None:
        service = UnitCommandService(FakeDiscovery((record(),)), FakeCommands())
        with self.assertRaises(CommandRejected):
            asyncio.run(service.operate(UNIT_ID, Capability.STATUS))

    def test_parallel_operation_for_same_unit_is_rejected(self) -> None:
        async def scenario() -> None:
            commands = FakeCommands()
            commands.entered = asyncio.Event()
            commands.release = asyncio.Event()
            service = UnitCommandService(FakeDiscovery((record(),)), commands)
            first = asyncio.create_task(service.operate(UNIT_ID, Capability.START))
            await commands.entered.wait()
            with self.assertRaises(CommandRejected):
                await service.operate(UNIT_ID, Capability.STOP)
            commands.release.set()
            await first

        asyncio.run(scenario())

    def test_reload_refreshes_catalog(self) -> None:
        discovery = FakeDiscovery((record(),))
        commands = FakeCommands()
        result = asyncio.run(UnitCommandService(discovery, commands).reload())
        self.assertEqual(commands.reloads, 1)
        self.assertEqual(discovery.scans, 1)
        self.assertEqual(result, (record(),))


if __name__ == "__main__":
    unittest.main()
