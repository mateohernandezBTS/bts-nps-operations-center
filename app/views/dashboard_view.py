from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.controllers.ui_controller import DashboardState
from app.theme import Colors, Spacing, Typography
from app.widgets.card import Card
from app.widgets.metric_card import MetricCard
from app.widgets.status_badge import StatusBadge


class DashboardView(QWidget):
    """
    Main operational dashboard for BTS SELAM NPS Operations Center.

    The view contains presentation logic only. All operational data is
    received through DashboardState, prepared by UIController.
    """

    EXPECTED_SOURCE_NAMES = (
        "Argentina",
        "Brazil",
        "Mexico",
    )

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("dashboardView")

        self._source_badges: list[StatusBadge] = []

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("dashboardScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        content = QWidget()
        content.setObjectName("dashboardContent")
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

        section_title = QLabel(
            "Weekly Overview",
            content,
        )
        section_title.setObjectName("dashboardSectionTitle")

        content_layout.addWidget(section_title)
        content_layout.addWidget(self._build_metrics())
        content_layout.addWidget(
            self._build_operational_section()
        )
        content_layout.addWidget(
            self._build_sources_card()
        )
        content_layout.addStretch()

        self.scroll_area.setWidget(content)
        outer_layout.addWidget(self.scroll_area)

    def _build_metrics(self) -> QWidget:
        metrics_container = QWidget(self)
        metrics_container.setObjectName("dashboardMetrics")

        metrics_layout = QGridLayout(metrics_container)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setHorizontalSpacing(Spacing.LG)
        metrics_layout.setVerticalSpacing(Spacing.LG)

        self.ready_card = MetricCard(
            label="READY",
            value="0",
            helper_text="Records ready for NPS creation",
            tone="neutral",
            accent_text="No data",
        )

        self.review_card = MetricCard(
            label="REVIEW",
            value="0",
            helper_text="Records requiring manual attention",
            tone="neutral",
            accent_text="No issues",
        )

        self.sources_metric_card = MetricCard(
            label="SOURCES",
            value="0 / 3",
            helper_text="Expected Upcoming NPS reports",
            tone="neutral",
            accent_text="Pending",
        )

        self.last_run_card = MetricCard(
            label="LAST RUN",
            value="No run",
            helper_text="No weekly process session is available",
            tone="neutral",
        )

        metric_cards = (
            self.ready_card,
            self.review_card,
            self.sources_metric_card,
            self.last_run_card,
        )

        for card in metric_cards:
            card.setFixedHeight(190)
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

        metrics_layout.addWidget(
            self.ready_card,
            0,
            0,
        )
        metrics_layout.addWidget(
            self.review_card,
            0,
            1,
        )
        metrics_layout.addWidget(
            self.sources_metric_card,
            1,
            0,
        )
        metrics_layout.addWidget(
            self.last_run_card,
            1,
            1,
        )

        metrics_layout.setColumnStretch(0, 1)
        metrics_layout.setColumnStretch(1, 1)

        return metrics_container

    def _build_operational_section(self) -> QWidget:
        container = QWidget(self)
        container.setObjectName(
            "dashboardOperationalSection"
        )

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.MD)

        latest_run_card = Card(
            title="Latest Weekly Run",
            subtitle="Latest persisted application session.",
        )
        latest_run_card.setMinimumHeight(235)
        latest_run_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        latest_run_card.add_widget(
            self._build_latest_run_content()
        )

        environment_card = Card(
            title="Current Environment",
            subtitle="Active execution context.",
        )
        environment_card.setMinimumHeight(235)
        environment_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        environment_card.add_widget(
            self._build_environment_content()
        )

        layout.addWidget(latest_run_card, 2)
        layout.addWidget(environment_card, 1)

        return container

    def _build_latest_run_content(self) -> QWidget:
        content = QWidget(self)
        content.setObjectName("latestRunContent")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        layout.setSpacing(Spacing.SM)

        status_row = QWidget(content)
        status_row.setObjectName(
            "dashboardStatusRow"
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
            "dashboardDetailLabel"
        )

        self.latest_status_badge = StatusBadge(
            "No run",
            status_row,
            tone="neutral",
            uppercase=False,
        )

        status_layout.addWidget(status_label)
        status_layout.addStretch()
        status_layout.addWidget(
            self.latest_status_badge
        )

        details = QWidget(content)
        details.setObjectName("latestRunDetails")

        details_layout = QGridLayout(details)
        details_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        details_layout.setHorizontalSpacing(
            Spacing.XL
        )
        details_layout.setVerticalSpacing(
            Spacing.SM
        )

        reference_label = QLabel(
            "Reference Monday",
            details,
        )
        reference_label.setObjectName(
            "dashboardDetailLabel"
        )

        self.reference_date_value = QLabel(
            "-",
            details,
        )
        self.reference_date_value.setObjectName(
            "dashboardDetailValue"
        )

        ready_label = QLabel(
            "Ready records",
            details,
        )
        ready_label.setObjectName(
            "dashboardDetailLabel"
        )

        self.ready_value = QLabel(
            "0",
            details,
        )
        self.ready_value.setObjectName(
            "dashboardDetailValue"
        )

        review_label = QLabel(
            "Manual review",
            details,
        )
        review_label.setObjectName(
            "dashboardDetailLabel"
        )

        self.review_value = QLabel(
            "0",
            details,
        )
        self.review_value.setObjectName(
            "dashboardDetailValue"
        )

        details_layout.addWidget(
            reference_label,
            0,
            0,
        )
        details_layout.addWidget(
            self.reference_date_value,
            0,
            1,
        )
        details_layout.addWidget(
            ready_label,
            1,
            0,
        )
        details_layout.addWidget(
            self.ready_value,
            1,
            1,
        )
        details_layout.addWidget(
            review_label,
            2,
            0,
        )
        details_layout.addWidget(
            self.review_value,
            2,
            1,
        )

        details_layout.setColumnMinimumWidth(
            0,
            120,
        )
        details_layout.setColumnStretch(1, 1)

        self.run_id_label = QLabel(
            "Run ID: -",
            content,
        )
        self.run_id_label.setObjectName(
            "dashboardMutedText"
        )
        self.run_id_label.setWordWrap(True)
        self.run_id_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout.addWidget(status_row)
        layout.addWidget(details)
        layout.addStretch()
        layout.addWidget(self.run_id_label)

        return content

    def _build_environment_content(self) -> QWidget:
        content = QWidget(self)
        content.setObjectName(
            "environmentContent"
        )

        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        layout.setSpacing(Spacing.SM)

        self.environment_title = QLabel(
            "TEST",
            content,
        )
        self.environment_title.setObjectName(
            "dashboardEnvironmentTitle"
        )

        environment_caption = QLabel(
            "Execution environment",
            content,
        )
        environment_caption.setObjectName(
            "dashboardMutedText"
        )

        backend_row = QWidget(content)
        backend_row.setObjectName(
            "dashboardStatusRow"
        )

        backend_layout = QHBoxLayout(
            backend_row
        )
        backend_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        backend_layout.setSpacing(Spacing.SM)

        backend_label = QLabel(
            "Backend",
            backend_row,
        )
        backend_label.setObjectName(
            "dashboardDetailLabel"
        )

        self.backend_badge = StatusBadge(
            "READY",
            backend_row,
            tone="success",
        )

        backend_layout.addWidget(
            backend_label
        )
        backend_layout.addStretch()
        backend_layout.addWidget(
            self.backend_badge
        )

        session_row = QWidget(content)
        session_row.setObjectName(
            "dashboardStatusRow"
        )

        session_layout = QHBoxLayout(
            session_row
        )
        session_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        session_layout.setSpacing(Spacing.SM)

        session_label = QLabel(
            "Session",
            session_row,
        )
        session_label.setObjectName(
            "dashboardDetailLabel"
        )

        self.session_badge = StatusBadge(
            "IDLE",
            session_row,
            tone="neutral",
        )

        session_layout.addWidget(
            session_label
        )
        session_layout.addStretch()
        session_layout.addWidget(
            self.session_badge
        )

        self.updated_label = QLabel(
            "Last update: -",
            content,
        )
        self.updated_label.setObjectName(
            "dashboardMutedText"
        )
        self.updated_label.setWordWrap(True)

        layout.addWidget(
            self.environment_title
        )
        layout.addWidget(
            environment_caption
        )
        layout.addSpacing(Spacing.XS)
        layout.addWidget(backend_row)
        layout.addWidget(session_row)
        layout.addStretch()
        layout.addWidget(self.updated_label)

        return content

    def _build_sources_card(self) -> Card:
        card = Card(
            title="Sources",
            subtitle=(
                "Expected Upcoming NPS reports "
                "for the weekly run."
            ),
        )
        card.setMinimumHeight(185)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        sources_container = QWidget(card)
        sources_container.setObjectName(
            "sourcesContainer"
        )

        sources_layout = QGridLayout(
            sources_container
        )
        sources_layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        sources_layout.setHorizontalSpacing(
            Spacing.MD
        )
        sources_layout.setVerticalSpacing(
            Spacing.SM
        )

        for row_index, source_name in enumerate(
            self.EXPECTED_SOURCE_NAMES
        ):
            indicator = QLabel(
                "●",
                sources_container,
            )
            indicator.setObjectName(
                "dashboardSourceIndicator"
            )

            source_label = QLabel(
                source_name,
                sources_container,
            )
            source_label.setObjectName(
                "dashboardSourceLabel"
            )

            source_badge = StatusBadge(
                "Expected",
                sources_container,
                tone="neutral",
            )
            source_badge.setMaximumWidth(115)

            self._source_badges.append(
                source_badge
            )

            sources_layout.addWidget(
                indicator,
                row_index,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )
            sources_layout.addWidget(
                source_label,
                row_index,
                1,
                Qt.AlignmentFlag.AlignVCenter,
            )
            sources_layout.addWidget(
                source_badge,
                row_index,
                2,
                Qt.AlignmentFlag.AlignVCenter,
            )

        self.sources_summary_badge = StatusBadge(
            "0 / 3 received",
            sources_container,
            tone="neutral",
            uppercase=False,
        )

        sources_layout.addWidget(
            self.sources_summary_badge,
            len(self.EXPECTED_SOURCE_NAMES),
            0,
            1,
            3,
            Qt.AlignmentFlag.AlignRight,
        )

        sources_layout.setColumnStretch(1, 1)

        card.add_widget(sources_container)

        return card

    def apply_state(
        self,
        state: DashboardState,
    ) -> None:
        """
        Apply a UI-friendly backend state to the dashboard.
        """

        has_run = bool(
            state.weekly_run_id
            or state.operation == "WEEKLY_PROCESS"
        )

        ready_tone = (
            "success"
            if state.ready_records > 0
            else "neutral"
        )

        ready_accent = (
            "Completed"
            if has_run
            else "No data"
        )

        review_exists = (
            state.review_records > 0
        )

        review_tone = (
            "warning"
            if review_exists
            else "success"
        )

        review_accent = (
            "Review required"
            if review_exists
            else "No issues"
        )

        sources_complete = (
            state.sources_expected > 0
            and state.sources_received
            >= state.sources_expected
        )

        sources_tone = (
            "success"
            if sources_complete
            else "warning"
        )

        sources_accent = (
            "Ready"
            if sources_complete
            else "Pending"
        )

        latest_tone = self._status_tone(
            state.latest_run_status
        )

        latest_status = self._display_status(
            state.latest_run_status
        )

        self.ready_card.set_value(
            str(state.ready_records)
        )
        self.ready_card.set_tone(
            ready_tone
        )
        self.ready_card.set_accent_text(
            ready_accent
        )

        self.review_card.set_value(
            str(state.review_records)
        )
        self.review_card.set_tone(
            review_tone
        )
        self.review_card.set_accent_text(
            review_accent
        )

        self.sources_metric_card.set_value(
            f"{state.sources_received} / "
            f"{state.sources_expected}"
        )
        self.sources_metric_card.set_tone(
            sources_tone
        )
        self.sources_metric_card.set_accent_text(
            sources_accent
        )

        self.last_run_card.set_value(
            latest_status
        )
        self.last_run_card.set_tone(
            latest_tone
        )
        self.last_run_card.set_helper_text(
            state.message
            or "Latest persisted weekly process"
        )

        self.latest_status_badge.set_status(
            text=latest_status,
            tone=latest_tone,
        )

        self.reference_date_value.setText(
            state.reference_date or "-"
        )
        self.ready_value.setText(
            str(state.ready_records)
        )
        self.review_value.setText(
            str(state.review_records)
        )

        self.run_id_label.setText(
            "Run ID: "
            + (
                state.weekly_run_id
                if state.weekly_run_id
                else "-"
            )
        )

        self.environment_title.setText(
            state.environment
        )

        self.backend_badge.set_status(
            text=state.backend_status,
            tone=self._status_tone(
                state.backend_status
            ),
        )

        self.session_badge.set_status(
            text=self._display_status(
                state.session_status
            ),
            tone=self._status_tone(
                state.session_status
            ),
        )

        self.updated_label.setText(
            "Last update: "
            + (
                state.updated_at
                if state.updated_at
                else "-"
            )
        )

        for index, source_badge in enumerate(
            self._source_badges
        ):
            source_received = (
                index < state.sources_received
            )

            source_badge.set_status(
                text=(
                    "Received"
                    if source_received
                    else "Expected"
                ),
                tone=(
                    "success"
                    if source_received
                    else "neutral"
                ),
            )

        self.sources_summary_badge.set_status(
            text=(
                f"{state.sources_received} / "
                f"{state.sources_expected} received"
            ),
            tone=sources_tone,
        )

    @staticmethod
    def _display_status(
        status: str,
    ) -> str:
        normalized = (
            status or "IDLE"
        ).replace("_", " ").strip()

        return normalized.title()

    @staticmethod
    def _status_tone(
        status: str,
    ) -> str:
        normalized = (
            status or "IDLE"
        ).upper()

        if normalized in {
            "COMPLETED",
            "COMPLETED_WITH_REVIEW",
            "READY",
            "READY_TO_PROCESS",
        }:
            return "success"

        if normalized in {
            "BLOCKED",
            "REVIEW",
        }:
            return "warning"

        if normalized in {
            "FAILED",
            "ERROR",
        }:
            return "error"

        if normalized in {
            "RUNNING",
            "PROCESSING",
            "PREFLIGHT_RUNNING",
            "STARTED",
        }:
            return "info"

        return "neutral"

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#dashboardView,
            QWidget#dashboardContent,
            QWidget#dashboardMetrics,
            QWidget#dashboardOperationalSection,
            QWidget#latestRunContent,
            QWidget#latestRunDetails,
            QWidget#environmentContent,
            QWidget#dashboardStatusRow,
            QWidget#sourcesContainer {{
                background-color: transparent;
            }}

            QScrollArea#dashboardScrollArea {{
                background-color: {Colors.APP_BACKGROUND};
                border: none;
            }}

            QScrollArea#dashboardScrollArea
            > QWidget > QWidget {{
                background-color: {Colors.APP_BACKGROUND};
            }}

            QLabel#dashboardSectionTitle {{
                color: {Colors.BTS_NAVY};
                background-color: transparent;
                font-size: {Typography.SIZE_TITLE}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#dashboardEnvironmentTitle {{
                color: {Colors.BTS_NAVY};
                background-color: transparent;
                font-size: 28px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#dashboardDetailLabel {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QLabel#dashboardDetailValue {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_MEDIUM};
            }}

            QLabel#dashboardMutedText {{
                color: {Colors.TEXT_MUTED};
                background-color: transparent;
                font-size: {Typography.SIZE_CAPTION}px;
                font-weight: {Typography.WEIGHT_NORMAL};
            }}

            QLabel#dashboardSourceIndicator {{
                color: {Colors.INFO};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#dashboardSourceLabel {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_NORMAL};
            }}
            """
        )