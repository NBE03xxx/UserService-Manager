"""Conservative path policy for service definitions and their references."""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import stat
import subprocess
from collections.abc import Callable

from user_service_manager.domain.discovery import (
    PathAssessment,
    ResolutionState,
    UnitFileCandidate,
    UnitSnapshot,
)


class DpkgPackageOwnership:
    """Verify that a runtime is owned by an installed Ubuntu/Debian package."""

    @staticmethod
    @lru_cache(maxsize=128)
    def owns(path: Path) -> bool:
        try:
            result = subprocess.run(
                ["dpkg-query", "-S", os.fspath(path)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0


class ServicePathPolicy:
    def __init__(
        self,
        home: Path | None = None,
        trusted_roots: tuple[Path, ...] = (),
        package_ownership: type[DpkgPackageOwnership] = DpkgPackageOwnership,
        runtime_trust: Callable[[Path, os.stat_result, bool], bool] | None = None,
    ) -> None:
        self.home = (home or Path.home()).resolve()
        self.trusted_roots = tuple(self._validated_root(path) for path in trusted_roots)
        self._package_ownership = package_ownership
        self._runtime_trust = runtime_trust or self._default_runtime_trust

    def assess(
        self, candidate: UnitFileCandidate, snapshot: UnitSnapshot
    ) -> PathAssessment:
        reasons: list[str] = []
        if candidate.resolution_state is not ResolutionState.RESOLVED:
            return PathAssessment(
                False,
                True,
                (f"Unit file resolution is {candidate.resolution_state.value}.",),
            )
        assert candidate.resolved_path is not None
        if not self._is_user_path(candidate.resolved_path):
            return PathAssessment(
                False,
                True,
                ("Unit file target is outside the allowed user directories.",),
            )

        if not snapshot.exec_commands:
            return PathAssessment(
                True,
                False,
                ("ExecStart is absent or could not be inspected.",),
            )

        conclusive = True
        allowed = True
        for command in snapshot.exec_commands:
            if not command:
                conclusive = False
                reasons.append("An ExecStart command has no arguments.")
                continue
            runtime_result = self._assess_runtime(command[0])
            allowed &= runtime_result[0]
            conclusive &= runtime_result[1]
            reasons.append(runtime_result[2])
            for argument in command[1:]:
                if self._looks_dynamic(argument):
                    allowed = False
                    conclusive = False
                    reasons.append("An ExecStart argument contains a dynamic expansion.")
                elif argument.startswith("/"):
                    result = self._assess_user_reference(Path(argument), "ExecStart argument")
                    allowed &= result[0]
                    conclusive &= result[1]
                    reasons.append(result[2])
                elif self._looks_like_relative_path(argument):
                    if (
                        snapshot.working_directory
                        and snapshot.working_directory.startswith("/")
                        and not self._looks_dynamic(snapshot.working_directory)
                    ):
                        result = self._assess_user_reference(
                            Path(snapshot.working_directory) / argument,
                            "Relative ExecStart argument",
                        )
                        allowed &= result[0]
                        conclusive &= result[1]
                        reasons.append(result[2])
                    else:
                        allowed = False
                        conclusive = False
                        reasons.append(
                            "A relative ExecStart path has no inspectable WorkingDirectory."
                        )

        if snapshot.working_directory:
            result = self._assess_user_reference(
                Path(snapshot.working_directory), "WorkingDirectory"
            )
            allowed &= result[0]
            conclusive &= result[1]
            reasons.append(result[2])
        for value in snapshot.environment_files:
            normalized = value.removeprefix("-")
            if self._looks_dynamic(normalized) or not normalized.startswith("/"):
                allowed = False
                conclusive = False
                reasons.append("An EnvironmentFile path is dynamic or not absolute.")
            else:
                result = self._assess_user_reference(Path(normalized), "EnvironmentFile")
                allowed &= result[0]
                conclusive &= result[1]
                reasons.append(result[2])

        return PathAssessment(allowed, conclusive, tuple(reasons))

    def _assess_runtime(self, value: str) -> tuple[bool, bool, str]:
        if self._looks_dynamic(value) or not value.startswith("/"):
            return False, False, "The ExecStart runtime is dynamic or not absolute."
        try:
            resolved = Path(value).resolve(strict=True)
            metadata = resolved.stat()
        except (OSError, RuntimeError):
            return False, False, "The ExecStart runtime cannot be resolved."
        if self._is_user_path(resolved):
            return True, True, "The ExecStart program is in an allowed user directory."
        packaged = self._package_ownership.owns(Path(value)) or self._package_ownership.owns(
            resolved
        )
        if self._runtime_trust(resolved, metadata, packaged):
            return True, True, "The ExecStart runtime is a trusted packaged system runtime."
        return False, True, "The ExecStart runtime is outside the trusted runtime policy."

    def _assess_user_reference(
        self, path: Path, label: str
    ) -> tuple[bool, bool, str]:
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError):
            return False, False, f"{label} cannot be resolved."
        if self._is_user_path(resolved):
            return True, True, f"{label} is in an allowed user directory."
        return False, True, f"{label} is outside the allowed user directories."

    def _is_user_path(self, path: Path) -> bool:
        return self._under(path, self.home) or any(
            self._under(path, root) for root in self.trusted_roots
        )

    def _validated_root(self, path: Path) -> Path:
        resolved = path.resolve(strict=True)
        if not resolved.is_dir() or not self._under(resolved, self.home):
            raise ValueError("Additional user roots must be existing directories inside home")
        return resolved

    @staticmethod
    def _under(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    @staticmethod
    def _looks_dynamic(value: str) -> bool:
        return "%" in value or "$" in value

    @staticmethod
    def _looks_like_relative_path(value: str) -> bool:
        return (
            "/" in value
            or value.startswith(".")
            or Path(value).suffix.lower() in {".py", ".sh", ".js", ".rb", ".pl"}
        )

    @staticmethod
    def _default_runtime_trust(
        _path: Path, metadata: os.stat_result, packaged: bool
    ) -> bool:
        unsafe_write_bits = metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        return metadata.st_uid == 0 and not unsafe_write_bits and packaged
