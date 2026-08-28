from __future__ import annotations

import asyncio
import unittest

from user_service_manager.adapters.mock_backend import MockServiceBackend
from user_service_manager.application.catalog import ServiceCatalog
from user_service_manager.domain.models import ActiveState, Capability, UnitId


class CatalogTests(unittest.TestCase):
    def test_mock_units_are_sorted(self) -> None:
        units = asyncio.run(ServiceCatalog(MockServiceBackend()).load())
        self.assertEqual(
            [unit.unit_id.value for unit in units],
            sorted(unit.unit_id.value for unit in units),
        )

    def test_start_and_stop_refresh_state(self) -> None:
        catalog = ServiceCatalog(MockServiceBackend())
        unit_id = UnitId("quiet-backup.service")
        started = asyncio.run(catalog.operate(unit_id, Capability.START))
        self.assertEqual(started.active_state, ActiveState.ACTIVE)
        stopped = asyncio.run(catalog.operate(unit_id, Capability.STOP))
        self.assertEqual(stopped.active_state, ActiveState.INACTIVE)

    def test_read_only_unit_rejects_change(self) -> None:
        catalog = ServiceCatalog(MockServiceBackend())
        with self.assertRaises(PermissionError):
            asyncio.run(catalog.operate(UnitId("shared-runtime.service"), Capability.START))


if __name__ == "__main__":
    unittest.main()
