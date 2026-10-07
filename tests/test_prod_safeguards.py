from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.controllers.ui_controller import (
    DashboardState,
    RunHistoryState,
    SettingsState,
    UIActionResult,
    WeeklyOutputState,
)
from app.main_window import ApplicationShell
from app.views.weekly_run.weekly_run_view import WeeklyRunView
from engine.session_manager import SessionManager


class FakeUIController:
    def __init__(self) -> None:
        self.environment = "TEST"
        self.run_weekly_process = Mock(
            return_value=UIActionResult(
                success=True,
                operation="WEEKLY_PROCESS",
                status="COMPLETED",
                environment="TEST",
                message="Completed.",
                issues=(),
                data={},
            )
        )
        self.reset_current_session = Mock()

    def set_environment(self, environment: str) -> None:
        self.environment = environment

    def get_dashboard_state(self) -> DashboardState:
        return DashboardState(
            environment=self.environment,
            backend_status="READY",
            session_status="IDLE",
            operation="NONE",
            ready_records=0,
            review_records=0,
            total_records=0,
            sources_received=0,
            sources_expected=3,
            latest_run_status="NO RUN",
            weekly_run_id="",
            reference_date="",
            message="System ready",
            started_at="",
            updated_at="",
            finished_at="",
            issues=(),
            outputs={},
        )

    def get_weekly_output_state(self) -> WeeklyOutputState:
        return WeeklyOutputState(
            environment="TEST",
            weekly_run_id="",
            status="NO RUN",
            message="No weekly run is available.",
            html_path="",
            html_content="",
            excel_path="",
            manual_review_path="",
            manual_review_count=0,
            requires_manual_review=False,
            manual_review_items=(),
        )

    def get_run_history_state(self) -> RunHistoryState:
        return RunHistoryState(runs=())

    def get_settings_state(self) -> SettingsState:
        return SettingsState(
            application_version="1.0.2",
            environment="TEST",
            backend_status="READY",
            session_status="IDLE",
            weekly_run_id="",
            reference_date="",
            test_output_root="tests/output/weekly_runs",
            production_output_root="output/weekly_runs",
            session_directory="runtime/sessions",
            session_file="runtime/sessions/current_session.json",
        )

    def get_application_status(self) -> dict[str, str]:
        return {
            "environment": "TEST",
            "backend_status": "READY",
            "session_status": "IDLE",
            "message": "System ready",
        }


class ProdSafeguardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = (
            QApplication.instance()
            or QApplication([])
        )

    def test_initial_environment_defaults_to_test(self) -> None:
        view = WeeklyRunView()

        self.assertTrue(view.is_test_mode())
        self.assertEqual(
            view.configuration_card.environment_combo.currentText(),
            "TEST",
        )

    def test_test_weekly_process_does_not_confirm_and_continues(self) -> None:
        window = self._make_window()

        with (
            patch.object(
                window,
                "_confirm_production_weekly_process",
                return_value=True,
            ) as confirm,
            patch.object(window, "_start_operation") as start,
        ):
            window._handle_weekly_process_request(
                "8/3/2026",
                True,
            )

        confirm.assert_not_called()
        start.assert_called_once()

    def test_production_weekly_process_requires_confirmation(self) -> None:
        window = self._make_window()

        with (
            patch.object(
                window,
                "_confirm_production_weekly_process",
                return_value=False,
            ) as confirm,
            patch.object(window, "_start_operation"),
        ):
            window._handle_weekly_process_request(
                "8/3/2026",
                False,
            )

        confirm.assert_called_once()

    def test_production_confirmation_dialog_keeps_cancel_defaults(self) -> None:
        window = self._make_window()

        dialog, run_button = (
            window._build_production_confirmation_dialog(
                reference_date="8/3/2026",
                weekly_window="8/4/2026 - 8/10/2026",
            )
        )

        self.assertEqual(
            dialog.windowTitle(),
            "Run Production Weekly Process",
        )
        self.assertIn(
            "PRODUCTION",
            dialog.text(),
        )
        self.assertIn(
            "Environment: PRODUCTION",
            dialog.informativeText(),
        )
        self.assertIn(
            "Reference Monday: 8/3/2026",
            dialog.informativeText(),
        )
        self.assertIn(
            "Weekly Window: 8/4/2026 - 8/10/2026",
            dialog.informativeText(),
        )
        self.assertEqual(
            run_button.objectName(),
            "productionActionButton",
        )
        self.assertEqual(
            dialog.defaultButton().text(),
            "Cancel",
        )
        self.assertEqual(
            dialog.escapeButton().text(),
            "Cancel",
        )
        self.assertIn(
            "QMessageBox",
            dialog.styleSheet(),
        )
        self.assertIn(
            "productionActionButton",
            dialog.styleSheet(),
        )

    def test_production_cancel_does_not_start_worker_or_backend(self) -> None:
        controller = FakeUIController()
        window = self._make_window(controller)

        with (
            patch.object(
                window,
                "_confirm_production_weekly_process",
                return_value=False,
            ),
            patch.object(window, "_start_operation") as start,
        ):
            window._handle_weekly_process_request(
                "8/3/2026",
                False,
            )

        start.assert_not_called()
        controller.run_weekly_process.assert_not_called()
        self.assertIsNone(window._operation_worker)
        self.assertIsNone(window._operation_thread)

    def test_production_confirm_starts_existing_backend_flow(self) -> None:
        controller = FakeUIController()
        window = self._make_window(controller)

        with (
            patch.object(
                window,
                "_confirm_production_weekly_process",
                return_value=True,
            ),
            patch.object(window, "_start_operation") as start,
        ):
            window._handle_weekly_process_request(
                "8/3/2026",
                False,
            )

        start.assert_called_once()
        operation = start.call_args.kwargs["operation"]
        operation()

        controller.run_weekly_process.assert_called_once_with(
            reference_date="8/3/2026",
            test_mode=False,
        )

    def test_environment_change_updates_toolbar_and_sidebar(self) -> None:
        window = self._make_window()

        window._handle_weekly_environment_changed("PRODUCTION")

        self.assertEqual(window.toolbar._environment, "PRODUCTION")
        self.assertEqual(window.sidebar._environment, "PRODUCTION")
        self.assertEqual(
            window.sidebar._environment_badge.text(),
            "PRODUCTION",
        )

        window._handle_weekly_environment_changed("TEST")

        self.assertEqual(window.toolbar._environment, "TEST")
        self.assertEqual(window.sidebar._environment, "TEST")
        self.assertEqual(
            window.sidebar._environment_badge.text(),
            "TEST",
        )

    def test_changing_environment_clears_stale_preflight_readiness(self) -> None:
        view = WeeklyRunView()

        view.set_preflight_result(
            ready=True,
            status="READY_TO_PROCESS",
            message="Ready.",
            issues=(),
            sources_received=3,
        )
        self.assertTrue(view.actions_card.process_button.isEnabled())

        view.configuration_card.environment_combo.setCurrentText(
            "PRODUCTION"
        )

        self.assertFalse(view.actions_card.process_button.isEnabled())

    def test_reset_current_session_does_not_delete_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            session_file = root / "runtime" / "sessions" / "current_session.json"
            output_file = root / "output" / "weekly_runs" / "kept.txt"
            output_file.parent.mkdir(parents=True)
            output_file.write_text("kept", encoding="utf-8")

            manager = SessionManager(session_file=session_file)
            manager.create(
                environment="PRODUCTION",
                operation="PREFLIGHT",
                reference_date="8/3/2026",
            )

            manager.reset()

            self.assertFalse(session_file.exists())
            self.assertTrue(output_file.exists())

    def _make_window(
        self,
        controller: FakeUIController | None = None,
    ) -> ApplicationShell:
        return ApplicationShell(
            ui_controller=controller or FakeUIController()
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
