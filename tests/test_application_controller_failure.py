from __future__ import annotations

import unittest
from unittest.mock import patch

from engine.application_controller import (
    NPSApplicationController,
)
from engine.process_weekly_run import (
    WeeklyEndToEndError,
)


class ApplicationControllerFailureTest(unittest.TestCase):
    """
    Validate that the application controller reports a safe,
    structured failure when the weekly pipeline cannot complete.
    """

    def setUp(self) -> None:
        self.controller = NPSApplicationController()

    def test_processing_failure_is_returned_safely(self) -> None:
        """
        The preflight succeeds, but the weekly pipeline fails.

        The controller must:
        - return success=False;
        - return status=FAILED;
        - preserve the preflight result;
        - expose a readable issue;
        - avoid propagating the exception to the caller.
        """
        fake_preflight = {
            "environment": "TEST",
            "reference_date": "8/3/2026",
            "window_start": "8/4/2026",
            "window_end": "8/10/2026",
            "weekly_run_id": (
                "NPS_WEEK_2026-08-04_2026-08-10"
            ),
            "source_group": "weekly_upcoming",
            "input_directory": "temporary/input",
            "output_root": "temporary/output",
            "expected_run_directory": (
                "temporary/output/"
                "NPS_WEEK_2026-08-04_2026-08-10"
            ),
            "allow_partial_run": False,
            "status": "READY_TO_PROCESS",
            "issues": [],
            "inventory": {
                "files_scanned": 3,
                "matched_files": 3,
                "known_out_of_scope_files": 0,
                "review_files": 0,
                "unconfigured_files": 0,
                "duplicate_sources": 0,
                "missing_required_sources": 0,
                "sources": [],
                "items": [],
            },
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
                side_effect=WeeklyEndToEndError(
                    "Controlled weekly processing failure."
                ),
            ),
        ):
            result = self.controller.run_weekly_process(
                reference_date="8/3/2026",
                test_mode=True,
            )

        self.assertFalse(result.success)

        self.assertEqual(
            result.operation,
            "WEEKLY_PROCESS",
        )

        self.assertEqual(
            result.status,
            "FAILED",
        )

        self.assertEqual(
            result.environment,
            "TEST",
        )

        self.assertEqual(
            result.message,
            "Controlled weekly processing failure.",
        )

        self.assertTrue(
            any(
                "Controlled weekly processing failure."
                in issue
                for issue in result.issues
            )
        )

        self.assertIn(
            "preflight",
            result.data,
        )

        self.assertEqual(
            result.data["preflight"]["status"],
            "READY_TO_PROCESS",
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2,
    )