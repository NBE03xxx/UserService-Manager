"""Backend-independent domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re


UNIT_NAME_PATTERN = re.compile(
    r"^(?:[-A-Za-z0-9:_.@]|\\x[0-9A-Fa-f]{2})+\.service$"
)


class ActiveState(StrEnum):
    ACTIVE = "active"
    RELOADING = "reloading"
    INACTIVE = "inactive"
    FAILED = "failed"
    ACTIVATING = "activating"
    DEACTIVATING = "deactivating"
    UNKNOWN = "unknown"


class LoadState(StrEnum):
    LOADED = "loaded"
    NOT_FOUND = "not-found"
    BAD_SETTING = "bad-setting"
    MASKED = "masked"
    ERROR = "error"
    UNKNOWN = "unknown"


class AccessMode(StrEnum):
    MANAGEABLE = "manageable"
    READ_ONLY = "read-only"
    UNKNOWN = "unknown"


class Capability(StrEnum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    ENABLE = "enable"
    DISABLE = "disable"
    STATUS = "status"
    LOGS = "logs"


class RegistrationState(StrEnum):
    DISCOVERED = "discovered"
    REGISTERED = "registered"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class UnitId:
    value: str

    def __post_init__(self) -> None:
        if not UNIT_NAME_PATTERN.fullmatch(self.value):
            raise ValueError(f"Invalid service unit name: {self.value!r}")


@dataclass(frozen=True, slots=True)
class UnitRecord:
    unit_id: UnitId
    description: str
    load_state: LoadState
    active_state: ActiveState
    sub_state: str
    unit_file_state: str
    fragment_path: str | None
    access_mode: AccessMode
    registration_state: RegistrationState
    capabilities: frozenset[Capability] = field(default_factory=frozenset)
    access_reasons: tuple[str, ...] = ()
    exec_commands: tuple[tuple[str, ...], ...] = ()
    working_directory: str | None = None
    environment_files: tuple[str, ...] = ()
    diagnostic_details: str | None = None

    @property
    def can_change_state(self) -> bool:
        return (
            self.access_mode is AccessMode.MANAGEABLE
            and self.registration_state is RegistrationState.REGISTERED
            and self.load_state is LoadState.LOADED
        )

    def supports(self, capability: Capability) -> bool:
        if capability in {Capability.STATUS, Capability.LOGS}:
            return capability in self.capabilities
        return self.can_change_state and capability in self.capabilities
