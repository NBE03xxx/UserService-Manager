from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from user_service_manager.adapters.systemd_unit_verifier import SystemdAnalyzeUnitVerifier
from user_service_manager.adapters.unit_lifecycle_store import LocalUnitLifecycleStore
from user_service_manager.application.lifecycle_service import UnitLifecycleService
from user_service_manager.domain.lifecycle import (
    DropInContentError,
    LifecycleConflictError,
    LifecycleSafetyError,
    validate_drop_in_content,
    validate_drop_in_name,
)
from user_service_manager.domain.models import (
    AccessMode,
    ActiveState,
    LoadState,
    RegistrationState,
    UnitId,
    UnitRecord,
)


UNIT_ID = UnitId("lifecycle-example.service")
SERVICE = "[Unit]\nDescription=Lifecycle\n\n[Service]\nExecStart=/usr/bin/true\n"
DROP_IN = "[Service]\nEnvironment=MODE=test\n"


class DropInValidationTests(unittest.TestCase):
    def test_accepts_supported_name_and_content(self) -> None:
        self.assertEqual(validate_drop_in_name("10-environment.conf"), "10-environment.conf")
        self.assertEqual(validate_drop_in_content(DROP_IN), DROP_IN.encode())

    def test_rejects_paths_wrong_suffix_and_directive_before_section(self) -> None:
        for name in ("../override.conf", "override", ".hidden.conf", "bad name.conf"):
            with self.subTest(name=name), self.assertRaises(DropInContentError):
                validate_drop_in_name(name)
        with self.assertRaises(DropInContentError):
            validate_drop_in_content("Environment=MODE=test\n")


class LocalUnitLifecycleStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.origin = self.home / ".config/systemd/user"
        self.origin.mkdir(parents=True, mode=0o700)
        service_file = self.origin / UNIT_ID.value
        service_file.write_text(SERVICE, encoding="utf-8")
        service_file.chmod(0o600)
        self.store = LocalUnitLifecycleStore(self.origin, self.home)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_create_list_edit_and_delete_drop_in(self) -> None:
        asyncio.run(self.store.save_drop_in(UNIT_ID, "10-environment.conf", DROP_IN, None))
        listed = asyncio.run(self.store.list_drop_ins(UNIT_ID))
        self.assertEqual([item.name for item in listed], ["10-environment.conf"])
        changed = DROP_IN.replace("test", "production")
        asyncio.run(
            self.store.save_drop_in(
                UNIT_ID, listed[0].name, changed, listed[0].revision
            )
        )
        loaded = asyncio.run(self.store.load_drop_in(UNIT_ID, listed[0].name))
        self.assertEqual(loaded.content, changed)
        asyncio.run(self.store.delete_drop_in(loaded))
        self.assertEqual(asyncio.run(self.store.list_drop_ins(UNIT_ID)), ())

    def test_drop_in_edit_refuses_external_change(self) -> None:
        asyncio.run(self.store.save_drop_in(UNIT_ID, "override.conf", DROP_IN, None))
        loaded = asyncio.run(self.store.load_drop_in(UNIT_ID, "override.conf"))
        target = self.origin / f"{UNIT_ID.value}.d/override.conf"
        target.write_text(DROP_IN.replace("test", "external"), encoding="utf-8")
        with self.assertRaises(LifecycleConflictError):
            asyncio.run(
                self.store.save_drop_in(
                    UNIT_ID, "override.conf", DROP_IN, loaded.revision
                )
            )

    def test_refuses_symlink_drop_in_directory(self) -> None:
        outside = self.home / "outside"
        outside.mkdir()
        (self.origin / f"{UNIT_ID.value}.d").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(LifecycleSafetyError):
            asyncio.run(self.store.list_drop_ins(UNIT_ID))

    def test_archive_delete_and_restore_service_with_drop_ins(self) -> None:
        asyncio.run(self.store.save_drop_in(UNIT_ID, "override.conf", DROP_IN, None))
        snapshot = asyncio.run(self.store.load_service_lifecycle(UNIT_ID))
        backup = asyncio.run(self.store.archive_and_delete(snapshot))

        self.assertFalse((self.origin / UNIT_ID.value).exists())
        self.assertFalse((self.origin / f"{UNIT_ID.value}.d").exists())
        self.assertEqual(asyncio.run(self.store.list_backups(UNIT_ID)), (backup,))

        asyncio.run(self.store.restore(backup))
        restored = asyncio.run(self.store.load_service_lifecycle(UNIT_ID))
        self.assertEqual(restored.service_content, SERVICE)
        self.assertEqual(restored.drop_ins[0].content, DROP_IN)

    def test_delete_refuses_changed_service_and_restore_refuses_overwrite(self) -> None:
        snapshot = asyncio.run(self.store.load_service_lifecycle(UNIT_ID))
        (self.origin / UNIT_ID.value).write_text(
            SERVICE.replace("Lifecycle", "External"), encoding="utf-8"
        )
        with self.assertRaises(LifecycleConflictError):
            asyncio.run(self.store.archive_and_delete(snapshot))

        fresh = asyncio.run(self.store.load_service_lifecycle(UNIT_ID))
        backup = asyncio.run(self.store.archive_and_delete(fresh))
        service_file = self.origin / UNIT_ID.value
        service_file.write_text(SERVICE, encoding="utf-8")
        service_file.chmod(0o600)
        with self.assertRaises(LifecycleConflictError):
            asyncio.run(self.store.restore(backup))


