"""Smoke test: the V2 package imports without desktop-only dependencies."""

from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DESKTOP_ONLY_MODULES = ("PySide6", "bs4", "openpyxl")


class PackageImportTest(unittest.TestCase):
    def test_package_exposes_version(self) -> None:
        import nps_v2

        self.assertRegex(nps_v2.__version__, r"^\d+\.\d+\.\d+$")

    def test_import_does_not_load_desktop_dependencies(self) -> None:
        # A fresh interpreter: other tests in the same process may import PySide6.
        probe = (
            "import sys, nps_v2; "
            f"print(','.join(m for m in {DESKTOP_ONLY_MODULES!r} if m in sys.modules))"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "")


class SyntaxCompatibilityTest(unittest.TestCase):
    """V2 runs on the Claude runtime (3.13 today): no syntax newer than 3.12."""

    def test_sources_parse_as_python_3_12(self) -> None:
        sources = sorted(
            path
            for folder in ("nps_v2", "tests/v2")
            for path in (REPOSITORY_ROOT / folder).rglob("*.py")
        )
        self.assertTrue(sources)
        for path in sources:
            with self.subTest(path=path.relative_to(REPOSITORY_ROOT).as_posix()):
                ast.parse(
                    path.read_text(encoding="utf-8"),
                    filename=str(path),
                    feature_version=(3, 12),
                )


if __name__ == "__main__":
    unittest.main()
