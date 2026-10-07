from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engine.application_controller import (
    NPSApplicationController,
)
from engine.session_manager import (
    SessionManager,
)


class ControllerSessionIntegrationTest(
    unittest.TestCase
):
    """
    Validate automatic session updates from the controller.
    """

    def setUp(self) -> None:
        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        session_file = (
            Path(self.temp_directory.name)
            / "current_session.json"
        )

        self.session_manager = SessionManager(
            session_file=session_file
        )

        self.controller = NPSApplicationController(
            session_manager=self.session_manager
        )

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
            "weekly_run_id": (
                "NPS_WEEK_2026-08-04_2026-08-10"
            ),
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
            "engine.application_controller."
            "run_weekly_preflight",
            return_value=fake_preflight,
        ):
            result = self.controller.run_preflight(
                reference_date="8/3/2026",
                test_mode=True,
            )

        session = (
            self.controller.get_current_session("TEST")
        )

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
            "weekly_run_id": (
                "NPS_WEEK_2026-08-04_2026-08-10"
            ),
            "status": "BLOCKED",
            "issues": [
                "Missing required source: Brazil upcoming"
            ],
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
            "engine.application_controller."
            "run_weekly_preflight",
            return_value=fake_preflight,
        ):
            result = (
                self.controller.run_weekly_process(
                    reference_date="8/3/2026",
                    test_mode=True,
                )
            )

        session = (
            self.controller.get_current_session("TEST")
        )

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
            "weekly_run_id": (
                "NPS_WEEK_2026-08-04_2026-08-10"
            ),
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
            "weekly_excel_path": (
                "output/report.xlsx"
            ),
            "slack_canvas_path": (
                "output/report.html"
            ),
            "csv_path": "output/report.csv",
            "manual_review_csv_path": (
                "output/review.csv"
            ),
            "summary_path": (
                "output/summary.json"
            ),
            "manifest_path": (
                "output/manifest.json"
            ),
        }

        with (
            patch(
                "engine.application_controller."
                "run_weekly_preflight",
                return_value=fake_preflight,
            ),
            patch(
                "engine.application_controller."
                "execute_weekly_end_to_end",
                return_value=fake_processing,
            ),
        ):
            result = (
                self.controller.run_weekly_process(
                    reference_date="8/3/2026",
                    test_mode=True,
                )
            )

        session = (
            self.controller.get_current_session("TEST")
        )

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
            "output\\report.xlsx",
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2,
    )
