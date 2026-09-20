"""Ubuntu 26.04 acceptance gate for v1.3 drop-ins and lifecycle.

Run as the logged-in desktop user. The script uses one reserved fixture unit,
refuses existing fixtures/backups, and removes only its explicit artifacts.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import stat

from user_service_manager.adapters.filesystem_scanner import UserUnitFileScanner
from user_service_manager.adapters.gio_systemd_commands import GioSystemdUnitCommands
from user_service_manager.adapters.gio_systemd_query import GioSystemdUnitQuery
from user_service_manager.adapters.path_policy import ServicePathPolicy
from user_service_manager.adapters.registration_repositories import MemoryRegistrationRepository
from user_service_manager.adapters.systemd_unit_verifier import SystemdAnalyzeUnitVerifier
from user_service_manager.adapters.unit_file_store import LocalUnitFileStore
from user_service_manager.adapters.unit_lifecycle_store import LocalUnitLifecycleStore
from user_service_manager.application.discovery_service import DiscoveryService
from user_service_manager.application.editing_service import UnitEditingService
from user_service_manager.application.lifecycle_service import UnitLifecycleService
from user_service_manager.domain.models import UnitId


UNIT_ID = UnitId("codex-usm-v130-validation.service")
DROP_IN_NAME = "10-environment.conf"
SERVICE = """[Unit]
Description=User Service Manager v1.3 lifecycle validation

[Service]
Type=oneshot
ExecStart=/usr/bin/true

[Install]
WantedBy=default.target
"""
DROP_IN = "[Service]\nEnvironment=USM_VALIDATION=initial\n"
EDITED_DROP_IN = DROP_IN.replace("initial", "edited")


async def run() -> None:
    origin = Path.home() / ".config/systemd/user"
    target = origin / UNIT_ID.value
    drop_directory = origin / f"{UNIT_ID.value}.d"
    backup_root = origin / LocalUnitLifecycleStore.BACKUP_DIRECTORY / UNIT_ID.value
    if any(path.exists() or path.is_symlink() for path in (target, drop_directory, backup_root)):
        raise RuntimeError("Reserved v1.3 validation fixture already exists")

    commands = GioSystemdUnitCommands()
    registrations = MemoryRegistrationRepository()
    discovery = DiscoveryService(
        UserUnitFileScanner(origin),
        GioSystemdUnitQuery(),
        registrations,
        ServicePathPolicy(),
    )
    verifier = SystemdAnalyzeUnitVerifier()
    editing = UnitEditingService(
        LocalUnitFileStore(origin), verifier, commands, discovery
    )
    lifecycle_store = LocalUnitLifecycleStore(origin)
    lifecycle = UnitLifecycleService(
        lifecycle_store, verifier, commands, discovery
    )

    try:
        created = await editing.prepare(UNIT_ID, SERVICE, None)
        await editing.apply(created, False)
        await discovery.register(UNIT_ID)

        drop_change = await lifecycle.prepare_drop_in(
            UNIT_ID, DROP_IN_NAME, DROP_IN, None
        )
        assert "+++ b/10-environment.conf" in drop_change.diff
        await lifecycle.apply_drop_in(drop_change)
        snapshot = await lifecycle.load_drop_in(UNIT_ID, DROP_IN_NAME)
        edited = await lifecycle.prepare_drop_in(
            UNIT_ID, DROP_IN_NAME, EDITED_DROP_IN, snapshot.revision
        )
        assert "-Environment=USM_VALIDATION=initial" in edited.diff
        assert "+Environment=USM_VALIDATION=edited" in edited.diff
        await lifecycle.apply_drop_in(edited)

        deletion = await lifecycle.prepare_delete(UNIT_ID)
        assert UNIT_ID.value in deletion.preview
        await lifecycle.apply_delete(deletion)
        assert not target.exists() and not drop_directory.exists()

        restoration = await lifecycle.prepare_restore(UNIT_ID)
        await lifecycle.apply_restore(restoration)
        assert target.read_text(encoding="utf-8") == SERVICE
        restored_drop = drop_directory / DROP_IN_NAME
        assert restored_drop.read_text(encoding="utf-8") == EDITED_DROP_IN
        assert stat.S_IMODE(target.stat().st_mode) == 0o600
        assert stat.S_IMODE(restored_drop.stat().st_mode) == 0o600
        print("PASS: drop-in create/edit/verify/diff, archive delete, restore, reload, rescan")
    finally:
        target.unlink(missing_ok=True)
        if drop_directory.is_dir() and not drop_directory.is_symlink():
            (drop_directory / DROP_IN_NAME).unlink(missing_ok=True)
            drop_directory.rmdir()
        if backup_root.is_dir() and not backup_root.is_symlink():
            for backup in tuple(backup_root.iterdir()):
                if not backup.is_dir() or backup.is_symlink():
                    continue
                (backup / "service.service").unlink(missing_ok=True)
                (backup / "manifest.json").unlink(missing_ok=True)
                drop_backup = backup / "drop-ins"
                if drop_backup.is_dir() and not drop_backup.is_symlink():
                    (drop_backup / DROP_IN_NAME).unlink(missing_ok=True)
                    drop_backup.rmdir()
                backup.rmdir()
            backup_root.rmdir()
        await commands.reload()


if __name__ == "__main__":
    os.umask(0o077)
    asyncio.run(run())
