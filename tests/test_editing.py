from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from user_service_manager.adapters.systemd_unit_verifier import SystemdAnalyzeUnitVerifier
from user_service_manager.adapters.unit_file_store import LocalUnitFileStore
from user_service_manager.application.editing_service import UnitEditingService
from user_service_manager.domain.editing import (
    EditConflictError,
    MAX_UNIT_FILE_BYTES,
    UnitContentError,
    UnitFileSnapshot,
    UnitReloadError,
    validate_unit_content,
)
from user_service_manager.domain.models import UnitId


UNIT_ID = UnitId("example.service")
VALID = "[Unit]\nDescription=Example\n\n[Service]\nExecStart=/usr/bin/true\n"


class FakeStore:
    def __init__(self) -> None:
        self.snapshot = UnitFileSnapshot(UNIT_ID, VALID, "revision")
        self.saved: list[tuple[UnitId, str, str | None, bool]] = []

    async def load(self, unit_id: UnitId) -> UnitFileSnapshot:
        if unit_id != self.snapshot.unit_id:
            raise FileNotFoundError(unit_id.value)
        return self.snapshot

    async def save(
        self,
        unit_id: UnitId,
        content: str,
        expected_revision: str | None,
        create_backup: bool,
    ) -> Path | None:
        self.saved.append((unit_id, content, expected_revision, create_backup))
        return Path("example.service.backup") if create_backup else None


class FakeVerifier:
    def __init__(self) -> None:
        self.calls: list[tuple[UnitId, str]] = []

    async def verify(self, unit_id: UnitId, content: str) -> str:
        self.calls.append((unit_id, content))
        return "verified"


class FakeCommands:
    def __init__(self) -> None:
        self.reloads = 0

    async def operate(self, *_args: object) -> None:
        raise AssertionError("not used")

    async def reload(self) -> None:
        self.reloads += 1


class FakeDiscovery:
    def __init__(self) -> None:
        self.scans = 0

    async def scan(self) -> tuple[object, ...]:
        self.scans += 1
        return ()


class UnitContentTests(unittest.TestCase):
    def test_requires_service_section_and_directives(self) -> None:
        with self.assertRaises(UnitContentError):
            validate_unit_content("[Unit]\nDescription=Only metadata\n")
        with self.assertRaises(UnitContentError):
            validate_unit_content("[Service]\nnot-a-directive\n")

    def test_accepts_comments_sections_and_continuations(self) -> None:
        content = "# comment\n[Service]\nExecStart=/usr/bin/printf \\\n  hello\n"
        self.assertEqual(validate_unit_content(content), content.encode())

    def test_rejects_oversized_content(self) -> None:
        with self.assertRaises(UnitContentError):
            validate_unit_content("[Service]\n#" + "x" * MAX_UNIT_FILE_BYTES)


class LocalUnitFileStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.origin = self.home / ".config/systemd/user"
        self.store = LocalUnitFileStore(self.origin, self.home)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_create_load_edit_and_explicit_backup(self) -> None:
        backup = asyncio.run(self.store.save(UNIT_ID, VALID, None, False))
        self.assertIsNone(backup)
        loaded = asyncio.run(self.store.load(UNIT_ID))
        changed = VALID.replace("Example", "Changed")

        backup = asyncio.run(
            self.store.save(UNIT_ID, changed, loaded.revision, True)
        )

        self.assertIsNotNone(backup)
        assert backup is not None
        self.assertEqual(backup.read_text(encoding="utf-8"), VALID)
        self.assertEqual(asyncio.run(self.store.load(UNIT_ID)).content, changed)

    def test_create_refuses_existing_file(self) -> None:
        asyncio.run(self.store.save(UNIT_ID, VALID, None, False))
        with self.assertRaises(EditConflictError):
            asyncio.run(self.store.save(UNIT_ID, VALID, None, False))

    def test_concurrent_create_never_overwrites(self) -> None:
        def attempt(content: str) -> str:
            try:
                asyncio.run(self.store.save(UNIT_ID, content, None, False))
                return "saved"
            except EditConflictError:
                return "conflict"

        first = VALID.replace("Example", "First")
        second = VALID.replace("Example", "Second")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = tuple(pool.map(attempt, (first, second)))
        self.assertCountEqual(results, ("saved", "conflict"))
        self.assertIn(asyncio.run(self.store.load(UNIT_ID)).content, {first, second})

    def test_new_file_refuses_meaningless_backup_request(self) -> None:
        with self.assertRaises(UnitContentError):
            asyncio.run(self.store.save(UNIT_ID, VALID, None, True))

    def test_edit_refuses_external_change(self) -> None:
        asyncio.run(self.store.save(UNIT_ID, VALID, None, False))
        loaded = asyncio.run(self.store.load(UNIT_ID))
        (self.origin / UNIT_ID.value).write_text(
            VALID.replace("Example", "External"), encoding="utf-8"
        )
        with self.assertRaises(EditConflictError):
            asyncio.run(self.store.save(UNIT_ID, VALID, loaded.revision, False))

    def test_load_refuses_symlink(self) -> None:
        self.origin.mkdir(parents=True)
        target = self.home / "target.service"
        target.write_text(VALID, encoding="utf-8")
        (self.origin / UNIT_ID.value).symlink_to(target)
        with self.assertRaises(PermissionError):
            asyncio.run(self.store.load(UNIT_ID))


