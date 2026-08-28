"""Systemd user-manager change adapter using the session D-Bus."""

from __future__ import annotations

import asyncio

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from user_service_manager.adapters.gio_systemd_query import (
    BUS_NAME,
    MANAGER_IFACE,
    MANAGER_PATH,
)
from user_service_manager.domain.models import Capability, UnitId
from user_service_manager.ports.commands import UnitCommandError


class GioSystemdUnitCommands:
    JOB_METHODS = {
        Capability.START: "StartUnit",
        Capability.STOP: "StopUnit",
        Capability.RESTART: "RestartUnit",
    }

    async def operate(self, unit_id: UnitId, capability: Capability) -> None:
        await asyncio.to_thread(self._operate_sync, unit_id, capability)

    async def reload(self) -> None:
        await asyncio.to_thread(self._reload_sync)

    def _operate_sync(self, unit_id: UnitId, capability: Capability) -> None:
        try:
            connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self._operate_with_connection(connection, unit_id, capability)
        except GLib.Error as error:
            raise UnitCommandError(error.message) from error

    def _operate_with_connection(
        self,
        connection: Gio.DBusConnection,
        unit_id: UnitId,
        capability: Capability,
    ) -> None:
        if capability in self.JOB_METHODS:
            self._run_job(connection, self.JOB_METHODS[capability], unit_id)
        elif capability is Capability.ENABLE:
            self._call(
                connection,
                "EnableUnitFiles",
                GLib.Variant("(asbb)", ([unit_id.value], False, False)),
                "(ba(sss))",
            )
            # EnableUnitFiles changes links on disk. Reload before the
            # application refreshes UnitFileState from the manager cache.
            self._call(connection, "Reload", None, "()")
        elif capability is Capability.DISABLE:
            self._call(
                connection,
                "DisableUnitFiles",
                GLib.Variant("(asb)", ([unit_id.value], False)),
                "(a(sss))",
            )
            self._call(connection, "Reload", None, "()")
        else:
            raise UnitCommandError(f"Unsupported operation: {capability.value}")

    def _reload_sync(self) -> None:
        try:
            connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self._call(connection, "Reload", None, "()")
        except GLib.Error as error:
            raise UnitCommandError(error.message) from error

    def _run_job(
        self, connection: Gio.DBusConnection, method: str, unit_id: UnitId
    ) -> None:
        loop = GLib.MainLoop()
        state: dict[str, object] = {"path": None, "result": None, "timed_out": False}

        def on_removed(
            _connection: Gio.DBusConnection,
            _sender: str,
            _path: str,
            _interface: str,
            _signal: str,
            parameters: GLib.Variant,
            _data: object,
        ) -> None:
            _job_id, job_path, unit_name, result = parameters.unpack()
            if job_path == state["path"] and unit_name == unit_id.value:
                state["result"] = result
                loop.quit()

        def on_timeout() -> bool:
            state["timed_out"] = True
            loop.quit()
            return GLib.SOURCE_REMOVE

        subscription = connection.signal_subscribe(
            BUS_NAME,
            MANAGER_IFACE,
            "JobRemoved",
            MANAGER_PATH,
            None,
            Gio.DBusSignalFlags.NONE,
            on_removed,
            None,
        )
        try:
            state["path"] = self._call(
                connection,
                method,
                GLib.Variant("(ss)", (unit_id.value, "replace")),
                "(o)",
            ).unpack()[0]
            timeout_source = GLib.timeout_add_seconds(15, on_timeout)
            loop.run()
            if not state["timed_out"]:
                GLib.source_remove(timeout_source)
        finally:
            connection.signal_unsubscribe(subscription)

        if state["timed_out"]:
            raise UnitCommandError(f"Timed out waiting for {method}")
        if state["result"] != "done":
            raise UnitCommandError(f"{method} failed: {state['result']}")

    @staticmethod
    def _call(
        connection: Gio.DBusConnection,
        method: str,
        parameters: GLib.Variant | None,
        reply_type: str,
    ) -> GLib.Variant:
        return connection.call_sync(
            BUS_NAME,
            MANAGER_PATH,
            MANAGER_IFACE,
            method,
            parameters,
            GLib.VariantType.new(reply_type),
            Gio.DBusCallFlags.NONE,
            15_000,
            None,
        )
