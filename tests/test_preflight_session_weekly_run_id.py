from __future__ import annotations

from pathlib import Path
from datetime import datetime
import tempfile
import unittest
from unittest.mock import patch

from engine.application_controller import NPSApplicationController
from engine.session_manager import SessionManager
from engine.weekly_preflight import WeeklyPreflightError, build_weekly_run_id


EXPECTED_ID = "NPS_WEEK_2026-08-11_2026-08-17"


class PreflightSessionWeeklyRunIdTest(unittest.TestCase):
    def _controller(self, root: Path) -> NPSApplicationController:
        return NPSApplicationController(
            test_session_manager=SessionManager(
                root / "test" / "current_session.json"
            ),
            production_session_manager=SessionManager(
                root / "prod" / "current_session.json"
            ),
        )

    @staticmethod
    def _preflight(environment: str, status: str = "READY_TO_PROCESS") -> dict:
        return {
            "environment": environment,
            "reference_date": "8/10/2026",
            "window_start": "8/11/2026",
            "window_end": "8/17/2026",
            "weekly_run_id": EXPECTED_ID,
            "status": status,
            "issues": [] if status == "READY_TO_PROCESS" else ["blocked"],
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
            "manifest": {"status": "COMPLETED", "weekly_run_id": EXPECTED_ID},
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

    def test_ready_preflight_persists_canonical_id_in_test_and_prod(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            controller = self._controller(Path(temp_root))
            for environment, test_mode in (("TEST", True), ("PRODUCTION", False)):
                preflight = self._preflight(environment)
                with patch(
                    "engine.application_controller.run_weekly_preflight",
                    return_value=preflight,
                ):
                    result = controller.run_preflight("8/10/2026", test_mode=test_mode)
                session = controller.get_current_session(environment)
                self.assertTrue(result.success)
                self.assertEqual(result.data["weekly_run_id"], EXPECTED_ID)
                self.assertEqual(session.weekly_run_id, EXPECTED_ID)
                self.assertEqual(session.environment, environment)
                self.assertEqual(session.reference_date, "8/10/2026")
                self.assertEqual(session.status, "READY_TO_PROCESS")
                self.assertEqual(session.operation, "PREFLIGHT")
                self.assertEqual(session.current_stage, "FINISHED")

    def test_id_matches_preflight_window(self) -> None:
        preflight = self._preflight("TEST")
        expected_from_window = build_weekly_run_id(
            datetime.strptime(preflight["window_start"], "%m/%d/%Y"),
            datetime.strptime(preflight["window_end"], "%m/%d/%Y"),
        )
        self.assertEqual(expected_from_window, EXPECTED_ID)
        self.assertEqual(preflight["weekly_run_id"], expected_from_window)

    def test_preflight_and_processing_use_exactly_the_same_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            controller = self._controller(Path(temp_root))
            preflight = self._preflight("TEST")
            with patch(
                "engine.application_controller.run_weekly_preflight",
                return_value=preflight,
            ):
                controller.run_preflight("8/10/2026", test_mode=True)
            preflight_id = controller.get_current_session("TEST").weekly_run_id
            with (
                patch(
                    "engine.application_controller.run_weekly_preflight",
                    return_value=preflight,
                ),
                patch(
                    "engine.application_controller.execute_weekly_end_to_end",
                    return_value=self._processing_result(),
                ),
            ):
                controller.run_weekly_process("8/10/2026", test_mode=True)
            processing_id = controller.get_current_session("TEST").weekly_run_id
            self.assertEqual(preflight_id, EXPECTED_ID)
            self.assertEqual(processing_id, EXPECTED_ID)
            self.assertEqual(preflight_id, processing_id)

    def test_blocked_and_failed_preflight_do_not_persist_an_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            controller = self._controller(Path(temp_root))
            with patch(
                "engine.application_controller.run_weekly_preflight",
                return_value=self._preflight("TEST", "BLOCKED"),
            ):
                blocked = controller.run_preflight("8/10/2026", test_mode=True)
            self.assertEqual(blocked.status, "BLOCKED")
            self.assertEqual(controller.get_current_session("TEST").weekly_run_id, "")
            with patch(
                "engine.application_controller.run_weekly_preflight",
                side_effect=WeeklyPreflightError("failed"),
            ):
                failed = controller.run_preflight("8/10/2026", test_mode=False)
            self.assertEqual(failed.status, "FAILED")
            self.assertEqual(
                controller.get_current_session("PRODUCTION").weekly_run_id,
                "",
            )

    def test_reset_removes_session_with_persisted_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            controller = self._controller(Path(temp_root))
            with patch(
                "engine.application_controller.run_weekly_preflight",
                return_value=self._preflight("TEST"),
            ):
                controller.run_preflight("8/10/2026", test_mode=True)
            self.assertEqual(controller.get_current_session("TEST").weekly_run_id, EXPECTED_ID)
            controller.reset_current_session("TEST")
            self.assertIsNone(controller.get_current_session("TEST"))


if __name__ == "__main__":
    unittest.main()
