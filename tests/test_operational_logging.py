from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import engine.operational_logging as operational_logging
import engine.paths as paths
from engine.application_controller import NPSApplicationController
from engine.session_manager import SessionManager
from engine.weekly_preflight import WeeklyPreflightError


class OperationalLoggingTest(unittest.TestCase):
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
        importlib.reload(operational_logging)

    def test_prod_application_error_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)

            with patch(
                "engine.operational_logging.data_path",
                side_effect=lambda *parts: root / Path(*parts),
            ):
                operational_logging.persist_application_error(
                    environment="PRODUCTION",
                    component="unit",
                    operation="prod_error",
                    error=RuntimeError("prod failure"),
                )

            log_path = (
                root
                / "logs"
                / "application_errors.jsonl"
            )
            self.assertTrue(log_path.exists())

    def test_test_source_application_error_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)

            with patch(
                "engine.operational_logging.test_data_path",
                side_effect=lambda *parts: root
                / "tests"
                / Path(*parts),
            ):
                operational_logging.persist_application_error(
                    environment="TEST",
                    component="unit",
                    operation="test_error",
                    error=RuntimeError("test failure"),
                )

            log_path = (
                root
                / "tests"
                / "logs"
                / "application_errors.jsonl"
            )
            self.assertTrue(log_path.exists())

    def test_test_frozen_application_error_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            data_root = root / "data"

            sys.frozen = True
            sys._MEIPASS = str(root / "_MEI")
            sys.executable = str(root / "app" / "NPS.exe")

            with patch.dict(
                os.environ,
                {paths.DATA_ROOT_ENV_VAR: str(data_root)},
            ):
                importlib.reload(paths)
                importlib.reload(operational_logging)

                operational_logging.persist_application_error(
                    environment="TEST",
                    component="unit",
                    operation="frozen_test_error",
                    error=RuntimeError("frozen test failure"),
                )

            log_path = (
                data_root
                / "test_data"
                / "logs"
                / "application_errors.jsonl"
            )
            self.assertTrue(log_path.exists())
            self.assertNotIn(
                str(root / "_MEI"),
                str(log_path),
            )

    def test_traceback_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)

            with patch(
                "engine.operational_logging.data_path",
                side_effect=lambda *parts: root / Path(*parts),
            ):
                try:
                    raise ValueError("trace me")
                except ValueError as exc:
                    operational_logging.persist_application_error(
                        environment="PRODUCTION",
                        component="unit",
                        operation="traceback",
                        error=exc,
                    )

            log_path = (
                root
                / "logs"
                / "application_errors.jsonl"
            )
            record = json.loads(
                log_path.read_text(encoding="utf-8").splitlines()[0]
            )

            self.assertEqual(record["error_type"], "ValueError")
            self.assertIn("ValueError: trace me", record["traceback"])

    def test_failed_logger_does_not_crash_handler(self) -> None:
        with patch(
            "engine.operational_logging.operational_log_root",
            side_effect=OSError("log root unavailable"),
        ):
            operational_logging.persist_application_error(
                environment="PRODUCTION",
                component="unit",
                operation="swallowed",
                error=RuntimeError("original"),
            )

    def test_ready_preflight_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            result = self._run_controller_preflight(
                root=Path(temp_root),
                status="READY_TO_PROCESS",
                issues=[],
            )

            self.assertTrue(result.success)
            files = list(
                (
                    Path(temp_root)
                    / "tests"
                    / "logs"
                    / "preflight"
                ).glob("*READY_TO_PROCESS.json")
            )
            self.assertEqual(len(files), 1)

            record = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "READY_TO_PROCESS")
            self.assertEqual(record["environment"], "TEST")

    def test_blocked_preflight_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            result = self._run_controller_preflight(
                root=Path(temp_root),
                status="BLOCKED",
                issues=["Missing required source: Brazil upcoming"],
            )

            self.assertFalse(result.success)
            files = list(
                (
                    Path(temp_root)
                    / "tests"
                    / "logs"
                    / "preflight"
                ).glob("*BLOCKED.json")
            )
            self.assertEqual(len(files), 1)

            record = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "BLOCKED")
            self.assertEqual(
                record["issues"],
                ["Missing required source: Brazil upcoming"],
            )

    def test_failed_preflight_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            session_manager = SessionManager(
                session_file=root / "current_session.json"
            )
            controller = NPSApplicationController(
                session_manager=session_manager
            )

            with (
                patch(
                    "engine.application_controller."
                    "run_weekly_preflight",
                    side_effect=WeeklyPreflightError(
                        "Input directory does not exist"
                    ),
                ),
                patch(
                    "engine.operational_logging.test_data_path",
                    side_effect=lambda *parts: root
                    / "tests"
                    / Path(*parts),
                ),
            ):
                result = controller.run_preflight(
                    reference_date="8/3/2026",
                    test_mode=True,
                )

            self.assertFalse(result.success)
            self.assertEqual(result.status, "FAILED")

            files = list(
                (
                    root
                    / "tests"
                    / "logs"
                    / "preflight"
                ).glob("*FAILED.json")
            )
            self.assertEqual(len(files), 1)

            record = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "FAILED")
            self.assertEqual(
                record["issues"],
                ["Input directory does not exist"],
            )

    def test_test_and_prod_preflight_logs_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)

            with (
                patch(
                    "engine.operational_logging.data_path",
                    side_effect=lambda *parts: root
                    / "prod"
                    / Path(*parts),
                ),
                patch(
                    "engine.operational_logging.test_data_path",
                    side_effect=lambda *parts: root
                    / "test_data"
                    / Path(*parts),
                ),
            ):
                operational_logging.persist_preflight_result(
                    self._fake_preflight(
                        environment="PRODUCTION",
                        status="READY_TO_PROCESS",
                        issues=[],
                    )
                )
                operational_logging.persist_preflight_result(
                    self._fake_preflight(
                        environment="TEST",
                        status="BLOCKED",
                        issues=["blocked"],
                    )
                )

            self.assertTrue(
                (
                    root
                    / "prod"
                    / "logs"
                    / "preflight"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "test_data"
                    / "logs"
                    / "preflight"
                ).exists()
            )
            self.assertFalse(
                (
                    root
                    / "prod"
                    / "logs"
                    / "preflight"
                    / "test_data"
                ).exists()
            )

    def test_existing_session_behavior_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            result = self._run_controller_preflight(
                root=root,
                status="READY_TO_PROCESS",
                issues=[],
            )

            self.assertTrue(result.success)

            session_file = root / "current_session.json"
            session = json.loads(
                session_file.read_text(encoding="utf-8")
            )

            self.assertEqual(
                session["status"],
                "READY_TO_PROCESS",
            )
            self.assertEqual(
                session["current_stage"],
                "FINISHED",
            )
            self.assertEqual(
                session["metrics"]["matched_files"],
                3,
            )

    def _run_controller_preflight(
        self,
        *,
        root: Path,
        status: str,
        issues: list[str],
    ):
        session_manager = SessionManager(
            session_file=root / "current_session.json"
        )
        controller = NPSApplicationController(
            session_manager=session_manager
        )

        with (
            patch(
                "engine.application_controller."
                "run_weekly_preflight",
                return_value=self._fake_preflight(
                    environment="TEST",
                    status=status,
                    issues=issues,
                ),
            ),
            patch(
                "engine.operational_logging.test_data_path",
                side_effect=lambda *parts: root
                / "tests"
                / Path(*parts),
            ),
        ):
            return controller.run_preflight(
                reference_date="8/3/2026",
                test_mode=True,
            )

    @staticmethod
    def _fake_preflight(
        *,
        environment: str,
        status: str,
        issues: list[str],
    ) -> dict:
        return {
            "environment": environment,
            "reference_date": "8/3/2026",
            "window_start": "8/4/2026",
            "window_end": "8/10/2026",
            "weekly_run_id": (
                "NPS_WEEK_2026-08-04_2026-08-10"
            ),
            "status": status,
            "issues": issues,
            "inventory": {
                "files_scanned": 3,
                "matched_files": 3,
                "review_files": 0,
                "unconfigured_files": 0,
                "duplicate_sources": 0,
                "missing_required_sources": 0,
                "sources": [],
            },
        }


if __name__ == "__main__":
    unittest.main(verbosity=2)
