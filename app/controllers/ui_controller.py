from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from engine.application_controller import (
    NPSApplicationController,
    WeeklyOperationResult,
)
from engine.paths import (
    data_path,
    session_directory,
    session_file_path,
    test_data_path,
)
from engine.session_manager import ApplicationSession


@dataclass(frozen=True)
class DashboardState:
    """
    Presentation-friendly state consumed by DashboardView.

    The Dashboard does not need to understand ApplicationSession,
    WeeklyOperationResult or internal engine structures.
    """

    environment: str
    backend_status: str
    session_status: str
    operation: str

    ready_records: int
    review_records: int
    total_records: int

    sources_received: int
    sources_expected: int

    latest_run_status: str
    weekly_run_id: str
    reference_date: str

    message: str
    started_at: str
    updated_at: str
    finished_at: str

    issues: tuple[str, ...] = field(default_factory=tuple)
    outputs: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ManualReviewItem:
    """
    Presentation-friendly manual review record.
    """

    client_name: str
    project_name: str
    country: str
    start_date: str
    decision_reason: str
    suggested_action: str
    decision: str
    project_url: str


@dataclass(frozen=True)
class ManualReviewState:
    """
    Presentation state consumed by ManualReviewView.
    """

    environment: str
    weekly_run_id: str
    review_count: int
    requires_review: bool
    message: str
    output_path: str
    items: tuple[ManualReviewItem, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class WeeklyOutputState:
    """
    Presentation state for the latest generated weekly outputs.
    """

    environment: str
    weekly_run_id: str
    status: str
    message: str

    html_path: str
    html_content: str

    excel_path: str

    manual_review_path: str
    manual_review_count: int
    requires_manual_review: bool
    manual_review_items: tuple[
        ManualReviewItem,
        ...
    ] = field(default_factory=tuple)

@dataclass(frozen=True)
class RunHistoryItem:
    """
    Presentation-friendly metadata for one persisted weekly run.
    """

    weekly_run_id: str
    environment: str
    status: str

    reference_date: str
    window_start: str
    window_end: str

    ready_records: int
    review_records: int
    total_records: int
    clients: int

    generated_at: str
    run_directory: str

    html_path: str
    excel_path: str
    manual_review_path: str


@dataclass(frozen=True)
class RunHistoryState:
    """
    Presentation state for persisted TEST and PRODUCTION weekly runs.
    """

    runs: tuple[RunHistoryItem, ...] = field(
        default_factory=tuple
    )

@dataclass(frozen=True)
class SettingsState:
    """
    Read-only application and backend settings shown in SettingsView.
    """

    application_version: str

    environment: str
    backend_status: str
    session_status: str

    weekly_run_id: str
    reference_date: str

    test_output_root: str
    production_output_root: str

    session_directory: str
    session_file: str


@dataclass(frozen=True)
class UIActionResult:
    """
    Standard response returned by UIController actions.
    """

    success: bool
    operation: str
    status: str
    environment: str
    message: str
    issues: tuple[str, ...]
    data: dict[str, Any]


class UIController:
    """
    Presentation adapter between PySide6 views and the certified backend.

    Responsibilities:
    - call the public NPSApplicationController interface;
    - translate backend objects into UI-friendly state;
    - provide safe defaults when no session exists;
    - read presentation outputs such as manual review CSVs;
    - prevent views from importing engine modules directly.

    This class contains no NPS business rules.
    """

    EXPECTED_SOURCE_COUNT = 3

    def __init__(
        self,
        application_controller: Optional[
            NPSApplicationController
        ] = None,
        *,
        default_environment: str = "TEST",
    ) -> None:
        self._application_controller = (
            application_controller
            if application_controller is not None
            else NPSApplicationController()
        )
        self._default_environment = default_environment.upper()

    def set_environment(self, environment: str) -> None:
        """Select the environment used for session-backed UI state."""
        normalized = environment.strip().upper()
        if normalized not in {"TEST", "PRODUCTION"}:
            raise ValueError(f"Unsupported environment: {environment}")
        self._default_environment = normalized

    def get_current_session(
        self,
    ) -> ApplicationSession | None:
        """
        Return the latest persisted backend session.
        """
        return self._application_controller.get_current_session(
            self._default_environment
        )

    def get_dashboard_state(self) -> DashboardState:
        """
        Build the current presentation state for DashboardView.
        """
        session = self.get_current_session()

        if session is None:
            return self._empty_dashboard_state()

        metrics = dict(session.metrics or {})
        outputs = dict(session.outputs or {})

        ready_records = self._to_int(
            metrics.get("ready_records", 0)
        )
        review_records = self._to_int(
            metrics.get("review_records", 0)
        )
        total_records = self._to_int(
            metrics.get("total_records", 0)
        )

        sources_received = self._to_int(
            metrics.get(
                "matched_files",
                self._sources_from_completed_session(session),
            )
        )

        return DashboardState(
            environment=(
                session.environment
                or self._default_environment
            ).upper(),
            backend_status=self._backend_status(
                session.status
            ),
            session_status=(
                session.status or "IDLE"
            ).upper(),
            operation=(
                session.operation or "NONE"
            ).upper(),
            ready_records=ready_records,
            review_records=review_records,
            total_records=total_records,
            sources_received=min(
                sources_received,
                self.EXPECTED_SOURCE_COUNT,
            ),
            sources_expected=self.EXPECTED_SOURCE_COUNT,
            latest_run_status=(
                session.status or "IDLE"
            ).upper(),
            weekly_run_id=session.weekly_run_id,
            reference_date=session.reference_date,
            message=session.message,
            started_at=session.started_at,
            updated_at=session.updated_at,
            finished_at=session.finished_at,
            issues=tuple(session.issues or []),
            outputs=outputs,
        )

    def get_manual_review_state(
        self,
    ) -> ManualReviewState:
        """
        Read the latest persisted manual review CSV and adapt it for UI.

        Missing session/output/file conditions return safe empty states.
        CSV parsing is presentation adaptation only; no review decision
        is made here.
        """
        session = self.get_current_session()

        if session is None:
            return ManualReviewState(
                environment=self._default_environment,
                weekly_run_id="",
                review_count=0,
                requires_review=False,
                message="No weekly run is available.",
                output_path="",
                items=(),
            )

        environment = (
            session.environment
            or self._default_environment
        ).upper()

        outputs = dict(session.outputs or {})
        manual_review_path_text = (
            outputs.get("manual_review", "") or ""
        ).strip()

        if not manual_review_path_text:
            return ManualReviewState(
                environment=environment,
                weekly_run_id=session.weekly_run_id,
                review_count=0,
                requires_review=False,
                message=(
                    "No manual review output is available "
                    "for the latest run."
                ),
                output_path="",
                items=(),
            )

        manual_review_path = Path(
            manual_review_path_text
        )

        if not manual_review_path.exists():
            return ManualReviewState(
                environment=environment,
                weekly_run_id=session.weekly_run_id,
                review_count=0,
                requires_review=False,
                message=(
                    "The manual review output could not be found."
                ),
                output_path=str(manual_review_path),
                items=(),
            )

        items = self._read_manual_review_items(
            manual_review_path
        )

        review_count = len(items)
        requires_review = review_count > 0

        if review_count == 1:
            message = "1 record requires manual review."
        elif review_count > 1:
            message = f"{review_count} records require manual review."
        else:
            message = "No records require manual review."

        return ManualReviewState(
            environment=environment,
            weekly_run_id=session.weekly_run_id,
            review_count=review_count,
            requires_review=requires_review,
            message=message,
            output_path=str(manual_review_path),
            items=tuple(items),
        )

    def get_application_status(self) -> dict[str, str]:
        """
        Return lightweight state for Toolbar and NotificationBar.
        """
        dashboard_state = self.get_dashboard_state()

        return {
            "environment": dashboard_state.environment,
            "backend_status": dashboard_state.backend_status,
            "session_status": dashboard_state.session_status,
            "message": dashboard_state.message,
        }

    def run_preflight(
        self,
        *,
        reference_date: str,
        test_mode: bool,
    ) -> UIActionResult:
        """
        Execute the certified backend preflight.
        """
        self.set_environment("TEST" if test_mode else "PRODUCTION")
        result = self._application_controller.run_preflight(
            reference_date=reference_date,
            test_mode=test_mode,
        )
        return self._adapt_operation_result(result)

    def run_weekly_process(
        self,
        *,
        reference_date: str,
        test_mode: bool,
        stop_on_error: bool = False,
    ) -> UIActionResult:
        """
        Execute the certified weekly process.
        """
        self.set_environment("TEST" if test_mode else "PRODUCTION")
        result = self._application_controller.run_weekly_process(
            reference_date=reference_date,
            test_mode=test_mode,
            stop_on_error=stop_on_error,
        )
        return self._adapt_operation_result(result)

    def reset_current_session(self) -> None:
        """
        Reset only the persisted application session.
        """
        self._application_controller.reset_current_session(
            self._default_environment
        )

    def _read_manual_review_items(
        self,
        source_path: Path,
    ) -> list[ManualReviewItem]:
        """
        Convert raw manual review CSV rows into presentation items.
        """
        items: list[ManualReviewItem] = []

        try:
            with source_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:
                reader = csv.DictReader(file)

                for row in reader:
                    items.append(
                        ManualReviewItem(
                            client_name=self._csv_value(
                                row,
                                "client_name",
                            ),
                            project_name=self._csv_value(
                                row,
                                "project_name",
                            ),
                            country=self._csv_value(
                                row,
                                "Country",
                            ),
                            start_date=self._csv_value(
                                row,
                                "start_date",
                            ),
                            decision_reason=self._csv_value(
                                row,
                                "decision_reason",
                            ),
                            suggested_action=self._csv_value(
                                row,
                                "Suggested Action",
                            ),
                            decision=self._csv_value(
                                row,
                                "decision",
                            ),
                            project_url=self._csv_value(
                                row,
                                "project_url",
                            ),
                        )
                    )
        except (OSError, csv.Error):
            return []

        return items

    def _empty_dashboard_state(
        self,
    ) -> DashboardState:
        """
        Return safe initial state before the first operation.
        """
        return DashboardState(
            environment=self._default_environment,
            backend_status="READY",
            session_status="IDLE",
            operation="NONE",
            ready_records=0,
            review_records=0,
            total_records=0,
            sources_received=0,
            sources_expected=self.EXPECTED_SOURCE_COUNT,
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

    def _adapt_operation_result(
        self,
        result: WeeklyOperationResult,
    ) -> UIActionResult:
        """
        Convert a backend result into the UI action contract.
        """
        return UIActionResult(
            success=result.success,
            operation=result.operation,
            status=result.status,
            environment=result.environment,
            message=result.message,
            issues=tuple(result.issues or []),
            data=dict(result.data or {}),
        )

    def _sources_from_completed_session(
        self,
        session: ApplicationSession,
    ) -> int:
        """
        Infer source completeness only for a completed weekly run.

        This is presentation fallback behavior, not a business rule.
        Preflight sessions normally provide matched_files directly.
        """
        completed_statuses = {
            "COMPLETED",
            "COMPLETED_WITH_REVIEW",
        }

        if (session.status or "").upper() in completed_statuses:
            return self.EXPECTED_SOURCE_COUNT

        return 0

    @staticmethod
    def _backend_status(
        session_status: str,
    ) -> str:
        """
        Translate session lifecycle state into Toolbar backend state.
        """
        normalized_status = (
            session_status or "IDLE"
        ).upper()

        if normalized_status == "FAILED":
            return "FAILED"

        if normalized_status == "BLOCKED":
            return "BLOCKED"

        if normalized_status in {
            "PREFLIGHT_RUNNING",
            "PROCESSING",
            "STARTED",
        }:
            return "RUNNING"

        if normalized_status == "IDLE":
            return "IDLE"

        return "READY"

    @staticmethod
    def _csv_value(
        row: dict[str, Any],
        key: str,
    ) -> str:
        """
        Return a normalized display string from a CSV row.
        """
        value = row.get(key, "")

        if value is None:
            return ""

        return str(value).strip()

    @staticmethod
    def _to_int(value: Any) -> int:
        """
        Safely convert backend metric values into integers.
        """
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def get_weekly_output_state(
        self,
    ) -> WeeklyOutputState:
        """
        Return the latest generated operational outputs.

        The UI receives file locations and HTML content without needing
        direct access to SessionManager or backend output structures.
        """

        session = self.get_current_session()

        if session is None:
            return WeeklyOutputState(
                environment=self._default_environment,
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

        environment = (
            session.environment
            or self._default_environment
        ).upper()

        outputs = dict(session.outputs or {})

        html_path_text = (
            outputs.get("html", "") or ""
        ).strip()

        excel_path_text = (
            outputs.get("excel", "") or ""
        ).strip()

        html_content = ""

        if html_path_text:
            html_path = Path(
                html_path_text
            )

            if html_path.exists():
                try:
                    html_content = (
                        html_path.read_text(
                            encoding="utf-8"
                        )
                    )
                except OSError:
                    html_content = ""

        manual_review = (
            self.get_manual_review_state()
        )

        return WeeklyOutputState(
            environment=environment,
            weekly_run_id=session.weekly_run_id,
            status=(
                session.status or "IDLE"
            ).upper(),
            message=session.message,
            html_path=html_path_text,
            html_content=html_content,
            excel_path=excel_path_text,
            manual_review_path=(
                manual_review.output_path
            ),
            manual_review_count=(
                manual_review.review_count
            ),
            requires_manual_review=(
                manual_review.requires_review
            ),
            manual_review_items=(
                manual_review.items
            ),
        )

    def get_run_history_state(
        self,
    ) -> RunHistoryState:
        """
        Discover persisted weekly runs from TEST and PRODUCTION.

        Each run is adapted from its weekly manifest and weekly summary.
        No business rules are evaluated here.
        """

        environments = (
            (
                "TEST",
                test_data_path(
                    "output",
                    "weekly_runs",
                ),
            ),
            (
                "PRODUCTION",
                data_path("output", "weekly_runs"),
            ),
        )

        history_items: list[
            RunHistoryItem
        ] = []

        for environment, history_root in environments:
            if not history_root.exists():
                continue

            for run_directory in history_root.iterdir():
                if not run_directory.is_dir():
                    continue

                history_item = (
                    self._read_run_history_item(
                        run_directory=run_directory,
                        environment=environment,
                    )
                )

                if history_item is not None:
                    history_items.append(
                        history_item
                    )

        history_items.sort(
            key=lambda item: item.generated_at,
            reverse=True,
        )

        return RunHistoryState(
            runs=tuple(history_items)
        )

    def get_weekly_output_state_for_run(
        self,
        run: RunHistoryItem,
    ) -> WeeklyOutputState:


        run_directory = Path(
            run.run_directory
        )

        if not run_directory.exists():
            return WeeklyOutputState(
                environment=run.environment,
                weekly_run_id=run.weekly_run_id,
                status=run.status,
                message=(
                    "The selected weekly run directory "
                    "could not be found."
                ),
                html_path="",
                html_content="",
                excel_path="",
                manual_review_path="",
                manual_review_count=0,
                requires_manual_review=False,
                manual_review_items=(),
            )

        html_path = (
            run_directory
            / "selam_slack_canvas.html"
        )

        excel_path = (
            run_directory
            / f"{run.weekly_run_id}.xlsx"
        )

        manual_review_path = (
            run_directory
            / "selam_manual_review.csv"
        )

        html_content = ""

        if html_path.exists():
            try:
                html_content = html_path.read_text(
                    encoding="utf-8"
                )
            except OSError:
                html_content = ""

        manual_review_items: tuple[
            ManualReviewItem,
            ...
        ] = ()

        if manual_review_path.exists():
            manual_review_items = tuple(
                self._read_manual_review_items(
                    manual_review_path
                )
            )

        manual_review_count = len(
            manual_review_items
        )

        return WeeklyOutputState(
            environment=run.environment,
            weekly_run_id=run.weekly_run_id,
            status=run.status,
            message=(
                "Historical weekly output loaded."
            ),
            html_path=(
                str(html_path)
                if html_path.exists()
                else ""
            ),
            html_content=html_content,
            excel_path=(
                str(excel_path)
                if excel_path.exists()
                else ""
            ),
            manual_review_path=(
                str(manual_review_path)
                if manual_review_path.exists()
                else ""
            ),
            manual_review_count=(
                manual_review_count
            ),
            requires_manual_review=(
                manual_review_count > 0
            ),
            manual_review_items=(
                manual_review_items
            ),
        )

    def _read_run_history_item(
        self,
        *,
        run_directory: Path,
        environment: str,
    ) -> RunHistoryItem | None:
        """
        Adapt one persisted weekly-run directory into history metadata.
        """

        manifest_path = (
            run_directory
            / "weekly_manifest.json"
        )

        summary_path = (
            run_directory
            / "selam_weekly_summary.json"
        )

        if not manifest_path.exists():
            return None

        try:
            import json

            with manifest_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                manifest = json.load(file)

            summary: dict[str, Any] = {}

            if summary_path.exists():
                with summary_path.open(
                    "r",
                    encoding="utf-8",
                ) as file:
                    summary = json.load(file)

        except (
            OSError,
            json.JSONDecodeError,
        ):
            return None

        weekly_run_id = str(
            manifest.get(
                "weekly_run_id",
                run_directory.name,
            )
        )

        excel_path = (
            run_directory
            / f"{weekly_run_id}.xlsx"
        )

        html_path = (
            run_directory
            / "selam_slack_canvas.html"
        )

        manual_review_path = (
            run_directory
            / "selam_manual_review.csv"
        )

        generated_at = str(
            summary.get(
                "generated_at",
                manifest.get(
                    "updated_at",
                    manifest.get(
                        "created_at",
                        "",
                    ),
                ),
            )
        )

        return RunHistoryItem(
            weekly_run_id=weekly_run_id,
            environment=environment,
            status=str(
                manifest.get(
                    "status",
                    "UNKNOWN",
                )
            ).upper(),
            reference_date=str(
                manifest.get(
                    "reference_date",
                    "",
                )
            ),
            window_start=str(
                summary.get(
                    "window_start",
                    manifest.get(
                        "window_start",
                        "",
                    ),
                )
            ),
            window_end=str(
                summary.get(
                    "window_end",
                    manifest.get(
                        "window_end",
                        "",
                    ),
                )
            ),
            ready_records=self._to_int(
                summary.get(
                    "ready_records",
                    0,
                )
            ),
            review_records=self._to_int(
                summary.get(
                    "review_records",
                    0,
                )
            ),
            total_records=self._to_int(
                summary.get(
                    "total_records",
                    0,
                )
            ),
            clients=self._to_int(
                summary.get(
                    "clients",
                    0,
                )
            ),
            generated_at=generated_at,
            run_directory=str(
                run_directory
            ),
            html_path=(
                str(html_path)
                if html_path.exists()
                else ""
            ),
            excel_path=(
                str(excel_path)
                if excel_path.exists()
                else ""
            ),
            manual_review_path=(
                str(manual_review_path)
                if manual_review_path.exists()
                else ""
            ),
        )

    def get_settings_state(
        self,
    ) -> SettingsState:
        """
        Build the current read-only Settings presentation state.
        """

        dashboard_state = (
            self.get_dashboard_state()
        )

        current_session_directory = session_directory(
            self._default_environment
        )
        current_session_file = session_file_path(
            self._default_environment
        )

        test_output_root = (
            test_data_path(
                "output",
                "weekly_runs",
            )
        )

        production_output_root = (
            data_path("output", "weekly_runs")
        )

        return SettingsState(
            application_version="1.0.2",
            environment=dashboard_state.environment,
            backend_status=dashboard_state.backend_status,
            session_status=dashboard_state.session_status,
            weekly_run_id=dashboard_state.weekly_run_id,
            reference_date=dashboard_state.reference_date,
            test_output_root=str(
                test_output_root
            ),
            production_output_root=str(
                production_output_root
            ),
            session_directory=str(
                current_session_directory
            ),
            session_file=str(
                current_session_file
            ),
        )
