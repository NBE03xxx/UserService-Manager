from __future__ import annotations

import unittest

from user_service_manager.infrastructure.preferences import AppearancePreference


class PreferenceTests(unittest.TestCase):
    def test_known_appearance_values(self) -> None:
        for value in ("system", "light", "dark"):
            self.assertEqual(AppearancePreference.parse(value).value, value)

    def test_unknown_appearance_falls_back_to_system(self) -> None:
        self.assertEqual(AppearancePreference.parse("unexpected"), AppearancePreference.SYSTEM)


if __name__ == "__main__":
    unittest.main()
