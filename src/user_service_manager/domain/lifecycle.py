"""Domain values for drop-ins, previews, deletion, and restoration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import difflib
import re

from user_service_manager.domain.editing import MAX_UNIT_FILE_BYTES, content_revision
from user_service_manager.domain.models import UnitId


DROP_IN_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.conf$")
MAX_PREVIEW_CHARS = 64 * 1024


class DropInContentError(ValueError):
    """Raised when a drop-in name or body is outside the supported subset."""


class LifecycleConflictError(RuntimeError):
    """Raised when files changed after a lifecycle operation was prepared."""


class LifecycleSafetyError(PermissionError):
    """Raised when a lifecycle operation would cross a safety boundary."""


class LifecycleReloadError(RuntimeError):
    """Raised when files changed successfully but daemon-reload failed."""


def validate_drop_in_name(name: str) -> str:
    if not DROP_IN_NAME_PATTERN.fullmatch(name):
        raise DropInContentError(
            "A drop-in name must end in .conf and contain only letters, numbers, '.', '_', or '-'."
        )
    return name


def validate_drop_in_content(content: str) -> bytes:
    try:
        encoded = content.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise DropInContentError("The drop-in must be valid UTF-8 text.") from error
    if not encoded:
        raise DropInContentError("The drop-in must not be empty.")
    if len(encoded) > MAX_UNIT_FILE_BYTES:
        raise DropInContentError("The drop-in exceeds the 256 KiB size limit.")
    if "\x00" in content:
        raise DropInContentError("The drop-in must not contain NUL characters.")

    section_seen = False
    continuation = False
    for number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if continuation:
            continuation = raw_line.rstrip().endswith("\\")
            continue
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            if not section or "[" in section or "]" in section:
                raise DropInContentError(f"Invalid section header on line {number}.")
            section_seen = True
        elif not section_seen:
            raise DropInContentError(f"A directive appears before a section on line {number}.")
        elif "=" not in raw_line:
            raise DropInContentError(f"Expected a directive on line {number}.")
        continuation = raw_line.rstrip().endswith("\\")
    if continuation:
        raise DropInContentError("The final line has an unfinished continuation.")
    if not section_seen:
        raise DropInContentError("At least one section is required.")
    return encoded


def unified_preview(before: str, after: str, before_name: str, after_name: str) -> str:
    lines = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=before_name,
        tofile=after_name,
    )
    preview = "".join(lines) or "No textual changes.\n"
    if len(preview) > MAX_PREVIEW_CHARS:
        return preview[:MAX_PREVIEW_CHARS] + "\n… preview truncated …\n"
    return preview


@dataclass(frozen=True, slots=True)
class DropInSnapshot:
    unit_id: UnitId
    name: str
    content: str
    revision: str

    @classmethod
    def from_bytes(cls, unit_id: UnitId, name: str, content: bytes) -> "DropInSnapshot":
        return cls(
            unit_id,
            name,
            content.decode("utf-8", errors="strict"),
            content_revision(content),
        )


@dataclass(frozen=True, slots=True)
class PreparedDropInChange:
    unit_id: UnitId
    name: str
    content: str
    expected_revision: str | None
    creating: bool
    verification_details: str
    diff: str


@dataclass(frozen=True, slots=True)
class ServiceLifecycleSnapshot:
    unit_id: UnitId
    service_content: str
    service_revision: str
    drop_ins: tuple[DropInSnapshot, ...]


@dataclass(frozen=True, slots=True)
class ServiceBackup:
    unit_id: UnitId
    backup_id: str
    created_at: datetime
    drop_in_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PreparedServiceDeletion:
    snapshot: ServiceLifecycleSnapshot
    preview: str


@dataclass(frozen=True, slots=True)
class PreparedServiceRestore:
    backup: ServiceBackup
    preview: str
