from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from engine.application_controller import (
    NPSApplicationController,
)
from engine.session_manager import (
    SessionManager,
)
from tests.support.weekly_cases import IsolatedWeeklyCase


class SyntheticControllerIntegrationTest(IsolatedWeeklyCase):
    """Real synthetic preflight and pipeline with fresh injected sessions."""

    def setUp(self) -> None:
        super().setUp()
        self.manager = SessionManager(session_file=self.root / "session.json")
        self.controller = NPSApplicationController(session_manager=self.manager)

    def test_synthetic_ready_preflight(self) -> None:
        self.populate("complete_weekly")
        result = self.controller.run_preflight("8/3/2026", test_mode=True)
        self.assertTrue(result.success)
        self.assertEqual(result.status, "READY_TO_PROCESS")
        self.assertEqual(result.data["inventory"]["matched_files"], 3)
        session = self.controller.get_current_session("TEST")
        self.assertIsNotNone(session)
        assert session is not None
        self.assertEqual(session.status, "READY_TO_PROCESS")
        self.assertEqual(session.metrics["matched_files"], 3)
        self.assertFalse(self.output.exists())

    def test_synthetic_blocked_preflight(self) -> None:
        self.populate("missing_brazil")
        result = self.controller.run_preflight("8/3/2026", test_mode=True)
        self.assertFalse(result.success)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(
            result.issues,
            [
                "Missing required source: Brazil upcoming",
                "Partial weekly runs are disabled.",
            ],
        )
        session = self.controller.get_current_session("TEST")
        assert session is not None
        self.assertEqual(session.status, "BLOCKED")
        self.assertEqual(session.metrics["missing_required_sources"], 1)
        self.assertFalse(self.output.exists())

    def test_synthetic_full_pipeline(self) -> None:
        self.populate("complete_weekly")
        with redirect_stdout(io.StringIO()):
            result = self.controller.run_weekly_process("8/3/2026", test_mode=True)
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.issues, [])
        session = self.controller.get_current_session("TEST")
        assert session is not None
        self.assertEqual(session.status, "COMPLETED")
        self.assertEqual(session.metrics["ready_records"], 6)
        self.assertEqual(session.metrics["review_records"], 0)
        for value in session.outputs.values():
            self.assertTrue(self.assert_local(value).is_file())
        self.assertEqual(list(self.pending.glob("*.eml")), [])

    def test_synthetic_partial_failure(self) -> None:
        self.populate("partial_failure")
        with redirect_stdout(io.StringIO()):
            result = self.controller.run_weekly_process("8/3/2026", test_mode=True)
        self.assertFalse(result.success, result.message)
        self.assertEqual(result.status, "FAILED")
        self.assertTrue(result.issues)
        processing = result.data["processing"]
        self.assertEqual(
            processing["manifest"]["processing_summary"]["failed_sources"], 1
        )
        self.assertNotIn("weekly_summary", processing)
        session = self.controller.get_current_session("TEST")
        assert session is not None
        self.assertEqual(session.status, "FAILED")
        self.assertEqual(session.metrics["processed_sources"], 2)
        self.assertEqual(session.metrics["failed_sources"], 1)
        self.assertEqual(session.outputs, {})


class ControllerSessionIntegrationTest(unittest.TestCase):
    """
    Validate automatic session updates from the controller.
    """

    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()

        session_file = Path(self.temp_directory.name) / "current_session.json"

        self.session_manager = SessionManager(session_file=session_file)

        self.controller = NPSApplicationController(session_manager=self.session_manager)

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_preflight_ready_updates_session(
        self,
    ) -> None:
        fake_preflight = {
            "environment": "TEST",
            "reference_date": "8/3/2026",
            "window_start": "8/4/2026",
            "window_end": "8/10/2026",
            "weekly_run_id": ("NPS_WEEK_2026-08-04_2026-08-10"),
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

        with patch(
            "engine.application_controller.run_weekly_preflight",
            return_value=fake_preflight,
        ):
            result = self.controller.run_preflight(
                reference_date="8/3/2026",
                test_mode=True,
            )

        session = self.controller.get_current_session("TEST")

        self.assertTrue(result.success)
        self.assertIsNotNone(session)
        self.assertEqual(
            session.status,
            "READY_TO_PROCESS",
        )
        self.assertEqual(
            session.current_stage,
            "FINISHED",
        )
        self.assertEqual(
            session.metrics["matched_files"],
            3,
        )

    def test_blocked_process_updates_session(
        self,
    ) -> None:
        fake_preflight = {
            "environment": "TEST",
            "reference_date": "8/3/2026",
            "window_start": "8/4/2026",
            "window_end": "8/10/2026",
            "weekly_run_id": ("NPS_WEEK_2026-08-04_2026-08-10"),
            "status": "BLOCKED",
            "issues": ["Missing required source: Brazil upcoming"],
            "inventory": {
                "files_scanned": 2,
                "matched_files": 2,
                "review_files": 0,
                "unconfigured_files": 0,
                "duplicate_sources": 0,
                "missing_required_sources": 1,
            },
        }

        with patch(
            "engine.application_controller.run_weekly_preflight",
            return_value=fake_preflight,
        ):
            result = self.controller.run_weekly_process(
                reference_date="8/3/2026",
                test_mode=True,
            )

        session = self.controller.get_current_session("TEST")

        self.assertFalse(result.success)
        self.assertEqual(
            result.status,
            "BLOCKED",
        )
        self.assertEqual(
            session.status,
            "BLOCKED",
        )
        self.assertIn(
            "Missing required source",
            session.issues[0],
        )

        self.assertEqual(
            session.weekly_run_id,
            "NPS_WEEK_2026-08-04_2026-08-10",
        )

    def test_completed_process_updates_session(
        self,
    ) -> None:
        fake_preflight = {
            "environment": "TEST",
            "reference_date": "8/3/2026",
            "window_start": "8/4/2026",
            "window_end": "8/10/2026",
            "weekly_run_id": ("NPS_WEEK_2026-08-04_2026-08-10"),
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

        fake_processing = {
            "manifest": {
                "status": "COMPLETED_WITH_REVIEW",
            },
            "weekly_summary": {
                "total_records": 21,
                "ready_records": 21,
                "review_records": 1,
                "clients": 10,
                "duplicate_issues": 0,
            },
            "weekly_excel_path": ("output/report.xlsx"),
            "slack_canvas_path": ("output/report.html"),
            "csv_path": "output/report.csv",
            "manual_review_csv_path": ("output/review.csv"),
            "summary_path": ("output/summary.json"),
            "manifest_path": ("output/manifest.json"),
        }

        with (
            patch(
                "engine.application_controller.run_weekly_preflight",
                return_value=fake_preflight,
            ),
            patch(
                "engine.application_controller.execute_weekly_end_to_end",
                return_value=fake_processing,
            ),
        ):
            result = self.controller.run_weekly_process(
                reference_date="8/3/2026",
                test_mode=True,
            )

        session = self.controller.get_current_session("TEST")

        self.assertTrue(result.success)
        self.assertEqual(
            session.status,
            "COMPLETED_WITH_REVIEW",
        )
        self.assertEqual(
            session.metrics["ready_records"],
            21,
        )
        self.assertEqual(
            session.metrics["review_records"],
            1,
        )
        self.assertEqual(
            session.outputs["excel"],
            str(Path("output") / "report.xlsx"),
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2,
    )
