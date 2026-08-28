from __future__ import annotations

import unittest

from user_service_manager.adapters.gio_systemd_commands import GioSystemdUnitCommands
from user_service_manager.domain.models import Capability, UnitId


class RecordingCommands(GioSystemdUnitCommands):
    def __init__(self) -> None:
        self.methods: list[str] = []

    def _call(self, _connection, method, _parameters, _reply_type):
        self.methods.append(method)
        return object()


class GioCommandTests(unittest.TestCase):
    def test_enable_and_disable_reload_manager_cache(self) -> None:
        for capability, expected in (
            (Capability.ENABLE, ["EnableUnitFiles", "Reload"]),
            (Capability.DISABLE, ["DisableUnitFiles", "Reload"]),
        ):
            with self.subTest(capability=capability):
                commands = RecordingCommands()
                commands._operate_with_connection(
                    object(), UnitId("example.service"), capability
                )
                self.assertEqual(commands.methods, expected)


if __name__ == "__main__":
    unittest.main()
