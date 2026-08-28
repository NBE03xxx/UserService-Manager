"""Read-only systemd user-manager query adapter using GIO D-Bus."""

from __future__ import annotations

import asyncio

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from user_service_manager.domain.discovery import UnitSnapshot
from user_service_manager.domain.models import ActiveState, LoadState, UnitId
from user_service_manager.ports.discovery import UnitQueryError


BUS_NAME = "org.freedesktop.systemd1"
MANAGER_PATH = "/org/freedesktop/systemd1"
MANAGER_IFACE = "org.freedesktop.systemd1.Manager"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
UNIT_IFACE = "org.freedesktop.systemd1.Unit"
SERVICE_IFACE = "org.freedesktop.systemd1.Service"


def _enum_or_unknown(enum_type: type[ActiveState] | type[LoadState], value: str):
    try:
        return enum_type(value)
    except ValueError:
        return enum_type.UNKNOWN


def _exec_commands(value: object) -> tuple[tuple[str, ...], ...]:
    commands: list[tuple[str, ...]] = []
    if not isinstance(value, (list, tuple)):
        return ()
    for entry in value:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        argv = entry[1]
        if isinstance(argv, (list, tuple)):
            commands.append(tuple(str(argument) for argument in argv))
    return tuple(commands)


def _environment_files(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(
        str(entry[0])
        for entry in value
        if isinstance(entry, (list, tuple)) and entry
    )


class GioSystemdUnitQuery:
    async def query(self, unit_id: UnitId) -> UnitSnapshot:
        return await asyncio.to_thread(self._query_sync, unit_id)

    @staticmethod
    def _query_sync(unit_id: UnitId) -> UnitSnapshot:
        try:
            connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            unit_path = connection.call_sync(
                BUS_NAME,
                MANAGER_PATH,
                MANAGER_IFACE,
                "LoadUnit",
                GLib.Variant("(s)", (unit_id.value,)),
                GLib.VariantType.new("(o)"),
                Gio.DBusCallFlags.NONE,
                5_000,
                None,
            ).unpack()[0]
            properties = connection.call_sync(
                BUS_NAME,
                unit_path,
                PROPERTIES_IFACE,
                "GetAll",
                GLib.Variant("(s)", (UNIT_IFACE,)),
                GLib.VariantType.new("(a{sv})"),
                Gio.DBusCallFlags.NONE,
                5_000,
                None,
            ).unpack()[0]
            service_properties = connection.call_sync(
                BUS_NAME,
                unit_path,
                PROPERTIES_IFACE,
                "GetAll",
                GLib.Variant("(s)", (SERVICE_IFACE,)),
                GLib.VariantType.new("(a{sv})"),
                Gio.DBusCallFlags.NONE,
                5_000,
                None,
            ).unpack()[0]
        except GLib.Error as error:
            raise UnitQueryError(unit_id, error.message) from error

        return UnitSnapshot(
            unit_id=unit_id,
            description=str(properties.get("Description") or unit_id.value),
            load_state=_enum_or_unknown(LoadState, str(properties.get("LoadState") or "unknown")),
            active_state=_enum_or_unknown(
                ActiveState, str(properties.get("ActiveState") or "unknown")
            ),
            sub_state=str(properties.get("SubState") or "unknown"),
            unit_file_state=str(properties.get("UnitFileState") or "unknown"),
            fragment_path=str(properties.get("FragmentPath") or "") or None,
            exec_commands=_exec_commands(service_properties.get("ExecStart")),
            working_directory=(
                str(service_properties.get("WorkingDirectory") or "") or None
            ),
            environment_files=_environment_files(
                service_properties.get("EnvironmentFiles")
            ),
        )
