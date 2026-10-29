"""NPS-001 publication contract, successful controls and stale-output safety."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from dataclasses import replace

from app.controllers.ui_controller import UIController
from engine.application_controller import NPSApplicationController
from engine.process_weekly_run import execute_weekly_end_to_end
from engine.session_manager import SessionManager
from tests.support.weekly_cases import IsolatedWeeklyCase, read_json


class FailedWeeklyStatusTest(IsolatedWeeklyCase):
    def setUp(self) -> None:
        super().setUp()
        self.manager = SessionManager(session_file=self.root / "session.json")
        self.controller = NPSApplicationController(session_manager=self.manager)
        self.ui = UIController(self.controller)

    def run_bundle(self, bundle: str):
        self.populate(bundle)
        with redirect_stdout(io.StringIO()):
            return self.controller.run_weekly_process("8/3/2026", test_mode=True)

    def test_failed_source_is_not_success(self) -> None:
        result = self.run_bundle("partial_failure")
        self.assertFalse(result.success, "Failed Brazil source reported as success")
        self.assertEqual(result.status, "FAILED")
        session = self.manager.load()
        assert session is not None
        self.assertEqual(session.status, "FAILED")
        self.assertEqual(session.issues, result.issues)
        self.assertEqual(session.outputs, {})

    def test_failure_issues_identify_source_and_counts(self) -> None:
        result = self.run_bundle("partial_failure")
        issues = " | ".join(result.issues)
        for detail in (
            "upcoming_brazil",
            "Brazil",
            "malformed_Brazil_no_table.eml",
            "ValueError",
            "processed=2",
            "failed=1",
        ):
            with self.subTest(detail=detail):
                self.assertIn(detail, issues)
        manifest = read_json(next(self.output.glob("*/weekly_manifest.json")))
        self.assertIn(
            manifest["expected_sources"][1]["processing_error"]["message"], issues
        )

    def test_pipeline_withholds_all_regional_outputs(self) -> None:
        self.populate("partial_failure")
        with redirect_stdout(io.StringIO()):
            try:
                execute_weekly_end_to_end("8/3/2026", test_mode=True)
            except Exception:
                pass  # Inspect persisted behavior even if the pipeline raises.
        manifest_path = next(self.output.glob("*/weekly_manifest.json"))
        self.assertEqual(
            [p.name for p in manifest_path.parent.iterdir()],
            ["weekly_manifest.json"],
            "Failed week published regional artifacts",
        )
        self.assertEqual(len(list((self.root / "runs").iterdir())), 3)
        self.assertEqual(len(list((self.root / "error").glob("*.eml"))), 1)

    def test_all_success_control(self) -> None:
        result = self.run_bundle("complete_weekly")
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.issues, [])
        self.assertEqual(
            result.data["processing"]["weekly_summary"]["ready_records"], 6
        )
        self.assertTrue(self.ui.get_weekly_output_state().html_content)

    def test_all_processed_manual_review_control(self) -> None:
        result = self.run_bundle("review_and_boundaries")
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.issues, [])
        self.assertGreater(
            result.data["processing"]["weekly_summary"]["review_records"], 0
        )
        self.assertTrue(self.ui.get_weekly_output_state().requires_manual_review)

    def test_failed_session_and_history_hide_stale_outputs(self) -> None:
        self.run_bundle("complete_weekly")
        session = self.manager.load()
        assert session is not None
        session.status = "FAILED"
        session.message = "Brazil source failed"
        self.manager.save(session)  # Deliberately retain previous output paths.
        state = self.ui.get_weekly_output_state()
        self.assertEqual(
            state.html_content, "", "Failed session exposes stale Slack copy"
        )
        self.assertEqual(
            (state.html_path, state.excel_path, state.manual_review_path), ("", "", "")
        )
        run_dir = next(self.output.iterdir())
        run = self.ui._read_run_history_item(run_directory=run_dir, environment="TEST")
        assert run is not None
        failed_run = replace(run, status="FAILED")
        historical = self.ui.get_weekly_output_state_for_run(failed_run)
        self.assertEqual(historical.html_content, "")
        self.assertEqual((historical.html_path, historical.excel_path), ("", ""))
