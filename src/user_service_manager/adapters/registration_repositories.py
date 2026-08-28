"""Registration repository implementations."""

from __future__ import annotations

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402

from user_service_manager.domain.models import UnitId


class MemoryRegistrationRepository:
    def __init__(self, unit_ids: frozenset[UnitId] = frozenset()) -> None:
        self._unit_ids = unit_ids

    def load(self) -> frozenset[UnitId]:
        return self._unit_ids

    def save(self, unit_ids: frozenset[UnitId]) -> None:
        self._unit_ids = unit_ids


class GSettingsRegistrationRepository:
    KEY = "registered-units"

    def __init__(self, settings: Gio.Settings) -> None:
        self._settings = settings

    def load(self) -> frozenset[UnitId]:
        valid: set[UnitId] = set()
        for value in self._settings.get_strv(self.KEY):
            try:
                valid.add(UnitId(value))
            except ValueError:
                continue
        return frozenset(valid)

    def save(self, unit_ids: frozenset[UnitId]) -> None:
        values = sorted(unit_id.value for unit_id in unit_ids)
        if not self._settings.set_strv(self.KEY, values):
            raise OSError("GSettings refused to save registered unit IDs")
