"""Domain values used while discovering service units."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from user_service_manager.domain.models import ActiveState, LoadState, UnitId


class ResolutionState(StrEnum):
    RESOLVED = "resolved"
    MISSING = "missing"
    CIRCULAR = "circular"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class UnitFileCandidate:
    unit_id: UnitId
    entry_path: Path
    resolved_path: Path | None
    resolution_state: ResolutionState
    resolution_error: str | None = None

    @property
    def is_symlink(self) -> bool:
        return self.entry_path.is_symlink()


@dataclass(frozen=True, slots=True)
class UnitSnapshot:
    unit_id: UnitId
    description: str
    load_state: LoadState
    active_state: ActiveState
    sub_state: str
    unit_file_state: str
    fragment_path: str | None
    exec_commands: tuple[tuple[str, ...], ...] = ()
    working_directory: str | None = None
    environment_files: tuple[str, ...] = ()
    diagnostic_details: str | None = None


@dataclass(frozen=True, slots=True)
class PathAssessment:
    fragment_allowed: bool
    conclusive: bool
    reasons: tuple[str, ...]
