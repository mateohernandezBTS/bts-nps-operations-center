from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.theme import (
    Colors,
    Spacing,
    Typography,
)
from app.views.weekly_run.actions_card import ActionsCard
from app.views.weekly_run.configuration_card import ConfigurationCard
from app.views.weekly_run.preflight_card import PreflightCard
from app.views.weekly_run.sources_card import SourcesCard


class WeeklyRunView(QWidget):
    """
    Modular Weekly Run screen.

    This view orchestrates reusable presentation components only.
    Backend execution remains outside the view and is requested through
    signals consumed by ApplicationShell.
    """

    preflight_requested = Signal(str, bool)
    weekly_process_requested = Signal(str, bool)
    environment_changed = Signal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("weeklyRunView")

        self._build_ui()
        self._connect_signals()
        self._apply_styles()

        self.set_idle_state()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName(
            "weeklyRunScrollArea"
        )
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(
            QScrollArea.Shape.NoFrame
        )

        content = QWidget()
        content.setObjectName(
            "weeklyRunContent"
        )
        content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(
            Spacing.XL,
            Spacing.LG,
            Spacing.XL,
            Spacing.XL,
        )
        content_layout.setSpacing(Spacing.LG)

        title = QLabel(
            "Prepare Weekly Process",
            content,
        )
        title.setObjectName(
            "weeklyRunSectionTitle"
        )

        description = QLabel(
            "Select a reference date, validate all expected sources "
            "and run preflight before starting the weekly process.",
            content,
        )
        description.setObjectName(
            "weeklyRunSectionDescription"
        )
        description.setWordWrap(True)

        self.configuration_card = ConfigurationCard(content)
        self.sources_card = SourcesCard(content)
        self.preflight_card = PreflightCard(content)
        self.actions_card = ActionsCard(content)

        content_layout.addWidget(title)
        content_layout.addWidget(description)
        content_layout.addWidget(self.configuration_card)
        content_layout.addWidget(self.sources_card)
        content_layout.addWidget(self.preflight_card)
        content_layout.addWidget(self.actions_card)
        content_layout.addStretch()

        self.scroll_area.setWidget(content)
        root_layout.addWidget(self.scroll_area)

    def _connect_signals(self) -> None:
        self.configuration_card.configuration_changed.connect(
            self._handle_configuration_changed
        )

        self.actions_card.preflight_requested.connect(
            self._emit_preflight_request
        )

        self.actions_card.weekly_process_requested.connect(
            self._emit_weekly_process_request
        )

    def _handle_configuration_changed(
        self,
        reference_date: str,
        test_mode: bool,
    ) -> None:
        self.sources_card.set_not_checked()
        self.preflight_card.set_idle_state()
        self.actions_card.set_idle_state()
        self.actions_card.set_production_mode(
            not test_mode
        )
        self.environment_changed.emit(
            "TEST" if test_mode else "PRODUCTION"
        )

    def _emit_preflight_request(self) -> None:
        self.preflight_requested.emit(
            self.reference_date_text(),
            self.is_test_mode(),
        )

    def _emit_weekly_process_request(self) -> None:
        self.weekly_process_requested.emit(
            self.reference_date_text(),
            self.is_test_mode(),
        )

    def reference_date_text(self) -> str:
        return self.configuration_card.reference_date_text()

    def selected_date_text(self) -> str:
        return self.configuration_card.selected_date_text()

    def weekly_window_text(self) -> str:
        return self.configuration_card.weekly_window_text()

    def is_test_mode(self) -> bool:
        return self.configuration_card.is_test_mode()

    def set_idle_state(self) -> None:
        self.sources_card.set_not_checked()
        self.preflight_card.set_idle_state()
        self.actions_card.set_idle_state()
        self.actions_card.set_production_mode(
            self.configuration_card.is_production_mode()
        )

    def set_preflight_running(self) -> None:
        self.preflight_card.set_running_state()
        self.actions_card.set_preflight_running()

    def set_preflight_result(
        self,
        *,
        ready: bool,
        status: str,
        message: str,
        issues: tuple[str, ...] = (),
        sources_received: int = 0,
    ) -> None:
        self.sources_card.set_sources_received(
            sources_received
        )

        self.preflight_card.set_result(
            ready=ready,
            status=status,
            message=message,
            issues=issues,
        )

        if ready:
            self.actions_card.set_preflight_ready()
        else:
            self.actions_card.set_preflight_blocked()

    def set_processing_running(self) -> None:
        self.preflight_card.status_badge.set_status(
            text="Processing",
            tone="info",
        )
        self.preflight_card.message_label.setText(
            "The weekly process is currently running."
        )
        self.preflight_card.issues_label.setText(
            "Weekly processing in progress."
        )
        self.actions_card.set_processing_running()

    def set_process_result(
        self,
        *,
        success: bool,
        status: str,
        message: str,
        issues: tuple[str, ...] = (),
    ) -> None:
        if success:
            self.preflight_card.status_badge.set_status(
                text=self._display_status(status),
                tone="success",
            )
            self.preflight_card.message_label.setText(message)

            if issues:
                self.preflight_card.issues_label.setText(
                    "\n".join(
                        f"• {issue}"
                        for issue in issues
                    )
                )
            else:
                self.preflight_card.issues_label.setText(
                    "No processing issues."
                )
        else:
            self.preflight_card.set_failed_state(
                message=message,
                issues=issues,
            )

        self.actions_card.set_process_finished()

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
            QWidget#weeklyRunView,
            QWidget#weeklyRunContent {{
                background-color: transparent;
            }}

            QScrollArea#weeklyRunScrollArea {{
                background-color: {Colors.APP_BACKGROUND};
                border: none;
            }}

            QScrollArea#weeklyRunScrollArea
            > QWidget > QWidget {{
                background-color: {Colors.APP_BACKGROUND};
            }}

            QLabel#weeklyRunSectionTitle {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_TITLE}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#weeklyRunSectionDescription {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_LARGE}px;
                font-weight: {Typography.WEIGHT_NORMAL};
            }}
            """
        )
