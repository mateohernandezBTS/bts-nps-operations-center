from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.process_weekly_run import (
    WeeklyEndToEndError,
    execute_weekly_end_to_end,
)
from engine.session_manager import (
    ApplicationSession,
    SessionManager,
    SessionManagerError,
)
from engine.paths import session_file_path
from engine.operational_logging import (
    persist_application_error,
    persist_preflight_result,
)
from engine.weekly_preflight import (
    WeeklyPreflightError,
    run_weekly_preflight,
)


class ApplicationControllerError(Exception):
    """Raised when an application operation cannot be completed."""


@dataclass
class WeeklyOperationResult:
    """
    Standard response returned by the application controller.
    """

    success: bool
    operation: str
    status: str
    environment: str
    message: str
    data: dict[str, Any]
    issues: list[str]


class NPSApplicationController:
    """
    Single application entry point for weekly NPS operations.

    Business logic remains in the engine modules.
    The controller coordinates operations and session state.
    """

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        *,
        test_session_manager: SessionManager | None = None,
        production_session_manager: SessionManager | None = None,
    ) -> None:
        if session_manager is not None:
            self._session_managers = {
                "TEST": session_manager,
                "PRODUCTION": session_manager,
            }
        else:
            self._session_managers = {
                "TEST": (
                    test_session_manager
                    if test_session_manager is not None
                    else SessionManager(
                        session_file=session_file_path("TEST")
                    )
                ),
                "PRODUCTION": (
                    production_session_manager
                    if production_session_manager is not None
                    else SessionManager(
                        session_file=session_file_path("PRODUCTION")
                    )
                ),
            }

    def _session_manager(
        self,
        environment: str,
    ) -> SessionManager:
        normalized = environment.strip().upper()
        if normalized not in self._session_managers:
            raise ValueError(f"Unsupported environment: {environment}")
        return self._session_managers[normalized]

    @property
    def session_manager(self) -> SessionManager:
        """Compatibility alias for explicitly injected legacy callers."""
        return self._session_managers["PRODUCTION"]

    def get_current_session(
        self,
        environment: str,
    ) -> ApplicationSession | None:
        """
        Return the latest persisted application session.
        """
        return self._session_manager(environment).load()

    def reset_current_session(
        self,
        environment: str,
    ) -> None:
        """
        Clear only the persisted application session.
        """
        self._session_manager(environment).reset()

    def _safe_finish_session(
        self,
        session_manager: SessionManager,
        session: ApplicationSession,
        *,
        status: str,
        message: str,
        issues: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
        outputs: dict[str, str] | None = None,
        weekly_run_id: str | None = None,
    ) -> None:
        """
        Finish a session without hiding the original
        operational result if session persistence fails.
        """
        try:
            if weekly_run_id is not None:
                session_manager.update(
                    session,
                    weekly_run_id=weekly_run_id,
                )
            session_manager.finish(
                session,
                status=status,
                message=message,
                issues=issues,
                metrics=metrics,
                outputs=outputs,
            )
        except SessionManagerError:
            pass

    def run_preflight(
        self,
        reference_date: str,
        *,
        test_mode: bool = False,
    ) -> WeeklyOperationResult:
        """
        Execute the weekly preflight without modifying files.
        """
        environment = (
            "TEST"
            if test_mode
            else "PRODUCTION"
        )
        session_manager = self._session_manager(environment)

        try:
            session = session_manager.create(
                environment=environment,
                operation="PREFLIGHT",
                reference_date=reference_date,
                status="PREFLIGHT_RUNNING",
                current_stage="PREFLIGHT",
                message="Weekly preflight started.",
            )
        except SessionManagerError as exc:
            return WeeklyOperationResult(
                success=False,
                operation="PREFLIGHT",
                status="FAILED",
                environment=environment,
                message=str(exc),
                data={},
                issues=[str(exc)],
            )

        try:
            preflight = run_weekly_preflight(
                reference_date_text=reference_date,
                test_mode=test_mode,
            )
        except WeeklyPreflightError as exc:
            message = str(exc)
            preflight_failure = self._build_failed_preflight_result(
                reference_date=reference_date,
                environment=environment,
                message=message,
            )
            persist_preflight_result(preflight_failure)

            self._safe_finish_session(
                session_manager,
                session,
                status="FAILED",
                message=message,
                issues=[message],
            )

            return WeeklyOperationResult(
                success=False,
                operation="PREFLIGHT",
                status="FAILED",
                environment=environment,
                message=message,
                data={},
                issues=[message],
            )

        ready = (
            preflight["status"]
            == "READY_TO_PROCESS"
        )
        persist_preflight_result(preflight)

        message = (
            "Weekly preflight completed successfully."
            if ready
            else "Weekly preflight found blocking issues."
        )

        issues = list(
            preflight.get(
                "issues",
                [],
            )
        )

        metrics = self._build_preflight_metrics(
            preflight
        )

        self._safe_finish_session(
            session_manager,
            session,
            status=preflight["status"],
            message=message,
            issues=issues,
            metrics=metrics,
            weekly_run_id=(
                preflight["weekly_run_id"]
                if ready
                else None
            ),
        )

        return WeeklyOperationResult(
            success=ready,
            operation="PREFLIGHT",
            status=preflight["status"],
            environment=preflight["environment"],
            message=message,
            data=preflight,
            issues=issues,
        )

    def run_weekly_process(
        self,
        reference_date: str,
        *,
        test_mode: bool = False,
        stop_on_error: bool = False,
    ) -> WeeklyOperationResult:
        """
        Run preflight and execute the weekly pipeline only
        when the preflight result is READY_TO_PROCESS.
        """
        environment = (
            "TEST"
            if test_mode
            else "PRODUCTION"
        )
        session_manager = self._session_manager(environment)

        try:
            session = session_manager.create(
                environment=environment,
                operation="WEEKLY_PROCESS",
                reference_date=reference_date,
                status="PREFLIGHT_RUNNING",
                current_stage="PREFLIGHT",
                message="Weekly processing preflight started.",
            )
        except SessionManagerError as exc:
            return WeeklyOperationResult(
                success=False,
                operation="WEEKLY_PROCESS",
                status="FAILED",
                environment=environment,
                message=str(exc),
                data={},
                issues=[str(exc)],
            )

        try:
            preflight = run_weekly_preflight(
                reference_date_text=reference_date,
                test_mode=test_mode,
            )
        except WeeklyPreflightError as exc:
            message = str(exc)
            preflight_failure = self._build_failed_preflight_result(
                reference_date=reference_date,
                environment=environment,
                message=message,
            )
            persist_preflight_result(preflight_failure)

            self._safe_finish_session(
                session_manager,
                session,
                status="FAILED",
                message=message,
                issues=[message],
            )

            return WeeklyOperationResult(
                success=False,
                operation="WEEKLY_PROCESS",
                status="FAILED",
                environment=environment,
                message=message,
                data={},
                issues=[message],
            )

        preflight_issues = list(
            preflight.get(
                "issues",
                [],
            )
        )
        persist_preflight_result(preflight)

        if (
            preflight["status"]
            != "READY_TO_PROCESS"
        ):
            message = (
                "Weekly processing was blocked "
                "by the preflight."
            )

            try:
                session_manager.update(
        session,
        weekly_run_id=preflight[
            "weekly_run_id"
        ],
    )
            except SessionManagerError:
                pass

            self._safe_finish_session(
                session_manager,
                session,
                status="BLOCKED",
                message=message,
                issues=preflight_issues,
                metrics=self._build_preflight_metrics(
                    preflight
                ),
            )

            return WeeklyOperationResult(
                success=False,
                operation="WEEKLY_PROCESS",
                status="BLOCKED",
                environment=preflight["environment"],
                message=message,
                data={
                    "preflight": preflight,
                },
                issues=preflight_issues,
            )

        try:
            session_manager.update(
                session,
                status="PROCESSING",
                current_stage="WEEKLY_PIPELINE",
                weekly_run_id=preflight[
                    "weekly_run_id"
                ],
                message="Weekly processing started.",
                metrics=self._build_preflight_metrics(
                    preflight
                ),
            )
        except SessionManagerError:
            pass

        try:
            processing_result = (
                execute_weekly_end_to_end(
                    reference_date=reference_date,
                    test_mode=test_mode,
                    stop_on_error=stop_on_error,
                )
            )
        except WeeklyEndToEndError as exc:
            message = str(exc)

            self._safe_finish_session(
                session_manager,
                session,
                status="FAILED",
                message=message,
                issues=[message],
            )

            return WeeklyOperationResult(
                success=False,
                operation="WEEKLY_PROCESS",
                status="FAILED",
                environment=preflight["environment"],
                message=message,
                data={
                    "preflight": preflight,
                },
                issues=[message],
            )
        except Exception as exc:
            message = (
                "Unexpected weekly processing error: "
                f"{exc}"
            )
            persist_application_error(
                environment=preflight["environment"],
                component="NPSApplicationController",
                operation="WEEKLY_PROCESS",
                error=exc,
            )

            self._safe_finish_session(
                session_manager,
                session,
                status="FAILED",
                message=message,
                issues=[str(exc)],
            )

            return WeeklyOperationResult(
                success=False,
                operation="WEEKLY_PROCESS",
                status="FAILED",
                environment=preflight["environment"],
                message=message,
                data={
                    "preflight": preflight,
                },
                issues=[str(exc)],
            )

        manifest = processing_result.get(
            "manifest",
            {},
        )

        status = manifest.get(
            "status",
            "COMPLETED",
        )

        success = status in {
            "COMPLETED",
            "COMPLETED_WITH_REVIEW",
        }

        message = (
            "Weekly processing completed successfully."
            if success
            else "Weekly processing did not complete."
        )

        metrics = self._build_processing_metrics(
            processing_result
        )

        outputs = self._build_processing_outputs(
            processing_result
        )

        self._safe_finish_session(
            session_manager,
            session,
            status=status,
            message=message,
            metrics=metrics,
            outputs=outputs,
        )

        return WeeklyOperationResult(
            success=success,
            operation="WEEKLY_PROCESS",
            status=status,
            environment=preflight["environment"],
            message=message,
            data={
                "preflight": preflight,
                "processing": processing_result,
            },
            issues=[],
        )

    @staticmethod
    def _build_preflight_metrics(
        preflight: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract UI-friendly metrics from preflight data.
        """
        inventory = preflight.get(
            "inventory",
            {},
        )

        return {
            "files_scanned": inventory.get(
                "files_scanned",
                0,
            ),
            "matched_files": inventory.get(
                "matched_files",
                0,
            ),
            "review_files": inventory.get(
                "review_files",
                0,
            ),
            "unknown_reports": inventory.get(
                "unconfigured_files",
                0,
            ),
            "duplicate_sources": inventory.get(
                "duplicate_sources",
                0,
            ),
            "missing_required_sources": inventory.get(
                "missing_required_sources",
                0,
            ),
        }

    @staticmethod
    def _build_processing_metrics(
        processing_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract final operational metrics for the UI.
        """
        summary = processing_result.get(
            "weekly_summary",
            {},
        )

        return {
            "total_records": summary.get(
                "total_records",
                0,
            ),
            "ready_records": summary.get(
                "ready_records",
                0,
            ),
            "review_records": summary.get(
                "review_records",
                0,
            ),
            "clients": summary.get(
                "clients",
                0,
            ),
            "duplicate_issues": summary.get(
                "duplicate_issues",
                0,
            ),
        }

    @staticmethod
    def _build_processing_outputs(
        processing_result: dict[str, Any],
    ) -> dict[str, str]:
        """
        Extract generated output paths for the UI.
        """
        output_keys = {
            "excel": "weekly_excel_path",
            "html": "slack_canvas_path",
            "csv": "csv_path",
            "manual_review": (
                "manual_review_csv_path"
            ),
            "summary": "summary_path",
            "manifest": "manifest_path",
        }

        outputs: dict[str, str] = {}

        for output_name, result_key in (
            output_keys.items()
        ):
            value = processing_result.get(
                result_key
            )

            if value:
                outputs[output_name] = str(
                    Path(value)
                )

        return outputs

    @staticmethod
    def _build_failed_preflight_result(
        *,
        reference_date: str,
        environment: str,
        message: str,
    ) -> dict[str, Any]:
        return {
            "environment": environment,
            "reference_date": reference_date,
            "status": "FAILED",
            "issues": [message],
            "inventory": {},
        }
