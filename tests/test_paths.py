from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import engine.paths as paths


class PathResolutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_frozen_exists = hasattr(sys, "frozen")
        self._original_frozen = getattr(sys, "frozen", None)
        self._original_meipass_exists = hasattr(sys, "_MEIPASS")
        self._original_meipass = getattr(sys, "_MEIPASS", None)
        self._original_executable = sys.executable

    def tearDown(self) -> None:
        if self._original_frozen_exists:
            sys.frozen = self._original_frozen
        elif hasattr(sys, "frozen"):
            delattr(sys, "frozen")

        if self._original_meipass_exists:
            sys._MEIPASS = self._original_meipass
        elif hasattr(sys, "_MEIPASS"):
            delattr(sys, "_MEIPASS")

        sys.executable = self._original_executable
        importlib.reload(paths)

    def test_roots_in_source_mode_are_repository_root(self) -> None:
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(paths.DATA_ROOT_ENV_VAR, None)
            importlib.reload(paths)

            expected_root = (
                Path(__file__).resolve().parent.parent
            )

            self.assertEqual(
                paths.bundled_resource_root(),
                expected_root,
            )
            self.assertEqual(
                paths.application_root(),
                expected_root,
            )
            self.assertEqual(
                paths.data_root(),
                expected_root,
            )

    def test_frozen_mode_uses_meipass_for_bundled_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            temp_path = Path(temp_root)
            meipass = temp_path / "bundle"
            executable = temp_path / "dist" / "NPS.exe"

            sys.frozen = True
            sys._MEIPASS = str(meipass)
            sys.executable = str(executable)

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop(paths.DATA_ROOT_ENV_VAR, None)
                importlib.reload(paths)

                self.assertEqual(
                    paths.bundled_resource_root(),
                    meipass.resolve(),
                )
                self.assertEqual(
                    paths.application_root(),
                    executable.resolve().parent,
                )

    def test_frozen_application_root_is_next_to_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            executable = Path(temp_root) / "NPS.exe"

            sys.frozen = True
            sys._MEIPASS = str(Path(temp_root) / "_MEI")
            sys.executable = str(executable)
            importlib.reload(paths)

            self.assertEqual(
                paths.application_root(),
                executable.resolve().parent,
            )

    def test_frozen_data_root_defaults_outside_meipass(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            meipass = root / "_MEI"
            executable = root / "app" / "NPS.exe"

            sys.frozen = True
            sys._MEIPASS = str(meipass)
            sys.executable = str(executable)

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop(paths.DATA_ROOT_ENV_VAR, None)
                importlib.reload(paths)

                self.assertEqual(
                    paths.data_root(),
                    executable.resolve().parent,
                )
                self.assertNotEqual(
                    paths.data_root(),
                    paths.bundled_resource_root(),
                )

    def test_data_root_override_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            override = Path(temp_root) / "data"

            with patch.dict(
                os.environ,
                {paths.DATA_ROOT_ENV_VAR: str(override)},
            ):
                importlib.reload(paths)

                self.assertEqual(
                    paths.data_root(),
                    override.resolve(),
                )

    def test_config_resolves_from_application_root_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            executable = Path(temp_root) / "dist" / "NPS.exe"

            sys.frozen = True
            sys._MEIPASS = str(Path(temp_root) / "_MEI")
            sys.executable = str(executable)
            importlib.reload(paths)

            self.assertEqual(
                paths.config_path("system_config.json"),
                executable.resolve().parent
                / "config"
                / "system_config.json",
            )

    def test_test_paths_remain_isolated_in_source_mode(self) -> None:
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")

        importlib.reload(paths)

        expected_root = Path(__file__).resolve().parent.parent

        self.assertEqual(
            paths.repository_path(
                "tests",
                "input",
                "power_automate",
                "upcoming",
            ),
            expected_root
            / "tests"
            / "input"
            / "power_automate"
            / "upcoming",
        )
        self.assertEqual(
            paths.repository_path("tests", "output", "weekly_runs"),
            expected_root / "tests" / "output" / "weekly_runs",
        )

    def test_source_test_data_root_is_repository_tests(self) -> None:
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")

        importlib.reload(paths)

        expected_root = Path(__file__).resolve().parent.parent

        self.assertEqual(
            paths.test_data_root(),
            expected_root / "tests",
        )
        self.assertEqual(
            paths.test_data_path("logs"),
            expected_root / "tests" / "logs",
        )

    def test_frozen_test_data_root_is_under_data_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            meipass = root / "_MEI"
            executable = root / "app" / "NPS.exe"

            sys.frozen = True
            sys._MEIPASS = str(meipass)
            sys.executable = str(executable)

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop(paths.DATA_ROOT_ENV_VAR, None)
                importlib.reload(paths)

                self.assertEqual(
                    paths.test_data_root(),
                    executable.resolve().parent / "test_data",
                )
                self.assertNotEqual(
                    paths.test_data_root(),
                    paths.data_root(),
                )
                self.assertNotEqual(
                    paths.test_data_root(),
                    paths.bundled_resource_root(),
                )

    def test_frozen_test_output_does_not_enter_prod_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)

            sys.frozen = True
            sys._MEIPASS = str(root / "_MEI")
            sys.executable = str(root / "app" / "NPS.exe")
            importlib.reload(paths)

            self.assertEqual(
                paths.data_path("output", "weekly_runs"),
                (root / "app" / "output" / "weekly_runs").resolve(),
            )
            self.assertEqual(
                paths.test_data_path("output", "weekly_runs"),
                (
                    root
                / "app"
                / "test_data"
                / "output"
                    / "weekly_runs"
                ).resolve(),
            )
            self.assertNotEqual(
                paths.test_data_path("output", "weekly_runs"),
                paths.data_path("output", "weekly_runs"),
            )

    def test_frozen_test_logs_and_runtime_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)

            sys.frozen = True
            sys._MEIPASS = str(root / "_MEI")
            sys.executable = str(root / "app" / "NPS.exe")
            importlib.reload(paths)

            self.assertEqual(
                paths.test_data_path("logs"),
                (root / "app" / "test_data" / "logs").resolve(),
            )
            self.assertEqual(
                paths.test_data_path("runtime"),
                (root / "app" / "test_data" / "runtime").resolve(),
            )
            self.assertNotEqual(
                paths.test_data_path("logs"),
                paths.data_path("logs"),
            )
            self.assertNotEqual(
                paths.test_data_path("runtime"),
                paths.data_path("runtime"),
            )

    def test_system_config_test_resolves_externally_in_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            executable = root / "app" / "NPS.exe"

            sys.frozen = True
            sys._MEIPASS = str(root / "_MEI")
            sys.executable = str(executable)
            importlib.reload(paths)

            self.assertEqual(
                paths.config_path("system_config_test.json"),
                executable.resolve().parent
                / "config"
                / "system_config_test.json",
            )

    def test_test_configured_paths_map_to_test_data_in_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)

            sys.frozen = True
            sys._MEIPASS = str(root / "_MEI")
            sys.executable = str(root / "app" / "NPS.exe")
            importlib.reload(paths)

            self.assertEqual(
                paths.resolve_configured_operational_path(
                    "tests/output/runs",
                    environment="TEST",
                ),
                (
                    root
                    / "app"
                    / "test_data"
                    / "output"
                    / "runs"
                ).resolve(),
            )
            self.assertEqual(
                paths.resolve_configured_operational_path(
                    "tests/logs",
                    environment="TEST",
                ),
                (root / "app" / "test_data" / "logs").resolve(),
            )
            self.assertEqual(
                paths.resolve_configured_operational_path(
                    "tests/runtime/weekly_pipeline/processing",
                    environment="TEST",
                ),
                (
                    root
                    / "app"
                    / "test_data"
                    / "runtime"
                    / "weekly_pipeline"
                    / "processing"
                ).resolve(),
            )

    def test_data_root_override_preserves_test_prod_separation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            override = root / "external_data"

            sys.frozen = True
            sys._MEIPASS = str(root / "_MEI")
            sys.executable = str(root / "app" / "NPS.exe")

            with patch.dict(
                os.environ,
                {paths.DATA_ROOT_ENV_VAR: str(override)},
            ):
                importlib.reload(paths)

                self.assertEqual(
                    paths.data_root(),
                    override.resolve(),
                )
                self.assertEqual(
                    paths.test_data_root(),
                    override.resolve() / "test_data",
                )
                self.assertNotEqual(
                    paths.test_data_path("output"),
                    paths.data_path("output"),
                )
                self.assertNotEqual(
                    paths.test_data_root(),
                    paths.bundled_resource_root(),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