class SystemdAnalyzeUnitVerifierTests(unittest.TestCase):
    def test_invokes_fixed_command_and_bounds_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "systemd-analyze"
            executable.write_text("placeholder", encoding="utf-8")

            def fake_run(args: list[str], **kwargs: object):
                output = kwargs["stdout"]
                output.write(b"x" * 70000)  # type: ignore[union-attr]
                from subprocess import CompletedProcess

                return CompletedProcess(args, 0)

            with patch(
                "user_service_manager.adapters.systemd_unit_verifier.subprocess.run",
                side_effect=fake_run,
            ) as run:
                details = asyncio.run(
                    SystemdAnalyzeUnitVerifier(executable).verify(UNIT_ID, VALID)
                )

        args = run.call_args.args[0]
        self.assertEqual(args[0], str(executable))
        self.assertEqual(
            args[1:7],
            [
                "--user",
                "--no-pager",
                "--man=no",
                "--generators=no",
                "--recursive-errors=no",
                "verify",
            ],
        )
        self.assertEqual(len(details), 65536)
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(run.call_args.kwargs["env"]["PATH"], "/usr/bin:/bin")
        self.assertEqual(run.call_args.kwargs["env"]["LC_ALL"], "C.UTF-8")


class UnitEditingServiceTests(unittest.TestCase):
    def test_prepare_and_apply_validate_save_reload_and_rescan(self) -> None:
        store = FakeStore()
        verifier = FakeVerifier()
        commands = FakeCommands()
        discovery = FakeDiscovery()
        service = UnitEditingService(store, verifier, commands, discovery)  # type: ignore[arg-type]

        changed = VALID.replace("Example", "Changed")
        prepared = asyncio.run(service.prepare(UNIT_ID, changed, "revision"))
        result = asyncio.run(service.apply(prepared, True))

        self.assertEqual(prepared.verification_details, "verified")
        self.assertIn("--- a/example.service", prepared.diff)
        self.assertEqual(verifier.calls, [(UNIT_ID, changed)])
        self.assertEqual(store.saved, [(UNIT_ID, changed, "revision", True)])
        self.assertEqual(commands.reloads, 1)
        self.assertEqual(discovery.scans, 1)
        self.assertEqual(result, ())

    def test_prepare_rejects_stale_revision_before_verification(self) -> None:
        store = FakeStore()
        verifier = FakeVerifier()
        service = UnitEditingService(
            store, verifier, FakeCommands(), FakeDiscovery()  # type: ignore[arg-type]
        )
        with self.assertRaises(EditConflictError):
            asyncio.run(service.prepare(UNIT_ID, VALID, "stale"))
        self.assertEqual(verifier.calls, [])

    def test_reload_failure_reports_that_file_was_already_saved(self) -> None:
        class FailingCommands(FakeCommands):
            async def reload(self) -> None:
                raise RuntimeError("reload unavailable")

        store = FakeStore()
        service = UnitEditingService(
            store, FakeVerifier(), FailingCommands(), FakeDiscovery()  # type: ignore[arg-type]
        )
        prepared = asyncio.run(service.prepare(UNIT_ID, VALID, "revision"))
        with self.assertRaisesRegex(UnitReloadError, "was saved"):
            asyncio.run(service.apply(prepared, False))
        self.assertEqual(len(store.saved), 1)


if __name__ == "__main__":
    unittest.main()
