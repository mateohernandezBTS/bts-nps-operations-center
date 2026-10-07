from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.theme import (
    Colors,
    Radius,
    Spacing,
    Typography,
)
from app.widgets.card import Card
from app.widgets.status_badge import StatusBadge


class PreflightCard(Card):
    """
    Presentation component for Weekly Run preflight status.

    This component does not execute preflight or interpret business
    rules. It only displays state supplied by the parent view.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(
            parent=parent,
            title="Preflight Validation",
            subtitle=(
                "Preflight checks source completeness, duplicates, "
                "unknown reports and the weekly window."
            ),
        )

        self.setObjectName("weeklyRunPreflightCard")

        self._build_ui()
        self._apply_styles()

        self.set_idle_state()

    def _build_ui(self) -> None:
        container = QWidget(self)
        container.setObjectName(
            "weeklyRunPreflightContainer"
        )

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        layout.setSpacing(Spacing.MD)

        status_row = QWidget(container)
        status_row.setObjectName(
            "weeklyRunPreflightStatusRow"
        )

        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        status_layout.setSpacing(Spacing.SM)

        status_label = QLabel(
            "Status",
            status_row,
        )
        status_label.setObjectName(
            "weeklyRunPreflightLabel"
        )

        self.status_badge = StatusBadge(
            "Not run",
            status_row,
            tone="neutral",
            uppercase=False,
        )

        status_layout.addWidget(status_label)
        status_layout.addStretch()
        status_layout.addWidget(
            self.status_badge
        )

        self.message_label = QLabel(
            "",
            container,
        )
        self.message_label.setObjectName(
            "weeklyRunPreflightMessage"
        )
        self.message_label.setWordWrap(True)

        issues_title = QLabel(
            "Issues",
            container,
        )
        issues_title.setObjectName(
            "weeklyRunPreflightIssuesTitle"
        )

        self.issues_label = QLabel(
            "",
            container,
        )
        self.issues_label.setObjectName(
            "weeklyRunPreflightIssues"
        )
        self.issues_label.setWordWrap(True)

        layout.addWidget(status_row)
        layout.addWidget(self.message_label)
        layout.addWidget(issues_title)
        layout.addWidget(self.issues_label)

        self.add_widget(container)

    def set_idle_state(self) -> None:
        self.status_badge.set_status(
            text="Not run",
            tone="neutral",
        )

        self.message_label.setText(
            "Run preflight to validate the selected weekly process."
        )

        self._set_issues(())

    def set_running_state(self) -> None:
        self.status_badge.set_status(
            text="Running",
            tone="info",
        )

        self.message_label.setText(
            "Validating weekly sources and execution conditions..."
        )

        self.issues_label.setText(
            "Validation in progress."
        )

    def set_ready_state(
        self,
        *,
        status: str = "READY_TO_PROCESS",
        message: str = (
            "Weekly preflight completed successfully."
        ),
    ) -> None:
        self.status_badge.set_status(
            text=self._display_status(status),
            tone="success",
        )

        self.message_label.setText(message)

        self._set_issues(())

    def set_blocked_state(
        self,
        *,
        status: str = "BLOCKED",
        message: str = (
            "Weekly preflight found blocking issues."
        ),
        issues: tuple[str, ...] = (),
    ) -> None:
        self.status_badge.set_status(
            text=self._display_status(status),
            tone="warning",
        )

        self.message_label.setText(message)
        self._set_issues(issues)

    def set_failed_state(
        self,
        *,
        message: str,
        issues: tuple[str, ...] = (),
    ) -> None:
        self.status_badge.set_status(
            text="Failed",
            tone="error",
        )

        self.message_label.setText(message)
        self._set_issues(issues)

    def set_result(
        self,
        *,
        ready: bool,
        status: str,
        message: str,
        issues: tuple[str, ...] = (),
    ) -> None:
        """
        Apply a generic UIController preflight result.
        """

        normalized = (
            status or ""
        ).upper()

        if ready:
            self.set_ready_state(
                status=status,
                message=message,
            )
            return

        if normalized == "BLOCKED":
            self.set_blocked_state(
                status=status,
                message=message,
                issues=issues,
            )
            return

        self.set_failed_state(
            message=message,
            issues=issues,
        )

    def _set_issues(
        self,
        issues: tuple[str, ...],
    ) -> None:
        if not issues:
            self.issues_label.setText(
                "No issues detected."
            )
            return

        self.issues_label.setText(
            "\n".join(
                f"• {issue}"
                for issue in issues
            )
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

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#weeklyRunPreflightContainer,
            QWidget#weeklyRunPreflightStatusRow {{
                background-color: transparent;
            }}

            QLabel#weeklyRunPreflightLabel,
            QLabel#weeklyRunPreflightIssuesTitle {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QLabel#weeklyRunPreflightMessage {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
            }}

            QLabel#weeklyRunPreflightIssues {{
                color: {Colors.TEXT_SECONDARY};
                background-color: {Colors.SURFACE_ALT};

                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {Radius.SMALL}px;

                padding: {Spacing.SM}px;

                font-size: {Typography.SIZE_BODY_SMALL}px;
            }}
            """
        )