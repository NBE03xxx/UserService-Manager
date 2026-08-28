from __future__ import annotations

import unittest

from user_service_manager.domain.models import (
    AccessMode,
    ActiveState,
    Capability,
    LoadState,
    RegistrationState,
    UnitId,
    UnitRecord,
)


class DomainTests(unittest.TestCase):
    def test_unit_id_accepts_service_name(self) -> None:
        self.assertEqual(UnitId("example@demo.service").value, "example@demo.service")

    def test_unit_id_rejects_non_service_and_path(self) -> None:
        for value in (
            "example.timer",
            "../example.service",
            "/tmp/example.service",
            "bad\\name.service",
            "",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                UnitId(value)

    def test_unit_id_accepts_systemd_hex_escape(self) -> None:
        self.assertEqual(UnitId(r"coffee\x20notes.service").value, r"coffee\x20notes.service")

    def test_change_requires_loaded_registered_manageable_unit(self) -> None:
        unit = UnitRecord(
            UnitId("example.service"),
            "Example",
            LoadState.LOADED,
            ActiveState.INACTIVE,
            "dead",
            "disabled",
            "/home/demo/.config/systemd/user/example.service",
            AccessMode.MANAGEABLE,
            RegistrationState.REGISTERED,
            frozenset({Capability.START}),
        )
        self.assertTrue(unit.supports(Capability.START))
        self.assertFalse(unit.supports(Capability.STOP))

    def test_read_only_unit_can_support_status_and_logs(self) -> None:
        unit = UnitRecord(
            UnitId("readonly.service"),
            "Read only",
            LoadState.LOADED,
            ActiveState.INACTIVE,
            "dead",
            "disabled",
            "/outside/readonly.service",
            AccessMode.READ_ONLY,
            RegistrationState.DISCOVERED,
            frozenset({Capability.STATUS, Capability.LOGS}),
        )
        self.assertTrue(unit.supports(Capability.STATUS))
        self.assertTrue(unit.supports(Capability.LOGS))
        self.assertFalse(unit.supports(Capability.START))


if __name__ == "__main__":
    unittest.main()
