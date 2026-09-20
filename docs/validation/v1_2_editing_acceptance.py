"""Ubuntu 26.04 acceptance gate for v1.2 service-file editing.

Run as the logged-in desktop user. The script uses one reserved fixture unit,
refuses to start if it already exists, and removes every created file in finally.
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
from user_service_manager.adapters.registration_repositories import (
    MemoryRegistrationRepository,
)
from user_service_manager.adapters.systemd_unit_verifier import (
    SystemdAnalyzeUnitVerifier,
)
from user_service_manager.adapters.unit_file_store import LocalUnitFileStore
from user_service_manager.application.discovery_service import DiscoveryService
from user_service_manager.application.editing_service import UnitEditingService
from user_service_manager.domain.editing import EditConflictError
from user_service_manager.domain.models import UnitId


UNIT_ID = UnitId("codex-usm-v120-validation.service")
ORIGINAL = """[Unit]
Description=User Service Manager v1.2 validation

[Service]
Type=oneshot
ExecStart=/usr/bin/true
RemainAfterExit=yes
"""
EDITED = ORIGINAL.replace("v1.2 validation", "v1.2 edited validation")


async def run() -> None:
    origin = Path.home() / ".config/systemd/user"
    target = origin / UNIT_ID.value
    existing_backups = set(origin.glob(f"{UNIT_ID.value}.*.bak"))
    if target.exists() or target.is_symlink() or existing_backups:
        raise RuntimeError("Reserved validation fixture already exists; refusing to overwrite it")

    commands = GioSystemdUnitCommands()
    discovery = DiscoveryService(
        UserUnitFileScanner(origin),
        GioSystemdUnitQuery(),
        MemoryRegistrationRepository(),
        ServicePathPolicy(),
    )
    editing = UnitEditingService(
        LocalUnitFileStore(origin),
        SystemdAnalyzeUnitVerifier(),
        commands,
        discovery,
    )

    try:
        created = await editing.prepare(UNIT_ID, ORIGINAL, None)
        records = await editing.apply(created, False)
        assert any(record.unit_id == UNIT_ID for record in records)
        assert stat.S_IMODE(target.stat().st_mode) == 0o600

        snapshot = await editing.load(UNIT_ID)
        changed = await editing.prepare(UNIT_ID, EDITED, snapshot.revision)
        await editing.apply(changed, True)
        backups = set(origin.glob(f"{UNIT_ID.value}.*.bak"))
        assert len(backups) == 1
        backup = next(iter(backups))
        assert backup.read_text(encoding="utf-8") == ORIGINAL
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600

        stale = await editing.load(UNIT_ID)
        external = EDITED.replace("edited validation", "external validation")
        target.write_text(external, encoding="utf-8")
        try:
            await editing.prepare(UNIT_ID, EDITED, stale.revision)
        except EditConflictError:
            pass
        else:
            raise AssertionError("External modification was not rejected")
        assert target.read_text(encoding="utf-8") == external
        print("PASS: create, verify, atomic edit, backup, reload, rescan, conflict")
    finally:
        target.unlink(missing_ok=True)
        for backup in set(origin.glob(f"{UNIT_ID.value}.*.bak")) - existing_backups:
            backup.unlink(missing_ok=True)
        await commands.reload()


if __name__ == "__main__":
    os.umask(0o077)
    asyncio.run(run())