class DropInVerifierTests(unittest.TestCase):
    def test_stages_drop_in_with_private_unit_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "systemd-analyze"
            executable.write_text("placeholder", encoding="utf-8")

            def fake_run(args: list[str], **kwargs: object):
                from subprocess import CompletedProcess

                self.assertTrue(Path(args[-1]).name.endswith(".service"))
                environment = kwargs["env"]
                self.assertIn("SYSTEMD_UNIT_PATH", environment)  # type: ignore[operator]
                staged_root = Path(environment["SYSTEMD_UNIT_PATH"])  # type: ignore[index]
                self.assertEqual(
                    (staged_root / f"{UNIT_ID.value}.d/override.conf").read_text(),
                    DROP_IN,
                )
                return CompletedProcess(args, 0)

            with patch(
                "user_service_manager.adapters.systemd_unit_verifier.subprocess.run",
                side_effect=fake_run,
            ):
                details = asyncio.run(
                    SystemdAnalyzeUnitVerifier(executable).verify_drop_in(
                        UNIT_ID, "override.conf", DROP_IN
                    )
                )
        self.assertIn("verification passed", details)


class FakeVerifier:
    async def verify_drop_in(self, unit_id: UnitId, name: str, content: str) -> str:
        return f"verified {unit_id.value}/{name}/{len(content)}"


class FakeCommands:
    def __init__(self) -> None:
        self.reloads = 0

    async def reload(self) -> None:
        self.reloads += 1


class FakeDiscovery:
    def __init__(self, record: UnitRecord) -> None:
        self.record = record
        self.scans = 0

    async def scan(self) -> tuple[UnitRecord, ...]:
        self.scans += 1
        return (self.record,)


def record(active: ActiveState = ActiveState.INACTIVE, state: str = "disabled") -> UnitRecord:
    return UnitRecord(
        UNIT_ID,
        "Lifecycle",
        LoadState.LOADED,
        active,
        "dead",
        state,
        f"/tmp/{UNIT_ID.value}",
        AccessMode.MANAGEABLE,
        RegistrationState.REGISTERED,
    )


class UnitLifecycleServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.origin = self.home / ".config/systemd/user"
        self.origin.mkdir(parents=True, mode=0o700)
        service_file = self.origin / UNIT_ID.value
        service_file.write_text(SERVICE, encoding="utf-8")
        service_file.chmod(0o600)
        self.store = LocalUnitLifecycleStore(self.origin, self.home)
        self.commands = FakeCommands()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def service(self, unit_record: UnitRecord | None = None) -> UnitLifecycleService:
        return UnitLifecycleService(
            self.store,
            FakeVerifier(),
            self.commands,  # type: ignore[arg-type]
            FakeDiscovery(unit_record or record()),  # type: ignore[arg-type]
        )

    def test_prepare_apply_drop_in_has_diff_and_reloads(self) -> None:
        service = self.service()
        prepared = asyncio.run(
            service.prepare_drop_in(UNIT_ID, "override.conf", DROP_IN, None)
        )
        self.assertIn("+++ b/override.conf", prepared.diff)
        result = asyncio.run(service.apply_drop_in(prepared))
        self.assertEqual(result[0].unit_id, UNIT_ID)
        self.assertEqual(self.commands.reloads, 1)

    def test_delete_requires_stopped_and_disabled_service(self) -> None:
        with self.assertRaises(LifecycleSafetyError):
            asyncio.run(
                self.service(record(ActiveState.ACTIVE, "disabled")).prepare_delete(UNIT_ID)
            )
        with self.assertRaises(LifecycleSafetyError):
            asyncio.run(
                self.service(record(ActiveState.INACTIVE, "enabled")).prepare_delete(UNIT_ID)
            )

    def test_delete_then_prepare_and_apply_latest_restore(self) -> None:
        service = self.service()
        deletion = asyncio.run(service.prepare_delete(UNIT_ID))
        self.assertIn("--- a/lifecycle-example.service", deletion.preview)
        asyncio.run(service.apply_delete(deletion))
        restoration = asyncio.run(service.prepare_restore(UNIT_ID))
        self.assertIn("Restore lifecycle-example.service", restoration.preview)
        asyncio.run(service.apply_restore(restoration))
        self.assertTrue((self.origin / UNIT_ID.value).exists())
        self.assertEqual(self.commands.reloads, 2)


if __name__ == "__main__":
    unittest.main()
