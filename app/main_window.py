from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.controllers.operation_worker import OperationWorker
from app.controllers.ui_controller import (
    DashboardState,
    RunHistoryItem,
    UIActionResult,
    UIController,
)
from app.theme import Colors, Spacing, Typography
from app.views.dashboard_view import DashboardView
from app.views.run_history.run_history_view import RunHistoryView
from app.views.settings.settings_view import SettingsView
from app.views.weekly_output.weekly_output_view import WeeklyOutputView
from app.views.weekly_run.weekly_run_view import WeeklyRunView
from app.widgets.card import Card
from app.widgets.notification_bar import NotificationBar
from app.widgets.sidebar import Sidebar
from app.widgets.status_badge import StatusBadge
from app.widgets.toolbar import Toolbar
from engine.operational_logging import persist_application_error


class PlaceholderView(QWidget):
    """Temporary content view for unfinished screens."""

    def __init__(
        self,
        title: str,
        description: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("placeholderView")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
        )
        root_layout.setSpacing(Spacing.LG)

        page_title = QLabel(title, self)
        page_title.setObjectName("placeholderPageTitle")

        page_description = QLabel(description, self)
        page_description.setObjectName(
            "placeholderPageDescription"
        )
        page_description.setWordWrap(True)

        placeholder_card = Card(
            title=title,
            subtitle="Application view placeholder",
        )

        placeholder_message = QLabel(
            "This area will be replaced by the final product screen.",
            placeholder_card,
        )
        placeholder_message.setObjectName("placeholderMessage")
        placeholder_message.setWordWrap(True)

        state_row = QWidget(placeholder_card)
        state_row.setObjectName("placeholderStateRow")

        state_layout = QHBoxLayout(state_row)
        state_layout.setContentsMargins(0, 0, 0, 0)
        state_layout.setSpacing(Spacing.SM)

        state_label = QLabel("View status:", state_row)
        state_label.setObjectName("placeholderStateLabel")

        state_badge = StatusBadge(
            "Under construction",
            state_row,
            tone="info",
            uppercase=False,
        )

        state_layout.addWidget(state_label)
        state_layout.addWidget(state_badge)
        state_layout.addStretch()

        placeholder_card.add_widget(placeholder_message)
        placeholder_card.add_widget(state_row)

        root_layout.addWidget(page_title)
        root_layout.addWidget(page_description)
        root_layout.addWidget(placeholder_card)
        root_layout.addStretch()

        self.setStyleSheet(
            f"""
            QWidget#placeholderView,
            QWidget#placeholderStateRow {{
                background-color: transparent;
            }}

            QLabel#placeholderPageTitle {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_PAGE_TITLE}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#placeholderPageDescription {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_LARGE}px;
                font-weight: {Typography.WEIGHT_NORMAL};
            }}

            QLabel#placeholderMessage,
            QLabel#placeholderStateLabel {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
            }}
            """
        )


