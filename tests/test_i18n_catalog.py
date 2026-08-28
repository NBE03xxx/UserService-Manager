from __future__ import annotations

import gettext
from pathlib import Path
import tempfile
import unittest

from tools.compile_mo import compile_catalog, read_catalog


ROOT = Path(__file__).resolve().parents[1]


class I18nCatalogTests(unittest.TestCase):
    def test_japanese_catalog_compiles_and_translates(self) -> None:
        catalog = read_catalog(ROOT / "po/ja.po")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "messages.mo"
            target.write_bytes(compile_catalog(catalog))
            with target.open("rb") as stream:
                translation = gettext.GNUTranslations(stream)
        self.assertEqual(translation.gettext("Service list"), "サービス一覧")
        self.assertEqual(
            translation.gettext("Managed: {count}").format(count=3),
            "管理対象 3件",
        )
        self.assertEqual(translation.gettext("Service logs"), "サービスログ")

    def test_catalog_preserves_format_placeholders(self) -> None:
        catalog = read_catalog(ROOT / "po/ja.po")
        for source, translated in catalog.items():
            with self.subTest(source=source):
                source_fields = {
                    part.split("}", 1)[0]
                    for part in source.split("{")[1:]
                    if "}" in part
                }
                translated_fields = {
                    part.split("}", 1)[0]
                    for part in translated.split("{")[1:]
                    if "}" in part
                }
                self.assertEqual(source_fields, translated_fields)


if __name__ == "__main__":
    unittest.main()
