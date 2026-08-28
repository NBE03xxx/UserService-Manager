from __future__ import annotations

import unittest

from user_service_manager.domain.models import (
    AccessMode,
    ActiveState,
    LoadState,
    RegistrationState,
    UnitId,
    UnitRecord,
)
from user_service_manager.presentation.application import filter_units, managed_unit_count


def unit(
    name: str,
    description: str,
    active: ActiveState,
    access: AccessMode,
    registration: RegistrationState = RegistrationState.DISCOVERED,
) -> UnitRecord:
    return UnitRecord(
        UnitId(name), description, LoadState.LOADED, active, "running", "enabled",
        f"/home/demo/{name}", access, registration,
    )


class UiFilterTests(unittest.TestCase):
    def test_managed_count_includes_registered_and_missing_units(self) -> None:
        units = (
            unit(
                "registered.service", "Registered", ActiveState.ACTIVE,
                AccessMode.MANAGEABLE, RegistrationState.REGISTERED,
            ),
            unit(
                "missing.service", "Missing", ActiveState.INACTIVE,
                AccessMode.UNKNOWN, RegistrationState.MISSING,
            ),
            unit(
                "discovered.service", "Discovered", ActiveState.INACTIVE,
                AccessMode.MANAGEABLE, RegistrationState.DISCOVERED,
            ),
        )
        self.assertEqual(managed_unit_count(units), 2)

    def setUp(self) -> None:
        self.units = (
            unit("coffee.service", "Coffee Notes", ActiveState.ACTIVE, AccessMode.MANAGEABLE),
            unit("backup.service", "Quiet Backup", ActiveState.INACTIVE, AccessMode.READ_ONLY),
        )

    def test_search_matches_id_and_description_case_insensitively(self) -> None:
        self.assertEqual(filter_units(self.units, "COFFEE", "all"), (self.units[0],))
        self.assertEqual(filter_units(self.units, "backup", "all"), (self.units[1],))

    def test_state_and_access_filters(self) -> None:
        self.assertEqual(filter_units(self.units, "", "running"), (self.units[0],))
        self.assertEqual(filter_units(self.units, "", "stopped"), (self.units[1],))
        self.assertEqual(filter_units(self.units, "", "read-only"), (self.units[1],))


if __name__ == "__main__":
    unittest.main()
