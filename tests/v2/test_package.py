"""Smoke test: the V2 package imports without desktop-only dependencies."""

from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
