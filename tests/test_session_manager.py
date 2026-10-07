from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engine.session_manager import (
    SessionManager,
)


class SessionManagerTest(unittest.TestCase):
    """
    Validate creation, persistence, update,
    completion, and reset of application sessions.
    """

    def test_session_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            session_file = (
                Path(temp_root)
                / "current_session.json"
            )

            manager = SessionManager(
                session_file=session_file
            )

            self.assertIsNone(
                manager.load()
            )

            session = manager.create(
                environment="TEST",
                operation="WEEKLY_PROCESS",
                reference_date="8/3/2026",
                weekly_run_id=(
                    "NPS_WEEK_2026-08-04_2026-08-10"
                ),
                status="PREFLIGHT_RUNNING",
                current_stage="PREFLIGHT",
                message="Weekly preflight started.",
            )

            self.assertTrue(
                session_file.exists()
            )

            loaded = manager.load()

            self.assertIsNotNone(loaded)
            self.assertEqual(
                loaded.session_id,
                session.session_id,
            )
            self.assertEqual(
                loaded.status,
                "PREFLIGHT_RUNNING",
            )

            manager.update(
                session,
                status="PROCESSING",
                current_stage="EMAIL_PARSING",
                current_source="Brazil",
                message="Processing Brazil report.",
            )

            loaded = manager.load()

            self.assertEqual(
                loaded.status,
                "PROCESSING",
            )
            self.assertEqual(
                loaded.current_stage,
                "EMAIL_PARSING",
            )
            self.assertEqual(
                loaded.current_source,
                "Brazil",
            )

            manager.finish(
                session,
                status="COMPLETED_WITH_REVIEW",
                message=(
                    "Weekly processing completed "
                    "with manual review."
                ),
                issues=[
                    "One record requires manual review."
                ],
                metrics={
                    "ready_records": 21,
                    "review_records": 1,
                    "clients": 10,
                },
                outputs={
                    "excel": "output/report.xlsx",
                    "html": "output/report.html",
                },
            )

            loaded = manager.load()

            self.assertEqual(
                loaded.status,
                "COMPLETED_WITH_REVIEW",
            )
            self.assertEqual(
                loaded.current_stage,
                "FINISHED",
            )
            self.assertTrue(
                loaded.finished_at
            )
            self.assertEqual(
                loaded.metrics["ready_records"],
                21,
            )
            self.assertEqual(
                loaded.outputs["excel"],
                "output/report.xlsx",
            )

            manager.reset()

            self.assertFalse(
                session_file.exists()
            )
            self.assertIsNone(
                manager.load()
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2,
    )