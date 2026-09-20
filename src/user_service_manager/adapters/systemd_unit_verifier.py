"""Adapter for validating staged service files with systemd itself."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

from user_service_manager.domain.editing import UnitVerificationError, validate_unit_content
from user_service_manager.domain.models import UnitId


class SystemdAnalyzeUnitVerifier:
    def __init__(self, executable: Path = Path("/usr/bin/systemd-analyze")) -> None:
        self.executable = executable

    async def verify(self, unit_id: UnitId, content: str) -> str:
        # Application services run on the presentation worker thread.
        return self._verify_sync(unit_id, content)

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
