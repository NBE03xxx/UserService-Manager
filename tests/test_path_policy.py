from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from user_service_manager.adapters.path_policy import ServicePathPolicy
from user_service_manager.domain.discovery import ResolutionState, UnitFileCandidate, UnitSnapshot
from user_service_manager.domain.models import ActiveState, LoadState, UnitId


class AlwaysPackaged:
    @staticmethod
    def owns(_path: Path) -> bool:
        return True


class PathPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.unit_path = self.home / ".config/systemd/user/example.service"
        self.script = self.home / "MyApp/app.py"
        self.unit_path.parent.mkdir(parents=True)
        self.script.parent.mkdir(parents=True)
        self.unit_path.write_text("unit", encoding="utf-8")
        self.script.write_text("pass", encoding="utf-8")
        self.candidate = UnitFileCandidate(
            UnitId("example.service"),
            self.unit_path,
            self.unit_path.resolve(),
            ResolutionState.RESOLVED,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def snapshot(
        self,
        command: tuple[str, ...],
        working_directory: str | None = None,
        environment_files: tuple[str, ...] = (),
    ) -> UnitSnapshot:
        return UnitSnapshot(
            UnitId("example.service"),
            "Example",
            LoadState.LOADED,
            ActiveState.INACTIVE,
            "dead",
            "disabled",
            str(self.unit_path),
            (command,),
            working_directory,
            environment_files,
        )

    def policy(self) -> ServicePathPolicy:
        return ServicePathPolicy(
            self.home,
            package_ownership=AlwaysPackaged,
            runtime_trust=lambda _path, _metadata, packaged: packaged,
        )

    def test_packaged_python_and_home_script_are_manageable(self) -> None:
        result = self.policy().assess(
            self.candidate,
            self.snapshot(("/usr/bin/python3", str(self.script))),
        )
        self.assertTrue(result.fragment_allowed)
        self.assertTrue(result.conclusive)

    def test_external_workload_is_read_only(self) -> None:
        result = self.policy().assess(
            self.candidate,
            self.snapshot(("/usr/bin/python3", "/usr/share/doc/systemd/README.Debian.gz")),
        )
        self.assertFalse(result.fragment_allowed)
        self.assertTrue(result.conclusive)

    def test_dynamic_reference_is_unknown_and_not_allowed(self) -> None:
        result = self.policy().assess(
            self.candidate,
            self.snapshot(("/usr/bin/python3", "%h/MyApp/app.py")),
        )
        self.assertFalse(result.fragment_allowed)
        self.assertFalse(result.conclusive)

    def test_environment_file_and_working_directory_are_assessed(self) -> None:
        environment = self.home / "MyApp/app.env"
        environment.write_text("NAME=value", encoding="utf-8")
        result = self.policy().assess(
            self.candidate,
            self.snapshot(
                ("/usr/bin/python3", str(self.script)),
                str(self.script.parent),
                (str(environment),),
            ),
        )
        self.assertTrue(result.fragment_allowed)
        self.assertTrue(result.conclusive)

    def test_relative_workload_is_resolved_against_working_directory(self) -> None:
        result = self.policy().assess(
            self.candidate,
            self.snapshot(
                ("/usr/bin/python3", "app.py"),
                str(self.script.parent),
            ),
        )
        self.assertTrue(result.fragment_allowed)
        self.assertTrue(
            any("Relative ExecStart argument" in reason for reason in result.reasons)
        )

        nested = self.script.parent / "app"
        nested.mkdir()
        nested_script = nested / "main.py"
        nested_script.write_text("pass", encoding="utf-8")
        result = self.policy().assess(
            self.candidate,
            self.snapshot(
                ("/usr/bin/python3", "app/main.py"),
                str(self.script.parent),
            ),
        )
        self.assertTrue(result.fragment_allowed)
        self.assertTrue(result.conclusive)
        self.assertTrue(
            any("Relative ExecStart argument" in reason for reason in result.reasons)
        )

    def test_relative_workload_without_working_directory_is_unknown(self) -> None:
        result = self.policy().assess(
            self.candidate,
            self.snapshot(("/usr/bin/python3", "app/main.py")),
        )
        self.assertFalse(result.fragment_allowed)
        self.assertFalse(result.conclusive)

    def test_additional_root_must_remain_inside_home(self) -> None:
        with self.assertRaises(ValueError):
            ServicePathPolicy(self.home, (self.root,))


if __name__ == "__main__":
    unittest.main()
