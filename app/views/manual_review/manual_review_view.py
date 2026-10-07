from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.controllers.ui_controller import ManualReviewState
from app.theme import (
    Colors,
    Spacing,
    Typography,
)
from app.widgets.card import Card
from app.widgets.status_badge import StatusBadge


class ManualReviewView(QWidget):
    """
    Operational view for records requiring manual attention.

    This view is presentation-only. It does not interpret business
    rules or modify backend data.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("manualReviewView")

        self._build_ui()
        self._apply_styles()

        self.set_empty_state()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            Spacing.XL,
            Spacing.LG,
            Spacing.XL,
            Spacing.XL,
        )
        root_layout.setSpacing(
            Spacing.LG
        )

        title = QLabel(
            "Manual Review",
            self,
        )
        title.setObjectName(
            "manualReviewTitle"
        )

        description = QLabel(
            "Inspect records that require operational attention "
            "before completing the weekly process.",
            self,
        )
        description.setObjectName(
            "manualReviewDescription"
        )
        description.setWordWrap(True)

        root_layout.addWidget(title)
        root_layout.addWidget(description)

        root_layout.addWidget(
            self._build_summary_card()
        )

        root_layout.addWidget(
            self._build_review_card()
        )

        root_layout.addStretch()

    def _build_summary_card(self) -> Card:
        card = Card(
            title="Review Summary",
            subtitle="Current manual review status.",
        )

        container = QWidget(card)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        layout.setSpacing(Spacing.MD)

        self.summary_status = StatusBadge(
            "No review required",
            container,
            tone="success",
            uppercase=False,
        )

        self.summary_count = QLabel(
            "No records require manual review.",
            container,
        )
        self.summary_count.setObjectName(
            "manualReviewSummaryCount"
        )

        self.summary_context = QLabel(
            "Latest run: -",
            container,
        )
        self.summary_context.setObjectName(
            "manualReviewSummaryContext"
        )

        layout.addWidget(
            self.summary_status,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        layout.addWidget(
            self.summary_count
        )
        layout.addWidget(
            self.summary_context
        )

        card.add_widget(container)

        return card

    def _build_review_card(self) -> Card:
        card = Card(
            title="Review Items",
            subtitle=(
                "Records requiring manual attention in the latest run."
            ),
        )

        self.review_table = QTableWidget(
            0,
            7,
            card,
        )

        self.review_table.setHorizontalHeaderLabels(
            (
                "Client",
                "Project / Session",
                "Country",
                "Date",
                "Reason",
                "Suggested Action",
                "Status",
            )
        )

        self.review_table.verticalHeader().setVisible(
            False
        )

        self.review_table.setAlternatingRowColors(
            True
        )

        self.review_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.review_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.review_table.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        header = self.review_table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            6,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        self.review_table.setMinimumHeight(
            240
        )

        card.add_widget(
            self.review_table
        )

        return card

    def apply_state(
        self,
        state: ManualReviewState,
    ) -> None:
        """
        Apply presentation-ready manual review state.
        """

        self.summary_context.setText(
            "Latest run: "
            + (
                state.weekly_run_id
                if state.weekly_run_id
                else "-"
            )
            + " · "
            + state.environment
        )

        if not state.requires_review:
            self.review_table.setRowCount(0)

            self.summary_status.set_status(
                text="No review required",
                tone="success",
            )

            self.summary_count.setText(
                state.message
                or "No records require manual review."
            )

            return

        self.summary_status.set_status(
            text="Attention required",
            tone="warning",
        )

        self.summary_count.setText(
            state.message
        )

        self.review_table.setRowCount(
            len(state.items)
        )

        for row_index, review_item in enumerate(
            state.items
        ):
            values = (
                review_item.client_name,
                review_item.project_name,
                review_item.country,
                review_item.start_date,
                review_item.decision_reason,
                review_item.suggested_action,
                review_item.decision,
            )

            for column_index, value in enumerate(
                values
            ):
                item = QTableWidgetItem(
                    value
                )

                if column_index == 6:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                self.review_table.setItem(
                    row_index,
                    column_index,
                    item,
                )

            self.review_table.setRowHeight(
                row_index,
                52,
            )

    def set_preview_state(self) -> None:
        """
        Temporary preview state used only by the isolated preview.
        """

        self.review_table.setRowCount(1)

        self.summary_status.set_status(
            text="Attention required",
            tone="warning",
        )

        self.summary_count.setText(
            "1 record requires manual review."
        )

        self.summary_context.setText(
            "Latest run: NPS_WEEK_2026-08-04_2026-08-10 · TEST"
        )

        values = (
            "Sample Client",
            "Leadership Program - Session 4",
            "Mexico",
            "8/6/2026",
            "Manual validation required",
            "Confirm the record before creating the NPS.",
            "REVIEW",
        )

        for column, value in enumerate(values):
            item = QTableWidgetItem(
                value
            )

            if column == 6:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

            self.review_table.setItem(
                0,
                column,
                item,
            )

    def set_empty_state(self) -> None:
        """
        Display a run with no manual-review records.
        """

        self.review_table.setRowCount(0)

        self.summary_status.set_status(
            text="No review required",
            tone="success",
        )

        self.summary_count.setText(
            "No records require manual review."
        )

        self.summary_context.setText(
            "Latest run: -"
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#manualReviewView {{
                background-color: transparent;
            }}

            QLabel#manualReviewTitle {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_PAGE_TITLE}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#manualReviewDescription {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_LARGE}px;
            }}

            QLabel#manualReviewSummaryCount {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_LARGE}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QLabel#manualReviewSummaryContext {{
                color: {Colors.TEXT_MUTED};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
            }}

            QTableWidget {{
                background-color: {Colors.SURFACE};
                alternate-background-color: {Colors.SURFACE_ALT};
                color: {Colors.TEXT_PRIMARY};

                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: 8px;

                gridline-color: {Colors.BORDER_LIGHT};

                selection-background-color: {Colors.BTS_PINK_BACKGROUND};
                selection-color: {Colors.TEXT_PRIMARY};
            }}

            QHeaderView::section {{
                background-color: {Colors.SURFACE_ALT};
                color: {Colors.TEXT_SECONDARY};

                border: none;
                border-bottom: 1px solid {Colors.BORDER};

                padding: {Spacing.SM}px;

                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}
            """
        )