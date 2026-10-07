from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


def load_packaging_module(name: str):
    packaging_root = (
        Path(__file__).resolve().parent.parent
        / "packaging"
    )
    module_path = packaging_root / f"{name}.py"
    if str(packaging_root) not in sys.path:
        sys.path.insert(0, str(packaging_root))
    spec = importlib.util.spec_from_file_location(
        name,
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


validate_release = load_packaging_module("validate_release")
build_release = load_packaging_module("build_release")


class PackagingReleaseTest(unittest.TestCase):
    def test_approved_config_allowlist_is_exact(self) -> None:
        self.assertEqual(
            validate_release.APPROVED_CONFIG_FILES,
            (
                "business_rules.json",
                "operational_output.json",
                "report_detection.json",
                "report_sources.json",
                "system_config.json",
                "system_config_test.json",
                "weekly_schedule.json",
            ),
        )

    def test_expected_directory_lists_are_exact(self) -> None:
        self.assertIn(
            Path("input") / "upcoming",
            validate_release.REQUIRED_PROD_DIRECTORIES,
        )
        self.assertIn(
            Path("runtime") / "sessions",
            validate_release.REQUIRED_PROD_DIRECTORIES,
        )
        self.assertIn(
            Path("test_data")
            / "input"
            / "power_automate"
            / "upcoming",
            validate_release.REQUIRED_TEST_DIRECTORIES,
        )
        self.assertNotIn(
            Path("tests"),
            validate_release.REQUIRED_TEST_DIRECTORIES,
        )

    def test_release_exclusion_detection_ignores_internal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            release = (
                root
                / validate_release.RELEASE_ROOT_RELATIVE
            )
            self._create_minimal_release(release)

            forbidden = release / "tests"
            forbidden.mkdir()

            internal_py = (
                release
                / "_internal"
                / "legitimate_internal.py"
            )
            internal_py.write_text(
                "print('internal')",
                encoding="utf-8",
            )

            errors = validate_release.validate_release(root)

            self.assertTrue(
                any(
                    "Forbidden directory" in error
                    and "tests" in error
                    for error in errors
                )
            )
            self.assertFalse(
                any(
                    "legitimate_internal.py" in error
                    for error in errors
                )
            )

    def test_validator_detects_old_operational_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            release = (
                root
                / validate_release.RELEASE_ROOT_RELATIVE
            )
            self._create_minimal_release(release)

            old_output = (
                release
                / "output"
                / "weekly_runs"
                / "old.json"
            )
            old_output.write_text("{}", encoding="utf-8")

            errors = validate_release.validate_release(root)

            self.assertTrue(
                any(
                    "Unexpected operational data file" in error
                    and "old.json" in error
                    for error in errors
                )
            )

    def test_safe_cleanup_removes_only_packaging_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            (root / "build").mkdir()
            (root / "dist").mkdir()
            (root / "config").mkdir()
            (root / "input").mkdir()
            (root / "BTS SELAM NPS Operations Center.spec").write_text(
                "# temporary",
                encoding="utf-8",
            )

            build_release.clean_packaging_artifacts(root)

            self.assertFalse((root / "build").exists())
            self.assertFalse((root / "dist").exists())
            self.assertFalse(
                (
                    root
                    / "BTS SELAM NPS Operations Center.spec"
                ).exists()
            )
            self.assertTrue((root / "config").exists())
            self.assertTrue((root / "input").exists())

    def test_safe_cleanup_refuses_unexpected_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            target = root / "output"
            target.mkdir()

            with self.assertRaises(RuntimeError):
                build_release._remove_packaging_directory(
                    root,
                    target,
                )

    def test_pyinstaller_uses_current_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)

            with patch(
                "build_release.subprocess.run",
            ) as run:
                run.return_value.returncode = 0

                build_release.run_pyinstaller(root)

            command = run.call_args.args[0]
            self.assertEqual(command[0], build_release.sys.executable)
            self.assertEqual(command[1:3], ["-m", "PyInstaller"])
            self.assertIn("--onedir", command)
            self.assertIn("--windowed", command)

    def _create_minimal_release(
        self,
        release: Path,
    ) -> None:
        release.mkdir(parents=True)
        (release / "_internal").mkdir()
        (
            release
            / f"{validate_release.PRODUCT_NAME}.exe"
        ).write_text("", encoding="utf-8")
        config_root = release / "config"
        config_root.mkdir()

        for config_name in validate_release.APPROVED_CONFIG_FILES:
            (config_root / config_name).write_text(
                "{}",
                encoding="utf-8",
            )

        for directory in (
            validate_release.REQUIRED_PROD_DIRECTORIES
            + validate_release.REQUIRED_TEST_DIRECTORIES
        ):
            (release / directory).mkdir(parents=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
