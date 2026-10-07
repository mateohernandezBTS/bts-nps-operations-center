from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from app.controllers.ui_controller import UIController
from engine.application_controller import NPSApplicationController
import engine.paths as paths


class SessionIsolationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._frozen_exists = hasattr(sys, "frozen")
        self._frozen = getattr(sys, "frozen", None)
        self._meipass_exists = hasattr(sys, "_MEIPASS")
        self._meipass = getattr(sys, "_MEIPASS", None)
        self._executable = sys.executable

    def tearDown(self) -> None:
        if self._frozen_exists:
            sys.frozen = self._frozen
        elif hasattr(sys, "frozen"):
            delattr(sys, "frozen")

        if self._meipass_exists:
            sys._MEIPASS = self._meipass
        elif hasattr(sys, "_MEIPASS"):
            delattr(sys, "_MEIPASS")

        sys.executable = self._executable
        importlib.reload(paths)

    def test_source_session_paths_are_environment_aware(self) -> None:
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(paths.DATA_ROOT_ENV_VAR, None)
            importlib.reload(paths)
            root = Path(__file__).resolve().parent.parent
            self.assertEqual(
                paths.session_file_path("PRODUCTION"),
                root / "runtime" / "sessions" / "current_session.json",
            )
            self.assertEqual(
                paths.session_file_path("TEST"),
                root / "tests" / "runtime" / "sessions" / "current_session.json",
            )

    def test_frozen_session_paths_are_environment_aware(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            sys.frozen = True
            sys._MEIPASS = str(root / "_MEI")
            sys.executable = str(root / "app" / "NPS.exe")
            importlib.reload(paths)
            self.assertEqual(
                paths.session_file_path("PRODUCTION"),
                (root / "app" / "runtime" / "sessions" / "current_session.json").resolve(),
            )
            self.assertEqual(
                paths.session_file_path("TEST"),
                (root / "app" / "test_data" / "runtime" / "sessions" / "current_session.json").resolve(),
            )

    def test_data_root_override_preserves_both_session_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            override = Path(temp_root) / "data"
            with patch.dict(os.environ, {paths.DATA_ROOT_ENV_VAR: str(override)}):
                importlib.reload(paths)
                self.assertEqual(
                    paths.session_file_path("PRODUCTION"),
                    override.resolve() / "runtime" / "sessions" / "current_session.json",
                )
                self.assertEqual(
                    paths.session_file_path("TEST"),
                    override.resolve() / "test_data" / "runtime" / "sessions" / "current_session.json",
                )

    def test_default_controller_test_preflight_creates_only_test_session(self) -> None:
        with self._default_controller() as (root, controller):
            with patch(
                "engine.application_controller.run_weekly_preflight",
                return_value=self._preflight("TEST"),
            ):
                controller.run_preflight("8/10/2026", test_mode=True)
            self.assertTrue(self._test_session(root).is_file())
            self.assertFalse(self._prod_session(root).exists())

    def test_default_controller_weekly_process_stays_in_test(self) -> None:
        with self._default_controller() as (root, controller):
            with (
                patch(
                    "engine.application_controller.run_weekly_preflight",
                    return_value=self._preflight("TEST"),
                ),
                patch(
                    "engine.application_controller.execute_weekly_end_to_end",
                    return_value=self._processing_result(),
                ),
            ):
                controller.run_weekly_process("8/10/2026", test_mode=True)
            session = controller.get_current_session("TEST")
            self.assertEqual(session.status, "COMPLETED")
            self.assertTrue(self._test_session(root).is_file())
            self.assertFalse(self._prod_session(root).exists())

    def test_production_operation_stays_in_production(self) -> None:
        with self._default_controller() as (root, controller):
            with patch(
                "engine.application_controller.run_weekly_preflight",
                return_value=self._preflight("PRODUCTION"),
            ):
                controller.run_preflight("8/10/2026", test_mode=False)
            self.assertTrue(self._prod_session(root).is_file())
            self.assertFalse(self._test_session(root).exists())

    def test_switching_both_directions_keeps_separate_sessions(self) -> None:
        with self._default_controller() as (root, controller):
            for environment, test_mode in (("TEST", True), ("PRODUCTION", False), ("TEST", True)):
                with patch(
                    "engine.application_controller.run_weekly_preflight",
                    return_value=self._preflight(environment),
                ):
                    controller.run_preflight("8/10/2026", test_mode=test_mode)
            self.assertEqual(controller.get_current_session("TEST").environment, "TEST")
            self.assertEqual(controller.get_current_session("PRODUCTION").environment, "PRODUCTION")
            self.assertTrue(self._test_session(root).is_file())
            self.assertTrue(self._prod_session(root).is_file())

    def test_reset_is_environment_isolated(self) -> None:
        with self._default_controller() as (root, controller):
            for environment, test_mode in (("TEST", True), ("PRODUCTION", False)):
                with patch(
                    "engine.application_controller.run_weekly_preflight",
                    return_value=self._preflight(environment),
                ):
                    controller.run_preflight("8/10/2026", test_mode=test_mode)
            controller.reset_current_session("TEST")
            self.assertFalse(self._test_session(root).exists())
            self.assertTrue(self._prod_session(root).exists())
            with patch(
                "engine.application_controller.run_weekly_preflight",
                return_value=self._preflight("TEST"),
            ):
                controller.run_preflight("8/10/2026", test_mode=True)
            controller.reset_current_session("PRODUCTION")
            self.assertFalse(self._prod_session(root).exists())
            self.assertTrue(self._test_session(root).exists())

    def test_ui_settings_and_dashboard_follow_selected_environment(self) -> None:
        with self._default_controller() as (root, controller):
            for environment, test_mode in (("TEST", True), ("PRODUCTION", False)):
                with patch(
                    "engine.application_controller.run_weekly_preflight",
                    return_value=self._preflight(environment),
                ):
                    controller.run_preflight("8/10/2026", test_mode=test_mode)
            ui = UIController(application_controller=controller)
            ui.set_environment("TEST")
            self.assertEqual(ui.get_dashboard_state().environment, "TEST")
            self.assertEqual(Path(ui.get_settings_state().session_file), self._test_session(root))
            ui.set_environment("PRODUCTION")
            self.assertEqual(ui.get_dashboard_state().environment, "PRODUCTION")
            self.assertEqual(Path(ui.get_settings_state().session_file), self._prod_session(root))

    def test_frozen_default_controller_test_creates_no_prod_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            sys.frozen = True
            sys._MEIPASS = str(root / "_MEI")
            sys.executable = str(root / "app" / "NPS.exe")
            importlib.reload(paths)
            controller = NPSApplicationController()
            with patch(
                "engine.application_controller.run_weekly_preflight",
                return_value=self._preflight("TEST"),
            ):
                controller.run_preflight("8/10/2026", test_mode=True)
            self.assertTrue(
                (root / "app" / "test_data" / "runtime" / "sessions" / "current_session.json").is_file()
            )
            self.assertFalse(
                (root / "app" / "runtime" / "sessions" / "current_session.json").exists()
            )

    class _ControllerContext:
        def __init__(self) -> None:
            self.temp = tempfile.TemporaryDirectory()
            self.root = Path(self.temp.name) / "data"
            self.patch = patch.dict(
                os.environ,
                {paths.DATA_ROOT_ENV_VAR: str(self.root)},
            )

        def __enter__(self):
            self.patch.start()
            return self.root.resolve(), NPSApplicationController()

        def __exit__(self, exc_type, exc, traceback):
            self.patch.stop()
            self.temp.cleanup()

    def _default_controller(self) -> _ControllerContext:
        return self._ControllerContext()

    @staticmethod
    def _prod_session(root: Path) -> Path:
        return root / "runtime" / "sessions" / "current_session.json"

    @staticmethod
    def _test_session(root: Path) -> Path:
        return root / "test_data" / "runtime" / "sessions" / "current_session.json"

    @staticmethod
    def _preflight(environment: str) -> dict:
        return {
            "environment": environment,
            "reference_date": "8/10/2026",
            "window_start": "8/11/2026",
            "window_end": "8/17/2026",
            "weekly_run_id": "NPS_WEEK_2026-08-11_2026-08-17",
            "status": "READY_TO_PROCESS",
            "issues": [],
            "inventory": {
                "files_scanned": 3,
                "matched_files": 3,
                "review_files": 0,
                "unconfigured_files": 0,
                "duplicate_sources": 0,
                "missing_required_sources": 0,
            },
        }

    @staticmethod
    def _processing_result() -> dict:
        return {
            "manifest": {"status": "COMPLETED"},
            "weekly_summary": {
                "total_records": 16,
                "ready_records": 16,
                "review_records": 1,
                "clients": 10,
                "duplicate_issues": 0,
            },
            "weekly_excel_path": "test.xlsx",
            "slack_canvas_path": "test.html",
            "csv_path": "test.csv",
            "manual_review_csv_path": "review.csv",
            "summary_path": "summary.json",
            "manifest_path": "manifest.json",
        }


if __name__ == "__main__":
    unittest.main(verbosity=2)
