from __future__ import annotations

import ast
from pathlib import Path
import re
import tomllib
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PRESENTATION = ROOT / "src/user_service_manager/presentation/application.py"
JAPANESE_PO = ROOT / "po/ja.po"
SCHEMA = ROOT / "data/io.github.NBE03xxx.UserServiceManager.gschema.xml"
METAINFO = ROOT / "data/io.github.NBE03xxx.UserServiceManager.metainfo.xml"
REQUIREMENTS = ROOT / "docs/REQUIREMENTS.md"
TEST_PLAN = ROOT / "docs/TEST_PLAN.md"
INSTALLED_LAUNCHER = ROOT / "src/user-service-manager.in"
MESON = ROOT / "meson.build"
PACKAGE_INIT = ROOT / "src/user_service_manager/__init__.py"
DEBIAN_CHANGELOG = ROOT / "debian/changelog"


class ProjectContractTests(unittest.TestCase):
    def test_presentation_does_not_reference_systemd_or_journal_commands(self) -> None:
        source = PRESENTATION.read_text(encoding="utf-8")
        for forbidden in (
            "org.freedesktop.systemd1",
            "systemctl",
            "journalctl",
            "python-systemd",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_all_presentation_gettext_strings_have_japanese_entries(self) -> None:
        tree = ast.parse(PRESENTATION.read_text(encoding="utf-8"))
        expected = {
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        }
        po_text = JAPANESE_PO.read_text(encoding="utf-8")
        actual = set(re.findall(r'^msgid "(.*)"$', po_text, re.MULTILINE))
        self.assertEqual(expected - {""}, actual - {""})

    def test_schema_has_required_appearance_choices(self) -> None:
        root = ET.parse(SCHEMA).getroot()
        key = root.find(".//key[@name='appearance']")
        self.assertIsNotNone(key)
        choices = {choice.attrib["value"] for choice in key.findall("./choices/choice")}
        self.assertEqual(choices, {"system", "light", "dark"})
        self.assertEqual(key.findtext("default"), "'system'")

    def test_registered_units_setting_is_string_array(self) -> None:
        root = ET.parse(SCHEMA).getroot()
        key = root.find(".//key[@name='registered-units']")
        self.assertIsNotNone(key)
        self.assertEqual(key.attrib["type"], "as")

    def test_every_requirement_id_is_present_in_traceability_table(self) -> None:
        pattern = re.compile(r"\b(?:FR|SEC|UI|NFR|I18N|EXT)-[0-9]{3}\b")
        requirement_ids = set(pattern.findall(REQUIREMENTS.read_text(encoding="utf-8")))
        traced_ids = set(pattern.findall(TEST_PLAN.read_text(encoding="utf-8")))
        self.assertEqual(requirement_ids, traced_ids)

    def test_installed_launcher_enables_the_production_backend(self) -> None:
        source = INSTALLED_LAUNCHER.read_text(encoding="utf-8")
        self.assertIn('os.environ.setdefault("USM_BACKEND", "systemd")', source)
        self.assertIn('os.environ.setdefault("USM_COMMANDS", "enabled")', source)

    def test_release_metadata_has_mit_license_and_homepage(self) -> None:
        root = ET.parse(METAINFO).getroot()
        self.assertEqual(root.findtext("id"), "io.github.NBE03xxx.UserServiceManager")
        self.assertEqual(root.findtext("project_license"), "MIT")
        homepage = root.find("url[@type='homepage']")
        self.assertIsNotNone(homepage)
        self.assertEqual(
            homepage.text,
            "https://github.com/NBE03xxx/UserService-Manager",
        )

    def test_release_version_is_consistently_1_2_0(self) -> None:
        version = "1.2.0"
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["version"], version)
        self.assertIn(f"version: '{version}'", MESON.read_text(encoding="utf-8"))
        self.assertIn(f'__version__ = "{version}"', PACKAGE_INIT.read_text(encoding="utf-8"))
        self.assertTrue(DEBIAN_CHANGELOG.read_text(encoding="utf-8").startswith(
            f"user-service-manager ({version})"
        ))
        release = ET.parse(METAINFO).getroot().find(
            f".//release[@version='{version}']"
        )
        self.assertIsNotNone(release)

    def test_v1_1_0_is_documented_as_skipped(self) -> None:
        self.assertIn("v1.1.0", (ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8"))
        self.assertNotIn("version=\"1.1.0\"", METAINFO.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
