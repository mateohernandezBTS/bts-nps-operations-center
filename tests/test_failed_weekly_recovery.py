"""Owner-assisted FAILED archive and full retry, using real isolated services."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from app.controllers.ui_controller import UIController
from engine.application_controller import NPSApplicationController
from engine.session_manager import SessionManager
from engine.weekly_preflight import run_weekly_preflight
from tests.support.weekly_cases import IsolatedWeeklyCase, read_json


class FailedWeeklyRecoveryTest(IsolatedWeeklyCase):
    def test_archive_failed_attempt_full_retry_preserves_evidence(self) -> None:
        manager = SessionManager(session_file=self.root / "session.json")
        controller = NPSApplicationController(session_manager=manager)
        ui = UIController(controller)
        self.populate("partial_failure")
        with redirect_stdout(io.StringIO()):
            failed = controller.run_weekly_process("8/3/2026", test_mode=True)
        self.assertEqual(failed.status, "FAILED")
        canonical = Path(failed.data["processing"]["manifest_path"]).parent
        self.assertEqual(
            read_json(canonical / "weekly_manifest.json")["status"], "FAILED"
        )
        original_week = {p.name: p.read_bytes() for p in canonical.iterdir()}

        # Step 2: owner preserves the complete environment, including session/logs.
        evidence = {
            p.relative_to(self.root): p.read_bytes()
            for p in self.root.rglob("*")
            if p.is_file()
        }
        backup = self.root / "owner_backup"
        for relative, content in evidence.items():
            target = backup / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        archive = canonical.with_name(canonical.name + "__FAILED_attempt_1")
        self.assertFalse(archive.exists())
        canonical.rename(archive)

        # Full fresh input, including corrected Brazil, rather than failed-only resume.
        self.populate("complete_weekly")
        preflight = run_weekly_preflight("8/3/2026", test_mode=True)
        self.assertEqual(preflight["status"], "READY_TO_PROCESS")
        self.assertEqual(preflight["inventory"]["matched_files"], 3)

        def history_root(*parts: str) -> Path:
            return self.output

        # Both history roots are injected; never inspect a production installation.
        with (
            patch(
                "app.controllers.ui_controller.test_data_path", side_effect=history_root
            ),
            patch(
                "app.controllers.ui_controller.data_path",
                return_value=self.root / "unused",
            ),
        ):
            history = ui.get_run_history_state()
            self.assertEqual(len(history.runs), 1)
            self.assertEqual(history.runs[0].status, "FAILED")
            self.assertEqual(Path(history.runs[0].run_directory), archive)
            state = ui.get_weekly_output_state_for_run(history.runs[0])
            self.assertEqual(
                (state.html_content, state.html_path, state.excel_path), ("", "", "")
            )
            with redirect_stdout(io.StringIO()):
                fresh = controller.run_weekly_process("8/3/2026", test_mode=True)
            self.assertTrue(fresh.success, fresh.message)
            self.assertEqual(fresh.status, "COMPLETED")
            processing = fresh.data["processing"]
            self.assertEqual(
                processing["manifest"]["processing_summary"]["processed_sources"], 3
            )
            self.assertEqual(processing["weekly_summary"]["ready_records"], 6)
            self.assertTrue(ui.get_weekly_output_state().html_content)
            self.assertEqual(
                sorted(r.status for r in ui.get_run_history_state().runs),
                ["COMPLETED", "FAILED"],
            )

        # Completed week cannot be rerun; no overwrite or duplicate publication.
        completed = {
            p.relative_to(canonical): p.read_bytes()
            for p in canonical.rglob("*")
            if p.is_file()
        }
        with redirect_stdout(io.StringIO()):
            blocked = controller.run_weekly_process("8/3/2026", test_mode=True)
        self.assertEqual(blocked.status, "BLOCKED")
        self.assertEqual(
            completed,
            {
                p.relative_to(canonical): p.read_bytes()
                for p in canonical.rglob("*")
                if p.is_file()
            },
        )
        self.assertEqual(
            original_week, {p.name: p.read_bytes() for p in archive.iterdir()}
        )
        self.assertEqual(len(list(self.output.glob("*/*.xlsx"))), 1)
        self.assertEqual(len(list((self.root / "runs").iterdir())), 6)
        for relative, content in evidence.items():
            with self.subTest(evidence=str(relative)):
                self.assertEqual((backup / relative).read_bytes(), content)
                if relative.parts[0] in {"runs", "logs", "processed", "error"}:
                    self.assertEqual((self.root / relative).read_bytes(), content)