class ApplicationShell(QMainWindow):
    """Permanent visual shell for BTS SELAM NPS Operations Center."""

    PAGE_METADATA = {
        "dashboard": {
            "title": "Dashboard",
            "subtitle": (
                "Operational overview of the latest SELAM "
                "weekly process."
            ),
        },
        "weekly_run": {
            "title": "Weekly Run",
            "subtitle": (
                "Validate sources, run preflight and start "
                "the weekly process."
            ),
        },
        "weekly_output": {
            "title": "Weekly Output",
            "subtitle": (
                "Review the latest Slack-ready output and "
                "generated weekly package."
            ),
        },
        "history": {
            "title": "Run History",
            "subtitle": (
                "Review previous weekly executions and "
                "generated outputs."
            ),
        },
        "settings": {
            "title": "Settings",
            "subtitle": (
                "View the active environment and system "
                "configuration."
            ),
        },
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        ui_controller: Optional[UIController] = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("BTS SELAM NPS Operations Center")
        self.setMinimumSize(1180, 760)

        self.ui_controller = (
            ui_controller
            if ui_controller is not None
            else UIController()
        )

        self._view_indexes: dict[str, int] = {}
        self._dashboard_state: Optional[DashboardState] = None
        self._operation_thread: Optional[QThread] = None
        self._operation_worker: Optional[OperationWorker] = None

        # True only while navigating from Run History to Weekly Output.
        self._historical_output_active = False

        self._build_ui()
        self._register_views()
        self._connect_signals()
        self._load_application_state()

        self.show_view("dashboard")

    def _build_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setObjectName("applicationRoot")

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar(
            application_version="1.0.2",
            environment="TEST",
        )

        self.main_area = QWidget(central_widget)
        self.main_area.setObjectName("mainArea")
        self.main_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        main_layout = QVBoxLayout(self.main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.toolbar = Toolbar(
            title="Dashboard",
            subtitle=(
                "Operational overview of the latest SELAM "
                "weekly process."
            ),
            environment="TEST",
            backend_status="READY",
        )

        self.content_stack = QStackedWidget(self.main_area)
        self.content_stack.setObjectName("contentStack")

        self.notification_bar = NotificationBar(
            message="Loading application state...",
            tone="info",
        )

        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.content_stack, 1)
        main_layout.addWidget(self.notification_bar)

        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(self.main_area, 1)

        self.setCentralWidget(central_widget)

        self.setStyleSheet(
            f"""
            QWidget#applicationRoot,
            QWidget#mainArea {{
                background-color: {Colors.APP_BACKGROUND};
            }}

            QStackedWidget#contentStack {{
                background-color: {Colors.APP_BACKGROUND};
                border: none;
            }}
            """
        )

    def _register_views(self) -> None:
        """Create and register every application view."""

        self.dashboard_view = DashboardView()
        self.weekly_run_view = WeeklyRunView()
        self.weekly_output_view = WeeklyOutputView()
        self.run_history_view = RunHistoryView()
        self.settings_view = SettingsView()

        views = {
            "dashboard": self.dashboard_view,
            "weekly_run": self.weekly_run_view,
            "weekly_output": self.weekly_output_view,
            "history": self.run_history_view,
            "settings": self.settings_view,
        }

        for key, view in views.items():
            index = self.content_stack.addWidget(view)
            self._view_indexes[key] = index

    def _connect_signals(self) -> None:
        """Connect shell navigation and operational UI requests."""

        self.sidebar.navigation_requested.connect(
            self.show_view
        )

        self.weekly_run_view.preflight_requested.connect(
            self._handle_preflight_request
        )

        self.weekly_run_view.weekly_process_requested.connect(
            self._handle_weekly_process_request
        )

        self.weekly_run_view.environment_changed.connect(
            self._handle_weekly_environment_changed
        )

        self.run_history_view.view_output_requested.connect(
            self._handle_historical_output_request
        )

        self.settings_view.reset_session_requested.connect(
            self._handle_reset_session_request
        )

    def _load_application_state(self) -> None:
        """Load the latest persisted backend state through UIController."""

        try:
            state = self.ui_controller.get_dashboard_state()
        except Exception as exc:
            self._persist_unexpected_error(
                operation="LOAD_DASHBOARD_STATE",
                error=exc,
            )
            self._apply_state_error(str(exc))
            return

        self._dashboard_state = state

        self.dashboard_view.apply_state(state)

        self._load_weekly_output_state()
        self._load_run_history_state()
        self._load_settings_state()

        self.toolbar.set_environment(state.environment)
        self.sidebar.set_environment(state.environment)
        self.toolbar.set_backend_status(state.backend_status)

        self._apply_notification_state(state)

    def refresh_application_state(self) -> None:
        """Reload persisted backend state and refresh connected views."""

        self._load_application_state()

    def _load_weekly_output_state(self) -> None:
        """Load the latest generated weekly outputs."""

        try:
            state = self.ui_controller.get_weekly_output_state()
        except Exception as exc:
            self._persist_unexpected_error(
                operation="LOAD_WEEKLY_OUTPUT_STATE",
                error=exc,
            )
            self.notification_bar.set_notification(
                message=(
                    "Weekly output could not be loaded: "
                    f"{exc}"
                ),
                tone="error",
                status_text="Failed",
            )
            return

        self.weekly_output_view.apply_state(state)

    def _load_run_history_state(self) -> None:
        """Load persisted TEST and PRODUCTION weekly runs."""

        try:
            state = self.ui_controller.get_run_history_state()
        except Exception as exc:
            self._persist_unexpected_error(
                operation="LOAD_RUN_HISTORY_STATE",
                error=exc,
            )
            self.notification_bar.set_notification(
                message=(
                    "Run history could not be loaded: "
                    f"{exc}"
                ),
                tone="error",
                status_text="Failed",
            )
            return

        self.run_history_view.apply_state(state)

    def _load_settings_state(self) -> None:
        """Load current application settings through UIController."""

        try:
            state = self.ui_controller.get_settings_state()
        except Exception as exc:
            self._persist_unexpected_error(
                operation="LOAD_SETTINGS_STATE",
                error=exc,
            )
            self.notification_bar.set_notification(
                message=(
                    "Settings state could not be loaded: "
                    f"{exc}"
                ),
                tone="error",
                status_text="Failed",
            )
            return

        self.settings_view.apply_state(state)

    def _handle_historical_output_request(
        self,
        run: RunHistoryItem,
    ) -> None:
        """Load one historical weekly run into Weekly Output."""

        try:
            state = (
                self.ui_controller
                .get_weekly_output_state_for_run(run)
            )
        except Exception as exc:
            self._persist_unexpected_error(
                operation="LOAD_HISTORICAL_OUTPUT",
                error=exc,
            )
            self.notification_bar.set_notification(
                message=(
                    "Historical output could not be loaded: "
                    f"{exc}"
                ),
                tone="error",
                status_text="Failed",
            )
            return

        self.weekly_output_view.apply_state(state)

        # Prevent show_view() from immediately reloading the latest run.
        self._historical_output_active = True
        self.show_view("weekly_output")

        self.toolbar.set_environment(state.environment)
        self.sidebar.set_environment(state.environment)

        self.notification_bar.set_notification(
            message=(
                "Historical weekly output loaded: "
                f"{state.weekly_run_id} "
                f"({state.environment})."
            ),
            tone="info",
            status_text="Historical",
        )

    def _handle_reset_session_request(self) -> None:
        """
        Confirm and reset only the current persisted application session.

        Weekly outputs and Run History are preserved.
        """

        confirmation = QMessageBox(self)
        confirmation.setStyleSheet(
    f"""
    QMessageBox {{
        background-color: {Colors.SURFACE};
    }}

    QMessageBox QLabel {{
        background-color: transparent;
        color: {Colors.TEXT_PRIMARY};
        font-size: {Typography.SIZE_BODY}px;
        min-width: 360px;
    }}

    QMessageBox QPushButton {{
        min-width: 100px;
        min-height: 38px;

        background-color: {Colors.SURFACE};
        color: {Colors.TEXT_PRIMARY};

        border: 1px solid {Colors.BORDER};
        border-radius: 6px;

        padding: 0 {Spacing.MD}px;

        font-weight: {Typography.WEIGHT_SEMIBOLD};
    }}

    QMessageBox QPushButton:hover {{
        background-color: {Colors.SURFACE_ALT};
        border-color: {Colors.BTS_PINK};
    }}

    QMessageBox QPushButton:pressed {{
        background-color: {Colors.BTS_PINK_BACKGROUND};
    }}
    """
)
        confirmation.setWindowTitle(
            "Reset Current Session"
        )
        confirmation.setIcon(
            QMessageBox.Icon.Warning
        )
        confirmation.setText(
            "Reset the current application session?"
        )
        confirmation.setInformativeText(
            "This clears the active session state only.\n\n"
            "Weekly outputs and Run History will not be deleted."
        )
        confirmation.setStandardButtons(
            QMessageBox.StandardButton.Cancel
            | QMessageBox.StandardButton.Reset
        )
        confirmation.setDefaultButton(
            QMessageBox.StandardButton.Cancel
        )

        result = confirmation.exec()

        if result != QMessageBox.StandardButton.Reset:
            return

        try:
            self.ui_controller.reset_current_session()
        except Exception as exc:
            self._persist_unexpected_error(
                operation="RESET_CURRENT_SESSION",
                error=exc,
            )
            self.notification_bar.set_notification(
                message=(
                    "Current session could not be reset: "
                    f"{exc}"
                ),
                tone="error",
                status_text="Failed",
            )
            return

        self.refresh_application_state()

        self.notification_bar.set_notification(
            message=(
                "Current session reset successfully. "
                "Weekly outputs and Run History were preserved."
            ),
            tone="success",
            status_text="Reset",
        )

    def _apply_notification_state(
        self,
        state: DashboardState,
    ) -> None:
        status = (
            state.session_status or "IDLE"
        ).upper()

        if status == "FAILED":
            tone = "error"
        elif status == "BLOCKED":
            tone = "warning"
        elif status in {
            "PROCESSING",
            "PREFLIGHT_RUNNING",
            "STARTED",
            "RUNNING",
        }:
            tone = "info"
        else:
            tone = "success"

        message = state.message or "System ready"

        self.notification_bar.set_notification(
            message=message,
            tone=tone,
            status_text=self._display_status(status),
        )

    def _apply_state_error(
        self,
        message: str,
    ) -> None:
        self.toolbar.set_backend_status("FAILED")

        self.notification_bar.set_notification(
            message=(
                "Application state could not be loaded: "
                f"{message}"
            ),
            tone="error",
            status_text="Failed",
        )

    def _handle_preflight_request(
        self,
        reference_date: str,
        test_mode: bool,
    ) -> None:
        """Start certified weekly preflight outside the UI thread."""

        if self._operation_thread is not None:
            self.notification_bar.set_notification(
                message="Another operation is already running.",
                tone="warning",
                status_text="Busy",
            )
            return

        environment = "TEST" if test_mode else "PRODUCTION"

        self.weekly_run_view.set_preflight_running()

        self.toolbar.set_environment(environment)
        self.sidebar.set_environment(environment)
        self.toolbar.set_backend_status("RUNNING")

        self.notification_bar.set_notification(
            message=(
                "Weekly preflight is running for "
                f"{reference_date} in {environment}."
            ),
            tone="info",
            status_text="Running",
        )

        operation = lambda: (
            self.ui_controller.run_preflight(
                reference_date=reference_date,
                test_mode=test_mode,
            )
        )

        self._start_operation(
            operation=operation,
            environment=environment,
            operation_name="PREFLIGHT",
            completed_handler=self._handle_preflight_completed,
            failed_handler=self._handle_preflight_failed,
        )

    def _handle_preflight_completed(
        self,
        result: UIActionResult,
    ) -> None:
        """Apply a completed preflight result to WeeklyRunView."""

        inventory = (
            result.data.get("inventory", {})
            if result.data
            else {}
        )

        sources_received = self._safe_int(
            inventory.get("matched_files", 0)
        )

        ready = (
            result.success
            and result.status == "READY_TO_PROCESS"
        )

        self.weekly_run_view.set_preflight_result(
            ready=ready,
            status=result.status,
            message=result.message,
            issues=result.issues,
            sources_received=sources_received,
        )

        self.toolbar.set_environment(result.environment)
        self.sidebar.set_environment(result.environment)

        if ready:
            backend_status = "READY"
            tone = "success"
        elif result.status == "BLOCKED":
            backend_status = "BLOCKED"
            tone = "warning"
        else:
            backend_status = "FAILED"
            tone = "error"

        self.toolbar.set_backend_status(backend_status)

        self.notification_bar.set_notification(
            message=result.message,
            tone=tone,
            status_text=self._display_status(result.status),
        )

    def _handle_preflight_failed(
        self,
        message: str,
    ) -> None:
        """Handle an unexpected worker-level preflight failure."""

        self.weekly_run_view.set_preflight_result(
            ready=False,
            status="FAILED",
            message="Weekly preflight could not be completed.",
            issues=(message,),
            sources_received=0,
        )

        self.toolbar.set_backend_status("FAILED")

        self.notification_bar.set_notification(
            message=f"Weekly preflight failed: {message}",
            tone="error",
            status_text="Failed",
        )

    def _handle_weekly_process_request(
        self,
        reference_date: str,
        test_mode: bool,
    ) -> None:
        """Start the certified weekly process outside the UI thread."""

        if self._operation_thread is not None:
            self.notification_bar.set_notification(
                message="Another operation is already running.",
                tone="warning",
                status_text="Busy",
            )
            return

        environment = "TEST" if test_mode else "PRODUCTION"

        if not test_mode and not self._confirm_production_weekly_process(
            reference_date=reference_date,
            weekly_window=self.weekly_run_view.weekly_window_text(),
        ):
            return

        self.weekly_run_view.set_processing_running()

        self.toolbar.set_environment(environment)
        self.sidebar.set_environment(environment)
        self.toolbar.set_backend_status("RUNNING")

        self.notification_bar.set_notification(
            message=(
                "Weekly processing is running for "
                f"{reference_date} in {environment}."
            ),
            tone="info",
            status_text="Running",
        )

        operation = lambda: (
            self.ui_controller.run_weekly_process(
                reference_date=reference_date,
                test_mode=test_mode,
            )
        )

        self._start_operation(
            operation=operation,
            environment=environment,
            operation_name="WEEKLY_PROCESS",
            completed_handler=self._handle_weekly_process_completed,
            failed_handler=self._handle_weekly_process_failed,
        )

    def _handle_weekly_process_completed(
        self,
        result: UIActionResult,
    ) -> None:
        """Apply a completed weekly-process result to the UI."""

        self.weekly_run_view.set_process_result(
            success=result.success,
            status=result.status,
            message=result.message,
            issues=result.issues,
        )

        self.toolbar.set_environment(result.environment)
        self.sidebar.set_environment(result.environment)

        if result.success:
            backend_status = "READY"
            tone = "success"
        elif result.status == "BLOCKED":
            backend_status = "BLOCKED"
            tone = "warning"
        else:
            backend_status = "FAILED"
            tone = "error"

        self.toolbar.set_backend_status(backend_status)

        self.notification_bar.set_notification(
            message=result.message,
            tone=tone,
            status_text=self._display_status(result.status),
        )

        # Refresh Dashboard, Weekly Output and Run History immediately.
        self.refresh_application_state()

    def _handle_weekly_process_failed(
        self,
        message: str,
    ) -> None:
        """Handle an unexpected worker-level weekly-process failure."""

        self.weekly_run_view.set_process_result(
            success=False,
            status="FAILED",
            message="Weekly processing could not be completed.",
            issues=(message,),
        )

        self.toolbar.set_backend_status("FAILED")

        self.notification_bar.set_notification(
            message=f"Weekly processing failed: {message}",
            tone="error",
            status_text="Failed",
        )

    def _start_operation(
        self,
        *,
        operation: Callable[[], UIActionResult],
        environment: str = "PRODUCTION",
        operation_name: str = "UI_OPERATION",
        completed_handler: Callable[
            [UIActionResult],
            None,
        ],
        failed_handler: Callable[
            [str],
            None,
        ],
    ) -> None:
        """Execute one UIController operation in a dedicated QThread."""

        thread = QThread(self)
        worker = OperationWorker(
            operation,
            environment=environment,
            operation_name=operation_name,
        )

        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        worker.completed.connect(completed_handler)
        worker.failed.connect(failed_handler)

        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)

        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(
            self._clear_operation_references
        )

        self._operation_thread = thread
        self._operation_worker = worker

        thread.start()

    def _clear_operation_references(self) -> None:
        """Release completed thread and worker references."""

        self._operation_thread = None
        self._operation_worker = None

    def _handle_weekly_environment_changed(
        self,
        environment: str,
    ) -> None:
        self.ui_controller.set_environment(environment)
        self.toolbar.set_environment(environment)
        self.sidebar.set_environment(environment)
        self._load_application_state()

    def _confirm_production_weekly_process(
        self,
        *,
        reference_date: str,
        weekly_window: str,
    ) -> bool:
        confirmation, run_button = (
            self._build_production_confirmation_dialog(
                reference_date=reference_date,
                weekly_window=weekly_window,
            )
        )

        confirmation.exec()

        return confirmation.clickedButton() is run_button

    def _build_production_confirmation_dialog(
        self,
        *,
        reference_date: str,
        weekly_window: str,
    ) -> tuple[QMessageBox, object]:
        confirmation = QMessageBox(self)
        confirmation.setStyleSheet(
    f"""
    QMessageBox {{
        background-color: {Colors.SURFACE};
    }}

    QMessageBox QLabel {{
        background-color: transparent;
        color: {Colors.TEXT_PRIMARY};
        font-size: {Typography.SIZE_BODY}px;
        min-width: 420px;
    }}

    QMessageBox QLabel#qt_msgbox_informativelabel {{
        color: {Colors.TEXT_SECONDARY};
    }}

    QMessageBox QPushButton {{
        min-width: 110px;
        min-height: 38px;

        background-color: {Colors.SURFACE};
        color: {Colors.TEXT_PRIMARY};

        border: 1px solid {Colors.BORDER};
        border-radius: 6px;

        padding: 0 {Spacing.MD}px;

        font-weight: {Typography.WEIGHT_SEMIBOLD};
    }}

    QMessageBox QPushButton:hover {{
        background-color: {Colors.SURFACE_ALT};
        border-color: {Colors.BTS_PINK};
    }}

    QMessageBox QPushButton:pressed {{
        background-color: {Colors.BTS_PINK_BACKGROUND};
    }}

    QMessageBox QPushButton#productionActionButton {{
        background-color: {Colors.BTS_PINK};
        color: {Colors.TEXT_ON_ACCENT};
        border: 1px solid {Colors.BTS_PINK};
    }}

    QMessageBox QPushButton#productionActionButton:hover {{
        background-color: {Colors.BTS_PINK_HOVER};
        border-color: {Colors.BTS_PINK_HOVER};
        color: {Colors.TEXT_ON_ACCENT};
    }}

    QMessageBox QPushButton#productionActionButton:pressed {{
        background-color: {Colors.BTS_PINK_PRESSED};
        border-color: {Colors.BTS_PINK_PRESSED};
        color: {Colors.TEXT_ON_ACCENT};
    }}
    """
)
        confirmation.setWindowTitle(
            "Run Production Weekly Process"
        )
        confirmation.setIcon(
            QMessageBox.Icon.Warning
        )
        confirmation.setText(
            "Run the weekly process in PRODUCTION?"
        )
        confirmation.setInformativeText(
            "Environment: PRODUCTION\n"
            f"Reference Monday: {reference_date}\n"
            f"Weekly Window: {weekly_window}\n\n"
            "This operation writes production outputs."
        )

        cancel_button = confirmation.addButton(
            QMessageBox.StandardButton.Cancel
        )
        run_button = confirmation.addButton(
            "Run Production",
            QMessageBox.ButtonRole.AcceptRole,
        )
        run_button.setObjectName("productionActionButton")

        confirmation.setDefaultButton(cancel_button)
        confirmation.setEscapeButton(cancel_button)

        return confirmation, run_button

    def show_view(
        self,
        view_key: str,
    ) -> None:
        """
        Display a registered application view.

        Direct Sidebar navigation to Weekly Output loads the latest run.
        History -> View Output preserves the selected historical state
        for that navigation event only.
        """

        if view_key not in self._view_indexes:
            raise KeyError(
                f"Unknown application view: {view_key!r}. "
                f"Available views: "
                f"{sorted(self._view_indexes)}"
            )

        if view_key == "weekly_output":
            if self._historical_output_active:
                self._historical_output_active = False
            else:
                self._load_weekly_output_state()

        elif view_key == "history":
            self._load_run_history_state()

        elif view_key == "settings":
            self._load_settings_state()

        self.content_stack.setCurrentIndex(
            self._view_indexes[view_key]
        )

        page_metadata = self.PAGE_METADATA[view_key]

        self.toolbar.set_page(
            title=page_metadata["title"],
            subtitle=page_metadata["subtitle"],
        )

        if self.sidebar.active_item() != view_key:
            self.sidebar.set_active_item(
                view_key,
                emit_signal=False,
            )

    def current_view(self) -> str:
        """Return the key of the currently visible view."""

        current_index = self.content_stack.currentIndex()

        for key, index in self._view_indexes.items():
            if index == current_index:
                return key

        return ""

    def _persist_unexpected_error(
        self,
        *,
        operation: str,
        error: BaseException,
    ) -> None:
        environment = "PRODUCTION"

        if self._dashboard_state is not None:
            environment = self._dashboard_state.environment
        else:
            try:
                environment = self.ui_controller.get_application_status().get(
                    "environment",
                    environment,
                )
            except Exception:
                pass

        persist_application_error(
            environment=environment,
            component="ApplicationShell",
            operation=operation,
            error=error,
        )

    @staticmethod
    def _display_status(
        status: str,
    ) -> str:
        return (
            (status or "IDLE")
            .replace("_", " ")
            .strip()
            .title()
        )

    @staticmethod
    def _safe_int(
        value: object,
    ) -> int:
        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return 0
