"""Adapter for validating staged service files with systemd itself."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

from user_service_manager.domain.editing import UnitVerificationError, validate_unit_content
from user_service_manager.domain.lifecycle import validate_drop_in_content, validate_drop_in_name
from user_service_manager.domain.models import UnitId


class SystemdAnalyzeUnitVerifier:
    def __init__(self, executable: Path = Path("/usr/bin/systemd-analyze")) -> None:
        self.executable = executable

    async def verify(self, unit_id: UnitId, content: str) -> str:
        # Application services run on the presentation worker thread.
        return self._verify_sync(unit_id, content)

    async def verify_drop_in(self, unit_id: UnitId, name: str, content: str) -> str:
        return self._verify_drop_in_sync(unit_id, name, content)

    def _verify_sync(self, unit_id: UnitId, content: str) -> str:
        encoded = validate_unit_content(content)
        if not self.executable.is_file():
            raise UnitVerificationError("systemd-analyze is not available.")
        environment = {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/bin:/bin",
        }
        for name in (
            "DBUS_SESSION_BUS_ADDRESS",
            "HOME",
            "LOGNAME",
            "USER",
            "XDG_RUNTIME_DIR",
        ):
            value = os.environ.get(name)
            if value:
                environment[name] = value
        with tempfile.TemporaryDirectory(prefix="user-service-manager-verify-") as directory:
            staged = Path(directory) / unit_id.value
            descriptor = os.open(
                staged,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
            with tempfile.TemporaryFile() as output:
                try:
                    result = subprocess.run(
                        [
                            os.fspath(self.executable),
                            "--user",
                            "--no-pager",
                            "--man=no",
                            "--generators=no",
                            "--recursive-errors=no",
                            "verify",
                            os.fspath(staged),
                        ],
                        stdin=subprocess.DEVNULL,
                        stdout=output,
                        stderr=subprocess.STDOUT,
                        check=False,
                        timeout=15,
                        env=environment,
                    )
                except (OSError, subprocess.SubprocessError) as error:
                    raise UnitVerificationError(
                        f"systemd verification could not run: {error}"
                    ) from error
                output.seek(0)
                details = output.read(65536).decode("utf-8", errors="replace").strip()
        if result.returncode != 0:
            raise UnitVerificationError(details or "systemd rejected the service file.")
        return details or "systemd-analyze verification passed."

    def _verify_drop_in_sync(self, unit_id: UnitId, name: str, content: str) -> str:
        validate_drop_in_name(name)
        encoded = validate_drop_in_content(content)
        if not self.executable.is_file():
            raise UnitVerificationError("systemd-analyze is not available.")
        environment = {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/bin:/bin",
        }
        for variable in (
            "DBUS_SESSION_BUS_ADDRESS",
            "HOME",
            "LOGNAME",
            "USER",
            "XDG_RUNTIME_DIR",
        ):
            value = os.environ.get(variable)
            if value:
                environment[variable] = value
        with tempfile.TemporaryDirectory(prefix="user-service-manager-drop-in-") as directory:
            root = Path(directory)
            staged = root / unit_id.value
            staged.write_text(
                "[Unit]\nDescription=Drop-in validation target\n\n"
                "[Service]\nType=oneshot\nExecStart=/usr/bin/true\n",
                encoding="utf-8",
            )
            drop_in_directory = root / f"{unit_id.value}.d"
            drop_in_directory.mkdir(mode=0o700)
            descriptor = os.open(
                drop_in_directory / name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
            environment["SYSTEMD_UNIT_PATH"] = os.fspath(root)
            with tempfile.TemporaryFile() as output:
                try:
                    result = subprocess.run(
                        [
                            os.fspath(self.executable),
                            "--user",
                            "--no-pager",
                            "--man=no",
                            "--generators=no",
                            "--recursive-errors=no",
                            "verify",
                            os.fspath(staged),
                        ],
                        stdin=subprocess.DEVNULL,
                        stdout=output,
                        stderr=subprocess.STDOUT,
                        check=False,
                        timeout=15,
                        env=environment,
                    )
                except (OSError, subprocess.SubprocessError) as error:
                    raise UnitVerificationError(
                        f"systemd drop-in verification could not run: {error}"
                    ) from error
                output.seek(0)
                details = output.read(65536).decode("utf-8", errors="replace").strip()
        if result.returncode != 0:
            raise UnitVerificationError(details or "systemd rejected the drop-in.")
        return details or "systemd-analyze drop-in verification passed."
