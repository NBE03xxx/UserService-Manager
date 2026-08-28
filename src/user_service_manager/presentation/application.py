"""GTK/libadwaita presentation with a read-only systemd discovery mode."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
import gettext
import os
from pathlib import Path
from threading import Thread

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from user_service_manager.adapters.filesystem_scanner import UserUnitFileScanner
from user_service_manager.adapters.gio_systemd_query import GioSystemdUnitQuery
from user_service_manager.adapters.gio_systemd_commands import GioSystemdUnitCommands
from user_service_manager.adapters.systemd_journal import SystemdJournalReader
from user_service_manager.adapters.mock_backend import MockServiceBackend
from user_service_manager.adapters.registration_repositories import (
    GSettingsRegistrationRepository,
    MemoryRegistrationRepository,
)
from user_service_manager.application.catalog import ServiceCatalog
from user_service_manager.application.discovery_service import DiscoveryService
from user_service_manager.application.command_service import UnitCommandService
from user_service_manager.application.journal_service import JournalService
from user_service_manager.domain.journal import JournalEntry, JournalPage
from user_service_manager.domain.models import (
    AccessMode,
    ActiveState,
    Capability,
    RegistrationState,
    UnitId,
    UnitRecord,
)
from user_service_manager.infrastructure.preferences import AppearancePreference


_ = gettext.gettext
APP_ID = "io.github.NBE03xxx.UserServiceManager"
SETTINGS_ID = APP_ID


def filter_units(
    units: tuple[UnitRecord, ...], query: str, mode: str
) -> tuple[UnitRecord, ...]:
    needle = query.casefold().strip()
    filtered: list[UnitRecord] = []
    for unit in units:
        if needle and needle not in unit.unit_id.value.casefold() and needle not in unit.description.casefold():
            continue
        if mode == "running" and unit.active_state is not ActiveState.ACTIVE:
            continue
        if mode == "stopped" and unit.active_state is ActiveState.ACTIVE:
            continue
        if mode == "read-only" and unit.access_mode is AccessMode.MANAGEABLE:
            continue
        filtered.append(unit)
    return tuple(filtered)


def managed_unit_count(units: tuple[UnitRecord, ...]) -> int:
    return sum(
        unit.registration_state
        in {RegistrationState.REGISTERED, RegistrationState.MISSING}
        for unit in units
    )


class LogWindow(Adw.Window):
    def __init__(
        self,
        parent: "MainWindow",
        unit_id: UnitId,
        service: JournalService,
    ) -> None:
        super().__init__(transient_for=parent, title=_("Service logs"))
        self.unit_id = unit_id
        self.service = service
        self.entries: tuple[JournalEntry, ...] = ()
        self.older_cursor: str | None = None
        self.has_more = False
        self._generation = 0
        self._busy = False
        self._closed = False
        self._last_updated: datetime | None = None
        self._diagnostic: str | None = None
        self.set_default_size(820, 620)
        self.connect("close-request", self._on_close)
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(
            Adw.WindowTitle(title=_("Service logs"), subtitle=unit_id.value)
        )
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text=_("Refresh logs"))
        refresh.connect("clicked", lambda _button: self.refresh())
        header.pack_start(refresh)
        copy = Gtk.Button(icon_name="edit-copy-symbolic", tooltip_text=_("Copy visible logs"))
        copy.connect("clicked", self._copy_visible)
        header.pack_end(copy)
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        self.search = Gtk.SearchEntry(placeholder_text=_("Search loaded logs"))
        self.search.connect("search-changed", lambda _entry: self._render())
        content.append(self.search)
        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("dim-label")
        content.append(self.status)
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list.add_css_class("boxed-list")
        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.set_child(self.list)
        content.append(scroller)
        self.more = Gtk.Button(label=_("Load older entries"), halign=Gtk.Align.CENTER)
        self.more.connect("clicked", lambda _button: self.load_more())
        content.append(self.more)
        toolbar.set_content(content)
        self.set_content(toolbar)
        self.refresh()

    def refresh(self) -> None:
        if self._busy:
            return
        self._generation += 1
        self.entries = ()
        self.older_cursor = None
        self._read(None, append=False, generation=self._generation)

    def load_more(self) -> None:
        if self._busy or not self.has_more or not self.older_cursor:
            return
        self._read(self.older_cursor, append=True, generation=self._generation)

    def _read(
        self, before_cursor: str | None, append: bool, generation: int
    ) -> None:
        self._busy = True
        self.status.set_text(_("Loading logs…"))
        self.more.set_sensitive(False)

        def worker() -> None:
            try:
                page = asyncio.run(
                    self.service.read(self.unit_id, before_cursor=before_cursor)
                )
            except Exception as error:
                GLib.idle_add(self._failed, str(error), generation)
            else:
                GLib.idle_add(self._loaded, page, append, generation)

        Thread(target=worker, daemon=True).start()

    def _loaded(self, page: JournalPage, append: bool, generation: int) -> bool:
        if self._closed or generation != self._generation:
            return GLib.SOURCE_REMOVE
        self._busy = False
        self._diagnostic = None
        self.entries = self.entries + page.entries if append else page.entries
        self._last_updated = datetime.now().astimezone()
        self.older_cursor = page.older_cursor
        self.has_more = page.has_more
        self.more.set_sensitive(page.has_more)
        self.more.set_visible(page.has_more)
        self._render()
        return GLib.SOURCE_REMOVE

    def _failed(self, message: str, generation: int) -> bool:
        if self._closed or generation != self._generation:
            return GLib.SOURCE_REMOVE
        self._busy = False
        self._diagnostic = message
        self.status.set_text(
            f'{_("Logs could not be loaded")} · {_("Use Copy to copy diagnostic details")}'
        )
        self.more.set_sensitive(False)
        return GLib.SOURCE_REMOVE

    def _render(self) -> None:
        child = self.list.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.list.remove(child)
            child = following
        needle = self.search.get_text().casefold().strip()
        visible = tuple(
            entry for entry in self.entries
            if not needle or needle in entry.message.casefold()
        )
        count_text = (
            _("No log entries")
            if not visible
            else f'{len(visible)} {_("entries shown")}'
        )
        if self._last_updated is not None:
            updated = _("Updated at {time}").format(
                time=self._last_updated.strftime("%H:%M:%S")
            )
            count_text = f"{count_text} · {updated}"
        self.status.set_text(count_text)
        for entry in visible:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(10)
            box.set_margin_end(10)
            metadata = Gtk.Label(
                label=f"{entry.timestamp.astimezone():%Y-%m-%d %H:%M:%S}  ·  priority {entry.priority}",
                xalign=0,
            )
            metadata.add_css_class("dim-label")
            message = Gtk.Label(label=entry.message, xalign=0, wrap=True, selectable=True)
            box.append(metadata)
            box.append(message)
            row.set_child(box)
            self.list.append(row)

    def _copy_visible(self, _button: Gtk.Button) -> None:
        if self._diagnostic is not None:
            self.get_clipboard().set(self._diagnostic)
            self.status.set_text(_("Diagnostic details copied"))
            return
        needle = self.search.get_text().casefold().strip()
        lines = [
            f"{entry.timestamp.astimezone().isoformat()} [{entry.priority}] {entry.message}"
            for entry in self.entries
            if not needle or needle in entry.message.casefold()
        ]
        clipboard = self.get_clipboard()
        clipboard.set("\n".join(lines))
        self.status.set_text(_("Visible logs copied"))

    def _on_close(self, *_args: object) -> bool:
        self._closed = True
        self._generation += 1
        return False

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: "UserServiceManagerApplication") -> None:
        super().__init__(application=app, title=_("User Service Manager"))
        self.app = app
        self.set_default_size(940, 700)
        self.add_css_class("coffee-window")
        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self._sync_appearance_class)
        self._sync_appearance_class()

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.add_css_class("coffee-header")
        self.window_title = Adw.WindowTitle(
            title=_("Service list"),
            subtitle=_("Managed: {count}").format(count=managed_unit_count(app.units)),
        )
        header.set_title_widget(self.window_title)
        toolbar.add_top_bar(header)

        menu = Gio.Menu()
        menu.append(_("Appearance: system"), "app.appearance::system")
        menu.append(_("Appearance: light"), "app.appearance::light")
        menu.append(_("Appearance: dark"), "app.appearance::dark")
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu))
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text=_("Rescan"))
        refresh.connect("clicked", lambda _button: self.app.reload_units())
        header.pack_start(refresh)
        if app.commands is not None:
            reload_manager = Gtk.Button(
                icon_name="emblem-synchronizing-symbolic",
                tooltip_text=_("Reload user manager"),
            )
            reload_manager.connect("clicked", self._confirm_reload)
            header.pack_start(reload_manager)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        outer.set_margin_top(24)
        outer.set_margin_bottom(24)
        outer.set_margin_start(24)
        outer.set_margin_end(24)
        outer.add_css_class("coffee-canvas")
        hero_path = Path(__file__).with_name("assets") / "cafe-coffee-line-v4.png"
        intro = Adw.StatusPage(
            paintable=Gdk.Texture.new_from_filename(str(hero_path)),
            title=_("User Service Manager"),
            description=_("— Take your time —"),
        )
        intro.add_css_class("compact")
        intro.add_css_class("coffee-hero")
        outer.append(intro)

        filters = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.search = Gtk.SearchEntry(placeholder_text=_("Search services"), hexpand=True)
        self.search.connect("search-changed", self._on_filter_changed)
        filters.append(self.search)
        self.filter_modes = ("all", "running", "stopped", "read-only")
        self.filter = Gtk.DropDown.new_from_strings(
            [_("All"), _("Running"), _("Stopped"), _("Read only")]
        )
        self.filter.set_tooltip_text(_("Filter services"))
        self.filter.connect("notify::selected", self._on_filter_changed)
        filters.append(self.filter)
        outer.append(filters)

        self.group = Adw.PreferencesGroup(title=_("User services"))
        self.group.add_css_class("coffee-service-list")
        self._rows: list[Gtk.Widget] = []
        outer.append(self.group)
        main_scroller = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        main_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_scroller.set_child(outer)
        toolbar.set_content(main_scroller)
        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(toolbar)
        self.set_content(self.toasts)

    def show_loading(self) -> None:
        self._clear_group()
        row = Adw.ActionRow(title=_("Checking your services…"))
        row.add_prefix(Gtk.Spinner(spinning=True))
        self._add_row(row)

    def show_error(self, message: str) -> None:
        self._clear_group()
        row = Adw.ActionRow(
            title=_("Services could not be loaded"),
            subtitle=_("Try again, or copy the diagnostic details."),
        )
        row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
        retry = Gtk.Button(label=_("Try again"), valign=Gtk.Align.CENTER)
        retry.connect("clicked", lambda _button: self.app.reload_units())
        row.add_suffix(retry)
        copy = Gtk.Button(
            icon_name="edit-copy-symbolic",
            tooltip_text=_("Copy diagnostic details"),
            valign=Gtk.Align.CENTER,
        )
        copy.connect("clicked", lambda _button: self._copy_diagnostic(message))
        row.add_suffix(copy)
        self._add_row(row)

    def show_operation_error(self, diagnostic: str) -> None:
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_("Operation failed"),
            body=_("The requested change could not be completed."),
        )
        dialog.add_response("close", _("Close"))
        dialog.add_response("copy", _("Copy details"))
        dialog.set_default_response("close")
        dialog.set_close_response("close")
        dialog.connect(
            "response",
            lambda _dialog, response: self._copy_diagnostic(diagnostic)
            if response == "copy" else None,
        )
        dialog.present()

    def _copy_diagnostic(self, diagnostic: str) -> None:
        self.get_clipboard().set(diagnostic)
        self.notify(_("Diagnostic details copied"))

    def show_units(self, units: tuple[UnitRecord, ...]) -> None:
        self.window_title.set_subtitle(
            _("Managed: {count}").format(count=managed_unit_count(self.app.units))
        )
        self._clear_group()
        if not units:
            self._add_row(Adw.ActionRow(title=_("No user services were found")))
            return
        for unit in units:
            self._add_row(self._unit_row(unit))

    def _on_filter_changed(self, *_args: object) -> None:
        selected = min(self.filter.get_selected(), len(self.filter_modes) - 1)
        units = filter_units(
            self.app.units,
            self.search.get_text(),
            self.filter_modes[selected],
        )
        self.show_units(units)

    def _unit_row(self, unit: UnitRecord) -> Adw.ExpanderRow:
        subtitle = f"{unit.unit_id.value} · {unit.active_state.value} · {unit.unit_file_state}"
        row = Adw.ExpanderRow(title=unit.description, subtitle=subtitle)
        row.add_css_class("coffee-service-row")
        row.add_prefix(Gtk.Image.new_from_icon_name(
            "media-playback-start-symbolic"
            if unit.active_state is ActiveState.ACTIVE
            else "media-playback-stop-symbolic"
        ))
        badge = Gtk.Label(label={
            AccessMode.MANAGEABLE: _("Manageable"),
            AccessMode.READ_ONLY: _("Read only"),
            AccessMode.UNKNOWN: _("Review needed"),
        }[unit.access_mode])
        badge.add_css_class("readonly-badge")
        row.add_suffix(badge)
        registered = unit.registration_state in {
            RegistrationState.REGISTERED, RegistrationState.MISSING
        }
        button = Gtk.Button(
            label=_("Remove") if registered else _("Add"),
            valign=Gtk.Align.CENTER,
        )
        button.add_css_class("flat")
        button.connect("clicked", self._on_registration, unit)
        row.add_suffix(button)
        if self.app.journal is not None and unit.supports(Capability.LOGS):
            logs = Gtk.Button(
                icon_name="document-open-recent-symbolic",
                tooltip_text=_("Show logs"),
                valign=Gtk.Align.CENTER,
            )
            logs.connect(
                "clicked", lambda _button: self.app.open_logs(unit.unit_id)
            )
            row.add_suffix(logs)
        if unit.can_change_state and self.app.commands is not None:
            self._add_operation_row(row, unit)
        self._detail(row, _("Load state"), unit.load_state.value)
        self._detail(row, _("Service file"), unit.fragment_path or _("Not found"))
        if unit.exec_commands:
            self._detail(row, _("ExecStart"), " ".join(unit.exec_commands[0]))
        if unit.working_directory:
            self._detail(row, _("Working directory"), unit.working_directory)
        for reason in unit.access_reasons:
            self._detail(row, _("Safety assessment"), reason)
        if unit.diagnostic_details:
            diagnostic = Adw.ActionRow(
                title=_("Service inspection failed"),
                subtitle=_("Copy the diagnostic details for troubleshooting."),
            )
            copy_diagnostic = Gtk.Button(
                icon_name="edit-copy-symbolic",
                tooltip_text=_("Copy diagnostic details"),
                valign=Gtk.Align.CENTER,
            )
            copy_diagnostic.connect(
                "clicked",
                lambda _button: self._copy_diagnostic(unit.diagnostic_details or ""),
            )
            diagnostic.add_suffix(copy_diagnostic)
            row.add_row(diagnostic)
        return row

    def _add_operation_row(self, row: Adw.ExpanderRow, unit: UnitRecord) -> None:
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_margin_top(8)
        actions.set_margin_bottom(8)
        actions.set_margin_start(12)
        actions.set_margin_end(12)
        if unit.active_state is ActiveState.ACTIVE:
            self._action_button(actions, _("Stop"), unit, Capability.STOP, True)
            self._action_button(actions, _("Restart"), unit, Capability.RESTART, True)
        else:
            self._action_button(actions, _("Start"), unit, Capability.START, False)
        if unit.unit_file_state == "enabled":
            self._action_button(actions, _("Disable"), unit, Capability.DISABLE, True)
        else:
            self._action_button(actions, _("Enable"), unit, Capability.ENABLE, False)
        row.add_row(actions)

    def _action_button(
        self,
        box: Gtk.Box,
        label: str,
        unit: UnitRecord,
        capability: Capability,
        confirm: bool,
    ) -> None:
        button = Gtk.Button(label=label)
        button.connect(
            "clicked",
            self._confirm_operation if confirm else self._run_operation,
            unit,
            capability,
        )
        box.append(button)

    def _confirm_operation(
        self,
        _button: Gtk.Button,
        unit: UnitRecord,
        capability: Capability,
    ) -> None:
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_("Confirm service operation"),
            body=_("The service state will be changed. Continue?"),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("proceed", _("Continue"))
        dialog.set_response_appearance("proceed", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect(
            "response",
            lambda _dialog, response: (
                self.app.operate(unit.unit_id, capability)
                if response == "proceed" else None
            ),
        )
        dialog.present()

    def _run_operation(
        self,
        _button: Gtk.Button,
        unit: UnitRecord,
        capability: Capability,
    ) -> None:
        self.app.operate(unit.unit_id, capability)

    def _confirm_reload(self, _button: Gtk.Button) -> None:
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_("Reload the user manager?"),
            body=_("systemd will reread all of your user service definitions."),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("reload", _("Reload"))
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect(
            "response",
            lambda _dialog, response: self.app.reload_manager()
            if response == "reload" else None,
        )
        dialog.present()

    def notify(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message, timeout=3))

    def _on_registration(self, _button: Gtk.Button, unit: UnitRecord) -> None:
        self.app.change_registration(
            unit.unit_id, unit.registration_state is RegistrationState.DISCOVERED
        )

    @staticmethod
    def _detail(parent: Adw.ExpanderRow, title: str, value: str) -> None:
        detail = Adw.ActionRow(title=title, subtitle=value)
        detail.set_subtitle_selectable(True)
        parent.add_row(detail)

    def _clear_group(self) -> None:
        for row in self._rows:
            self.group.remove(row)
        self._rows.clear()

    def _add_row(self, row: Gtk.Widget) -> None:
        self.group.add(row)
        self._rows.append(row)

    def _sync_appearance_class(self, *_args: object) -> None:
        dark = (
            self.app.appearance is AppearancePreference.DARK
            or (
                self.app.appearance is AppearancePreference.SYSTEM
                and self.style_manager.get_dark()
            )
        )
        self.remove_css_class("coffee-light" if dark else "coffee-dark")
        self.add_css_class("coffee-dark" if dark else "coffee-light")


class UserServiceManagerApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        self.units: tuple[UnitRecord, ...] = ()
        self.settings: Gio.Settings | None = None
        self.discovery: DiscoveryService | None = None
        self.commands: UnitCommandService | None = None
        self.journal: JournalService | None = None
        self._log_windows: list[LogWindow] = []
        self.appearance = AppearancePreference.SYSTEM
        self.catalog = ServiceCatalog(MockServiceBackend())
        self.use_systemd = os.environ.get("USM_BACKEND") == "systemd"
        self._busy = False
        action = Gio.SimpleAction.new("appearance", GLib.VariantType.new("s"))
        action.connect("activate", self._on_appearance)
        self.add_action(action)

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        self._load_css()
        try:
            self.settings = Gio.Settings.new(SETTINGS_ID)
            preference = AppearancePreference.parse(self.settings.get_string("appearance"))
        except GLib.Error:
            preference = AppearancePreference.SYSTEM
        self._apply_appearance(preference)
        if self.use_systemd:
            repository = (
                GSettingsRegistrationRepository(self.settings)
                if self.settings is not None else MemoryRegistrationRepository()
            )
            self.discovery = DiscoveryService(
                UserUnitFileScanner(), GioSystemdUnitQuery(), repository
            )
            self.journal = JournalService(self.discovery, SystemdJournalReader())
            if os.environ.get("USM_COMMANDS") == "enabled":
                self.commands = UnitCommandService(
                    self.discovery, GioSystemdUnitCommands()
                )

    def do_activate(self) -> None:
        window = self.get_active_window() or MainWindow(self)
        window.present()
        if not self.units:
            self.reload_units()

    def reload_units(self) -> None:
        if self._busy:
            return
        window = self.get_active_window()
        if isinstance(window, MainWindow):
            window.show_loading()
        operation = self.discovery.scan if self.discovery else self.catalog.load
        self._run_async(operation)

    def change_registration(self, unit_id: UnitId, register: bool) -> None:
        if self.discovery is None or self._busy:
            return
        operation = self.discovery.register if register else self.discovery.unregister
        self._run_async(lambda: operation(unit_id))

    def operate(self, unit_id: UnitId, capability: Capability) -> None:
        if self.commands is None or self._busy:
            return
        self._run_async(
            lambda: self.commands.operate(unit_id, capability),
            _("Operation completed"),
        )

    def reload_manager(self) -> None:
        if self.commands is None or self._busy:
            return
        self._run_async(self.commands.reload, _("User manager reloaded"))

    def open_logs(self, unit_id: UnitId) -> None:
        parent = self.get_active_window()
        if self.journal is None or not isinstance(parent, MainWindow):
            return
        window = LogWindow(parent, unit_id, self.journal)
        self._log_windows.append(window)
        window.connect(
            "close-request",
            lambda closed, *_args: self._forget_log_window(closed),
        )
        window.present()

    def _forget_log_window(self, window: LogWindow) -> bool:
        if window in self._log_windows:
            self._log_windows.remove(window)
        return False

    def _run_async(
        self, operation: Callable[[], object], success_message: str | None = None
    ) -> None:
        self._busy = True
        def worker() -> None:
            try:
                result = asyncio.run(operation())
            except Exception as error:
                GLib.idle_add(self._failed, str(error), success_message is not None)
            else:
                GLib.idle_add(self._loaded, result, success_message)
        Thread(target=worker, daemon=True).start()

    def _loaded(
        self, units: tuple[UnitRecord, ...], message: str | None = None
    ) -> bool:
        self._busy = False
        self.units = units
        window = self.get_active_window()
        if isinstance(window, MainWindow):
            window.show_units(units)
            if message:
                window.notify(message)
        return GLib.SOURCE_REMOVE

    def _failed(self, message: str, preserve_units: bool = False) -> bool:
        self._busy = False
        window = self.get_active_window()
        if isinstance(window, MainWindow):
            if preserve_units:
                window.show_operation_error(message)
            else:
                window.show_error(message)
        return GLib.SOURCE_REMOVE

    def _on_appearance(self, _action: Gio.SimpleAction, parameter: GLib.Variant) -> None:
        preference = AppearancePreference.parse(parameter.get_string())
        self._apply_appearance(preference)
        if self.settings is not None:
            self.settings.set_string("appearance", preference.value)

    def _apply_appearance(self, preference: AppearancePreference) -> None:
        self.appearance = preference
        Adw.StyleManager.get_default().set_color_scheme({
            AppearancePreference.SYSTEM: Adw.ColorScheme.DEFAULT,
            AppearancePreference.LIGHT: Adw.ColorScheme.FORCE_LIGHT,
            AppearancePreference.DARK: Adw.ColorScheme.FORCE_DARK,
        }[preference])
        window = self.get_active_window()
        if isinstance(window, MainWindow):
            window._sync_appearance_class()

    @staticmethod
    def _load_css() -> None:
        provider = Gtk.CssProvider()
        provider.load_from_path(str(Path(__file__).with_name("style.css")))
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
