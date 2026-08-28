"""Strict scanner for the configured systemd user-unit origin."""

from __future__ import annotations

import errno
from pathlib import Path

from user_service_manager.domain.discovery import ResolutionState, UnitFileCandidate
from user_service_manager.domain.models import UnitId


class UserUnitFileScanner:
    def __init__(self, origin: Path | None = None) -> None:
        self.origin = origin if origin is not None else Path.home() / ".config/systemd/user"

    def scan(self) -> tuple[UnitFileCandidate, ...]:
        if not self.origin.is_dir():
            return ()

        candidates: list[UnitFileCandidate] = []
        for entry in self.origin.iterdir():
            if entry.name.startswith(".") or not entry.name.endswith(".service"):
                continue
            if not (entry.is_file() or entry.is_symlink()):
                continue
            try:
                unit_id = UnitId(entry.name)
            except ValueError:
                continue
            candidates.append(self._candidate(unit_id, entry))

        return tuple(sorted(candidates, key=lambda candidate: candidate.unit_id.value))

    @staticmethod
    def _candidate(unit_id: UnitId, entry: Path) -> UnitFileCandidate:
        try:
            resolved = entry.resolve(strict=True)
            return UnitFileCandidate(
                unit_id,
                entry,
                resolved,
                ResolutionState.RESOLVED,
            )
        except FileNotFoundError as error:
            return UnitFileCandidate(
                unit_id,
                entry,
                None,
                ResolutionState.MISSING,
                str(error),
            )
        except OSError as error:
            state = (
                ResolutionState.CIRCULAR
                if error.errno == errno.ELOOP
                else ResolutionState.ERROR
            )
            return UnitFileCandidate(unit_id, entry, None, state, str(error))
        except RuntimeError as error:
            # pathlib reports a symlink loop as RuntimeError on some Python
            # versions instead of exposing ELOOP as OSError.
            return UnitFileCandidate(
                unit_id,
                entry,
                None,
                ResolutionState.CIRCULAR,
                str(error),
            )
