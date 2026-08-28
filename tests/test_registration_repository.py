from __future__ import annotations

import unittest

from user_service_manager.adapters.registration_repositories import (
    GSettingsRegistrationRepository,
    MemoryRegistrationRepository,
)
from user_service_manager.domain.models import UnitId


class RegistrationRepositoryTests(unittest.TestCase):
    def test_memory_repository_replaces_snapshot(self) -> None:
        repository = MemoryRegistrationRepository()
        expected = frozenset({UnitId("a.service"), UnitId("b.service")})
        repository.save(expected)
        self.assertEqual(repository.load(), expected)

    def test_gsettings_repository_filters_invalid_values_and_sorts_saves(self) -> None:
        settings = FakeSettings(["b.service", "../escape.service", "a.service"])
        repository = GSettingsRegistrationRepository(settings)

        self.assertEqual(
            repository.load(),
            frozenset({UnitId("a.service"), UnitId("b.service")}),
        )

        repository.save(frozenset({UnitId("z.service"), UnitId("c.service")}))
        self.assertEqual(settings.values, ["c.service", "z.service"])


class FakeSettings:
    def __init__(self, values: list[str]) -> None:
        self.values = values

    def get_strv(self, key: str) -> list[str]:
        self.assert_key(key)
        return self.values

    def set_strv(self, key: str, values: list[str]) -> bool:
        self.assert_key(key)
        self.values = values
        return True

    @staticmethod
    def assert_key(key: str) -> None:
        if key != "registered-units":
            raise AssertionError(f"Unexpected settings key: {key}")


if __name__ == "__main__":
    unittest.main()
