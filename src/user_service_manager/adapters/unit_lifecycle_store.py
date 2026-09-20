"""Strict local storage for drop-ins and reversible service deletion."""

from __future__ import annotations

from datetime import datetime, timezone
import errno
import json
import os
from pathlib import Path
import secrets
import stat
import tempfile

from user_service_manager.domain.editing import MAX_UNIT_FILE_BYTES, content_revision
from user_service_manager.domain.lifecycle import (
    DropInContentError,
    DropInSnapshot,
    LifecycleConflictError,
    LifecycleSafetyError,
    ServiceBackup,
    ServiceLifecycleSnapshot,
    validate_drop_in_content,
    validate_drop_in_name,
)
from user_service_manager.domain.models import UnitId


class LocalUnitLifecycleStore:
    BACKUP_DIRECTORY = ".user-service-manager-backups"

    def __init__(self, origin: Path | None = None, home: Path | None = None) -> None:
        self.home = (home or Path.home()).resolve()
        self.origin = origin or self.home / ".config/systemd/user"

    async def list_drop_ins(self, unit_id: UnitId) -> tuple[DropInSnapshot, ...]:
        directory = self._drop_in_directory(unit_id, create=False, missing_ok=True)
        if directory is None:
            return ()
        snapshots = [
            self._load_drop_in_sync(unit_id, entry.name)
            for entry in directory.iterdir()
            if entry.name.endswith(".conf")
        ]
        return tuple(sorted(snapshots, key=lambda item: item.name))

    async def load_drop_in(self, unit_id: UnitId, name: str) -> DropInSnapshot:
        return self._load_drop_in_sync(unit_id, name)

    async def save_drop_in(
        self,
        unit_id: UnitId,
        name: str,
        content: str,
        expected_revision: str | None,
    ) -> None:
        validate_drop_in_name(name)
        encoded = validate_drop_in_content(content)
        directory = self._drop_in_directory(unit_id, create=True)
        assert directory is not None
        target = directory / name
        current = self._read_optional(target)
        if expected_revision is None:
            if current is not None:
                raise LifecycleConflictError("A drop-in with this name already exists.")
        elif current is None or content_revision(current) != expected_revision:
            raise LifecycleConflictError("The drop-in changed after it was loaded.")
        self._atomic_write(
            directory,
            target,
            encoded,
            exclusive=expected_revision is None,
        )

    async def delete_drop_in(self, snapshot: DropInSnapshot) -> None:
        directory = self._drop_in_directory(snapshot.unit_id, create=False)
        assert directory is not None
        target = directory / validate_drop_in_name(snapshot.name)
        current = self._read_optional(target)
        if current is None or content_revision(current) != snapshot.revision:
            raise LifecycleConflictError("The drop-in changed after it was loaded.")
        target.unlink()
        self._fsync_directory(directory)
        if not any(directory.iterdir()):
            directory.rmdir()
            self._fsync_directory(directory.parent)

    async def load_service_lifecycle(self, unit_id: UnitId) -> ServiceLifecycleSnapshot:
        origin = self._validated_origin(create=False)
        raw = self._read_owned_regular(origin / unit_id.value)
        try:
            service_content = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise DropInContentError("The service file is not valid UTF-8.") from error
        drop_ins = await self.list_drop_ins(unit_id)
        return ServiceLifecycleSnapshot(
            unit_id,
            service_content,
            content_revision(raw),
            drop_ins,
        )

    async def archive_and_delete(self, snapshot: ServiceLifecycleSnapshot) -> ServiceBackup:
        current = await self.load_service_lifecycle(snapshot.unit_id)
        if (
            current.service_revision != snapshot.service_revision
            or current.drop_ins != snapshot.drop_ins
        ):
            raise LifecycleConflictError("The service or its drop-ins changed before deletion.")

        backup = self._create_backup(current)
        # Recheck after the durable backup is complete and immediately before deletion.
        latest = await self.load_service_lifecycle(snapshot.unit_id)
        if (
            latest.service_revision != snapshot.service_revision
            or latest.drop_ins != snapshot.drop_ins
        ):
            raise LifecycleConflictError(
                "The service or its drop-ins changed while the backup was being created."
            )

        origin = self._validated_origin(create=False)
        drop_in_directory = self._drop_in_directory(
            snapshot.unit_id, create=False, missing_ok=True
        )
        if drop_in_directory is not None:
            expected_names = {item.name for item in snapshot.drop_ins}
            actual_names = {entry.name for entry in drop_in_directory.iterdir()}
            if actual_names != expected_names:
                raise LifecycleSafetyError("The drop-in directory contains unmanaged entries.")
            for item in snapshot.drop_ins:
                (drop_in_directory / item.name).unlink()
            drop_in_directory.rmdir()
        (origin / snapshot.unit_id.value).unlink()
        self._fsync_directory(origin)
        return backup

    async def list_backups(self, unit_id: UnitId) -> tuple[ServiceBackup, ...]:
        root = self._backup_unit_directory(unit_id, create=False, missing_ok=True)
        if root is None:
            return ()
        backups: list[ServiceBackup] = []
        for entry in root.iterdir():
            if not entry.is_dir() or entry.is_symlink():
                continue
            try:
                backups.append(self._read_manifest(unit_id, entry))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        return tuple(sorted(backups, key=lambda item: item.created_at, reverse=True))

    async def restore(self, backup: ServiceBackup) -> None:
        origin = self._validated_origin(create=True)
        target = origin / backup.unit_id.value
        drop_target = origin / f"{backup.unit_id.value}.d"
        if (
            target.exists()
            or target.is_symlink()
            or drop_target.exists()
            or drop_target.is_symlink()
        ):
            raise LifecycleConflictError("The service or its drop-in directory already exists.")

        backup_directory = self._backup_unit_directory(backup.unit_id, create=False)
        assert backup_directory is not None
        source = backup_directory / backup.backup_id
        actual = self._read_manifest(backup.unit_id, source)
        if actual != backup:
            raise LifecycleConflictError("The selected backup changed before restoration.")
        service_raw = self._read_owned_regular(source / "service.service")
        drop_raw = {
            name: self._read_owned_regular(source / "drop-ins" / name)
            for name in backup.drop_in_names
        }

        created_drop_directory = False
        created_service = False
        try:
            self._atomic_write(origin, target, service_raw, exclusive=True)
            created_service = True
            if drop_raw:
                drop_target.mkdir(mode=0o700)
                created_drop_directory = True
                for name, raw in drop_raw.items():
                    self._atomic_write(
                        drop_target, drop_target / name, raw, exclusive=True
                    )
            self._fsync_directory(origin)
        except Exception:
            if created_drop_directory:
                for name in drop_raw:
                    (drop_target / name).unlink(missing_ok=True)
                try:
                    drop_target.rmdir()
                except OSError:
                    pass
            if created_service:
                target.unlink(missing_ok=True)
            self._fsync_directory(origin)
            raise

    def _load_drop_in_sync(self, unit_id: UnitId, name: str) -> DropInSnapshot:
        validate_drop_in_name(name)
        directory = self._drop_in_directory(unit_id, create=False)
        assert directory is not None
        raw = self._read_owned_regular(directory / name)
        try:
            return DropInSnapshot.from_bytes(unit_id, name, raw)
        except UnicodeDecodeError as error:
            raise DropInContentError("The drop-in is not valid UTF-8.") from error

    def _validated_origin(self, create: bool) -> Path:
        if create:
            self.origin.mkdir(mode=0o700, parents=True, exist_ok=True)
        resolved = self.origin.resolve(strict=True)
        try:
            resolved.relative_to(self.home)
        except ValueError as error:
            raise LifecycleSafetyError(
                "The user service directory must remain inside home."
            ) from error
        self._validate_owned_directory(resolved)
        return resolved

    def _drop_in_directory(
        self,
        unit_id: UnitId,
        *,
        create: bool,
        missing_ok: bool = False,
    ) -> Path | None:
        origin = self._validated_origin(create=create)
        directory = origin / f"{unit_id.value}.d"
        if not directory.exists() and not directory.is_symlink():
            if not create:
                if missing_ok:
                    return None
                raise FileNotFoundError(directory)
            directory.mkdir(mode=0o700)
            self._fsync_directory(origin)
        if directory.is_symlink():
            raise LifecycleSafetyError("The drop-in directory must not be a symbolic link.")
        self._validate_owned_directory(directory)
        return directory

    def _backup_unit_directory(
        self,
        unit_id: UnitId,
        *,
        create: bool,
        missing_ok: bool = False,
    ) -> Path | None:
        origin = self._validated_origin(create=create)
        root = origin / self.BACKUP_DIRECTORY
        if not root.exists():
            if not create:
                if missing_ok:
                    return None
                raise FileNotFoundError(root)
            root.mkdir(mode=0o700)
        if root.is_symlink():
            raise LifecycleSafetyError("The backup directory must not be a symbolic link.")
        self._validate_owned_directory(root)
        unit_root = root / unit_id.value
        if not unit_root.exists():
            if not create:
                if missing_ok:
                    return None
                raise FileNotFoundError(unit_root)
            unit_root.mkdir(mode=0o700)
        if unit_root.is_symlink():
            raise LifecycleSafetyError("The unit backup directory must not be a symbolic link.")
        self._validate_owned_directory(unit_root)
        return unit_root

    def _create_backup(self, snapshot: ServiceLifecycleSnapshot) -> ServiceBackup:
        unit_root = self._backup_unit_directory(snapshot.unit_id, create=True)
        assert unit_root is not None
        created_at = datetime.now(timezone.utc)
        backup_id = created_at.strftime("%Y%m%dT%H%M%S.%fZ") + f"-{secrets.token_hex(4)}"
        destination = unit_root / backup_id
        destination.mkdir(mode=0o700)
        try:
            self._atomic_write(
                destination,
                destination / "service.service",
                snapshot.service_content.encode("utf-8"),
            )
            if snapshot.drop_ins:
                drop_destination = destination / "drop-ins"
                drop_destination.mkdir(mode=0o700)
                for item in snapshot.drop_ins:
                    self._atomic_write(
                        drop_destination,
                        drop_destination / item.name,
                        item.content.encode("utf-8"),
                    )
            manifest = {
                "format": 1,
                "unit_id": snapshot.unit_id.value,
                "backup_id": backup_id,
                "created_at": created_at.isoformat(),
                "drop_ins": [item.name for item in snapshot.drop_ins],
            }
            self._atomic_write(
                destination,
                destination / "manifest.json",
                (json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n").encode(),
            )
            self._fsync_directory(destination)
            self._fsync_directory(unit_root)
        except Exception:
            for child in destination.rglob("*"):
                if child.is_file():
                    child.unlink(missing_ok=True)
            for child in sorted(destination.rglob("*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
            destination.rmdir()
            raise
        return ServiceBackup(
            snapshot.unit_id,
            backup_id,
            created_at,
            tuple(item.name for item in snapshot.drop_ins),
        )

    def _read_manifest(self, unit_id: UnitId, directory: Path) -> ServiceBackup:
        self._validate_owned_directory(directory)
        raw = self._read_owned_regular(directory / "manifest.json")
        data = json.loads(raw.decode("utf-8"))
        if data.get("format") != 1 or data.get("unit_id") != unit_id.value:
            raise ValueError("Unsupported or mismatched backup manifest.")
        backup_id = str(data["backup_id"])
        if backup_id != directory.name or "/" in backup_id or "\\" in backup_id:
            raise ValueError("Invalid backup identifier.")
        drop_ins = tuple(validate_drop_in_name(str(name)) for name in data["drop_ins"])
        return ServiceBackup(
            unit_id,
            backup_id,
            datetime.fromisoformat(str(data["created_at"])),
            drop_ins,
        )

    @staticmethod
    def _validate_owned_directory(directory: Path) -> None:
        metadata = directory.stat(follow_symlinks=False)
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise LifecycleSafetyError("A lifecycle directory is not owned by this user.")
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise LifecycleSafetyError("A lifecycle directory is writable by another account.")

    @staticmethod
    def _read_owned_regular(target: Path) -> bytes:
        try:
            descriptor = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise LifecycleSafetyError("Symbolic links are not accepted here.") from error
            raise
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
                raise LifecycleSafetyError("Only user-owned regular files are accepted.")
            if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise LifecycleSafetyError("The file is writable by another account.")
            if metadata.st_size > MAX_UNIT_FILE_BYTES:
                raise DropInContentError("The lifecycle file exceeds the 256 KiB size limit.")
            raw = stream.read(MAX_UNIT_FILE_BYTES + 1)
        if len(raw) > MAX_UNIT_FILE_BYTES:
            raise DropInContentError("The lifecycle file exceeds the 256 KiB size limit.")
        return raw

    def _read_optional(self, target: Path) -> bytes | None:
        try:
            return self._read_owned_regular(target)
        except FileNotFoundError:
            return None

    @staticmethod
    def _atomic_write(
        directory: Path,
        target: Path,
        content: bytes,
        *,
        exclusive: bool = False,
    ) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=directory
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if exclusive:
                try:
                    os.link(temporary, target, follow_symlinks=False)
                except FileExistsError as error:
                    raise LifecycleConflictError(
                        f"The destination already exists: {target.name}"
                    ) from error
                temporary.unlink()
            else:
                os.replace(temporary, target)
            LocalUnitLifecycleStore._fsync_directory(directory)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
