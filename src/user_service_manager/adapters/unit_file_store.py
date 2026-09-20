"""Race-aware local storage for systemd user service definitions."""

from __future__ import annotations

from datetime import datetime, timezone
import errno
import os
from pathlib import Path
import stat
import tempfile

from user_service_manager.domain.editing import (
    MAX_UNIT_FILE_BYTES,
    EditConflictError,
    UnitContentError,
    UnitFileSnapshot,
    content_revision,
    validate_unit_content,
)
from user_service_manager.domain.models import UnitId


class LocalUnitFileStore:
    def __init__(self, origin: Path | None = None, home: Path | None = None) -> None:
        self.home = (home or Path.home()).resolve()
        self.origin = origin or self.home / ".config/systemd/user"

    async def load(self, unit_id: UnitId) -> UnitFileSnapshot:
        # Application services run on the presentation worker thread.
        return self._load_sync(unit_id)

    async def save(
        self,
        unit_id: UnitId,
        content: str,
        expected_revision: str | None,
        create_backup: bool,
    ) -> Path | None:
        # Application services run on the presentation worker thread.
        return self._save_sync(unit_id, content, expected_revision, create_backup)

    def _load_sync(self, unit_id: UnitId) -> UnitFileSnapshot:
        origin = self._validated_origin(create=False)
        target = origin / unit_id.value
        raw = self._read_regular_owned(target)
        try:
            content = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise UnitContentError("The existing service file is not valid UTF-8.") from error
        return UnitFileSnapshot(unit_id, content, content_revision(raw))

    def _save_sync(
        self,
        unit_id: UnitId,
        content: str,
        expected_revision: str | None,
        create_backup: bool,
    ) -> Path | None:
        encoded = validate_unit_content(content)
        origin = self._validated_origin(create=True)
        target = origin / unit_id.value
        current: bytes | None
        try:
            current = self._read_regular_owned(target)
        except FileNotFoundError:
            current = None

        if expected_revision is None:
            if current is not None:
                raise EditConflictError("A service file with this name already exists.")
            if create_backup:
                raise UnitContentError("A new service has no original file to back up.")
        else:
            if current is None:
                raise EditConflictError("The service file was removed after it was loaded.")
            if content_revision(current) != expected_revision:
                raise EditConflictError("The service file changed after it was loaded.")

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{unit_id.value}.", suffix=".tmp", dir=origin
        )
        temporary = Path(temporary_name)
        backup: Path | None = None
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            if current is not None and create_backup:
                backup = self._write_backup(origin, unit_id, current)
            os.replace(temporary, target)
            directory_fd = os.open(origin, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return backup

    def _validated_origin(self, create: bool) -> Path:
        if create:
            self.origin.mkdir(mode=0o700, parents=True, exist_ok=True)
        resolved = self.origin.resolve(strict=True)
        try:
            resolved.relative_to(self.home)
        except ValueError as error:
            raise PermissionError("The user service directory must remain inside home.") from error
        metadata = resolved.stat()
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise PermissionError("The user service directory is not owned by this user.")
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise PermissionError("The user service directory is writable by another account.")
        return resolved

    @staticmethod
    def _read_regular_owned(target: Path) -> bytes:
        try:
            descriptor = os.open(
                target,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            )
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise PermissionError(
                    "Only directly stored regular service files can be edited."
                ) from error
            raise
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise PermissionError(
                    "Only directly stored regular service files can be edited."
                )
            if metadata.st_uid != os.getuid():
                raise PermissionError("The service file is not owned by this user.")
            if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise PermissionError("The service file is writable by another account.")
            if metadata.st_size > MAX_UNIT_FILE_BYTES:
                raise UnitContentError("The service file exceeds the 256 KiB size limit.")
            raw = stream.read(MAX_UNIT_FILE_BYTES + 1)
        if len(raw) > MAX_UNIT_FILE_BYTES:
            raise UnitContentError("The service file exceeds the 256 KiB size limit.")
        return raw

    @staticmethod
    def _write_backup(origin: Path, unit_id: UnitId, content: bytes) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for counter in range(1000):
            suffix = "" if counter == 0 else f".{counter}"
            backup = origin / f"{unit_id.value}.{stamp}{suffix}.bak"
            try:
                descriptor = os.open(
                    backup,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                )
            except FileExistsError:
                continue
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            return backup
        raise FileExistsError("Could not allocate a unique backup filename.")
