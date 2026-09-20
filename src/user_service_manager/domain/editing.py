"""Domain values and conservative validation for editable service files."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from user_service_manager.domain.models import UnitId


MAX_UNIT_FILE_BYTES = 256 * 1024


class UnitContentError(ValueError):
    """Raised when text cannot be accepted as a service definition."""


class EditConflictError(RuntimeError):
    """Raised when the target changed after it was loaded or validated."""


class UnitVerificationError(ValueError):
    """Raised when systemd rejects a staged service definition."""


class UnitReloadError(RuntimeError):
    """Raised when a saved definition could not be loaded by the user manager."""


def content_revision(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_unit_content(content: str) -> bytes:
    """Validate cheap invariants before invoking systemd's own verifier."""
    try:
        encoded = content.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise UnitContentError("The service file must be valid UTF-8 text.") from error
    if not encoded:
        raise UnitContentError("The service file must not be empty.")
    if len(encoded) > MAX_UNIT_FILE_BYTES:
        raise UnitContentError("The service file exceeds the 256 KiB size limit.")
    if "\x00" in content:
        raise UnitContentError("The service file must not contain NUL characters.")

    sections: set[str] = set()
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
                raise UnitContentError(f"Invalid section header on line {number}.")
            sections.add(section)
        elif "=" not in raw_line:
            raise UnitContentError(f"Expected a directive on line {number}.")
        continuation = raw_line.rstrip().endswith("\\")
    if continuation:
        raise UnitContentError("The final line has an unfinished continuation.")
    if "Service" not in sections:
        raise UnitContentError("A [Service] section is required.")
    return encoded


@dataclass(frozen=True, slots=True)
class UnitFileSnapshot:
    unit_id: UnitId
    content: str
    revision: str


@dataclass(frozen=True, slots=True)
class PreparedUnitChange:
    unit_id: UnitId
    content: str
    expected_revision: str | None
    creating: bool
    verification_details: str
