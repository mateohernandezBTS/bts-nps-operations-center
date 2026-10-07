from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.controllers.ui_controller import WeeklyOutputState
from app.theme import (
    Colors,
    Spacing,
    Typography,
)
from app.widgets.card import Card
from app.widgets.secondary_button import SecondaryButton
from app.widgets.status_badge import StatusBadge


class WeeklyOutputView(QWidget):
    """
    Read-only operations center for the latest weekly outputs.

    The view presents:
    - run summary;
    - Slack-ready HTML preview;
    - generated Excel output;
    - manual review details when applicable.

    The backend remains the source of truth for all generated outputs.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("weeklyOutputView")

        self._excel_path = ""

        self._build_ui()
        self._connect_signals()
        self._apply_styles()

        self.set_empty_state()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName(
            "weeklyOutputScrollArea"
        )
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(
            QScrollArea.Shape.NoFrame
        )

        content = QWidget()
        content.setObjectName(
            "weeklyOutputContent"
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
        content_layout.setSpacing(
            Spacing.LG
        )

        title = QLabel(
            "Weekly Output",
            content,
        )
        title.setObjectName(
            "weeklyOutputTitle"
        )

        description = QLabel(
            "Review the latest generated Slack-ready output, "
            "Excel package and any manual-review attention required.",
            content,
        )
        description.setObjectName(
            "weeklyOutputDescription"
        )
        description.setWordWrap(True)

        self.summary_card = (
            self._build_summary_card()
        )
        self.preview_card = (
            self._build_preview_card()
        )
        self.excel_card = (
            self._build_excel_card()
        )
        self.manual_review_card = (
            self._build_manual_review_card()
        )

        content_layout.addWidget(title)
        content_layout.addWidget(description)
        content_layout.addWidget(
            self.summary_card
        )
        content_layout.addWidget(
            self.preview_card
        )
        content_layout.addWidget(
            self.excel_card
        )
        content_layout.addWidget(
            self.manual_review_card
        )
        content_layout.addStretch()

        self.scroll_area.setWidget(content)
        root_layout.addWidget(
            self.scroll_area
        )

    def _build_summary_card(self) -> Card:
        card = Card(
            title="Output Summary",
            subtitle="Latest generated weekly package.",
        )

        container = QWidget(card)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        layout.setSpacing(
            Spacing.SM
        )

        self.status_badge = StatusBadge(
            "No run",
            container,
            tone="neutral",
            uppercase=False,
        )

        self.run_label = QLabel(
            "Run: -",
            container,
        )
        self.run_label.setObjectName(
            "weeklyOutputContext"
        )

        self.environment_label = QLabel(
            "Environment: -",
            container,
        )
        self.environment_label.setObjectName(
            "weeklyOutputContext"
        )

        self.review_label = QLabel(
            "Manual review: 0",
            container,
        )
        self.review_label.setObjectName(
            "weeklyOutputContext"
        )

        self.review_warning = QLabel(
            "",
            container,
        )
        self.review_warning.setObjectName(
            "weeklyOutputWarning"
        )
        self.review_warning.setWordWrap(True)
        self.review_warning.setVisible(False)

        layout.addWidget(
            self.status_badge,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        layout.addWidget(
            self.run_label
        )
        layout.addWidget(
            self.environment_label
        )
        layout.addWidget(
            self.review_label
        )
        layout.addWidget(
            self.review_warning
        )

        card.add_widget(container)

        return card

    def _build_preview_card(self) -> Card:
        card = Card(
            title="Slack Preview",
            subtitle=(
                "Read-only preview of the HTML generated by the backend."
            ),
        )

        self.html_preview = QWebEngineView(
            card
        )
        self.html_preview.setObjectName(
            "weeklyOutputHtmlPreview"
        )
        settings = self.html_preview.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanPaste,
            True,
        )
        self.html_preview.page().featurePermissionRequested.connect(
            self._grant_web_engine_feature_permission
        )
        self.html_preview.setMinimumHeight(
            680
        )

        card.add_widget(
            self.html_preview
        )

        return card

    def _build_excel_card(self) -> Card:
        card = Card(
            title="Excel Output",
            subtitle=(
                "Generated weekly workbook ready for operational use."
            ),
        )

        container = QWidget(card)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        layout.setSpacing(
            Spacing.MD
        )

        self.excel_name_label = QLabel(
            "No Excel output is available.",
            container,
        )
        self.excel_name_label.setObjectName(
            "weeklyOutputExcelName"
        )
        self.excel_name_label.setWordWrap(
            True
        )

        self.open_excel_button = SecondaryButton(
            "Open Excel",
            container,
            minimum_width=160,
        )
        self.open_excel_button.setEnabled(
            False
        )

        self.excel_message = QLabel(
            "",
            container,
        )
        self.excel_message.setObjectName(
            "weeklyOutputFileMessage"
        )
        self.excel_message.setWordWrap(
            True
        )
        self.excel_message.setVisible(
            False
        )

        layout.addWidget(
            self.excel_name_label
        )
        layout.addWidget(
            self.open_excel_button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        layout.addWidget(
            self.excel_message
        )

        card.add_widget(container)

        return card

    def _build_manual_review_card(
        self,
    ) -> Card:
        card = Card(
            title="Manual Review",
            subtitle=(
                "Operational exceptions requiring attention "
                "before finalizing the weekly process."
            ),
        )

        self.manual_review_table = (
            QTableWidget(
                0,
                6,
                card,
            )
        )

        self.manual_review_table.setHorizontalHeaderLabels(
            (
                "Client",
                "Project / Session",
                "Country",
                "Date",
                "Reason",
                "Suggested Action",
            )
        )

        self.manual_review_table.verticalHeader().setVisible(
            False
        )

        self.manual_review_table.setAlternatingRowColors(
            True
        )

        self.manual_review_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.manual_review_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.manual_review_table.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        self.manual_review_table.setWordWrap(
            True
        )

        header = (
            self.manual_review_table
            .horizontalHeader()
        )

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

        self.manual_review_table.setMinimumHeight(
            300
        )

        card.add_widget(
            self.manual_review_table
        )

        return card

    def _connect_signals(self) -> None:
        self.open_excel_button.clicked.connect(
            self._open_excel
        )

    def apply_state(
        self,
        state: WeeklyOutputState,
    ) -> None:
        """
        Apply presentation-ready output state.
        """

        self._excel_path = (
            state.excel_path or ""
        )

        self.run_label.setText(
            "Run: "
            + (
                state.weekly_run_id
                if state.weekly_run_id
                else "-"
            )
        )

        self.environment_label.setText(
            f"Environment: {state.environment}"
        )

        self.review_label.setText(
            f"Manual review: "
            f"{state.manual_review_count}"
        )

        normalized_status = (
            state.status or "NO RUN"
        ).upper()

        if normalized_status in {
            "COMPLETED",
            "COMPLETED_WITH_REVIEW",
        }:
            tone = "success"
        elif normalized_status == "BLOCKED":
            tone = "warning"
        elif normalized_status in {
            "FAILED",
            "ERROR",
        }:
            tone = "error"
        else:
            tone = "neutral"

        self.status_badge.set_status(
            text=self._display_status(
                normalized_status
            ),
            tone=tone,
        )

        self._apply_html_state(
            state
        )
        self._apply_excel_state(
            state
        )
        self._apply_manual_review_state(
            state
        )

    def _apply_html_state(
        self,
        state: WeeklyOutputState,
    ) -> None:
        if state.html_content:
            self.html_preview.setHtml(
                state.html_content
            )
            return

        self.html_preview.setHtml(
            """
            <div style="
                font-family: Segoe UI;
                color: #667085;
                padding: 24px;
            ">
                No HTML output is available for the latest run.
            </div>
            """
        )

    def _apply_excel_state(
        self,
        state: WeeklyOutputState,
    ) -> None:
        excel_path_text = (
            state.excel_path or ""
        )

        if not excel_path_text:
            self.excel_name_label.setText(
                "No Excel output is available."
            )
            self.open_excel_button.setEnabled(
                False
            )
            return

        excel_path = Path(
            excel_path_text
        )

        self.excel_name_label.setText(
            excel_path.name
        )
        self.excel_name_label.setToolTip(
            excel_path_text
        )

        self.open_excel_button.setEnabled(
            excel_path.exists()
        )

    def _apply_manual_review_state(
        self,
        state: WeeklyOutputState,
    ) -> None:
        items = tuple(
            state.manual_review_items or ()
        )

        self.manual_review_table.clearContents()
        self.manual_review_table.setRowCount(
            0
        )

        if not state.requires_manual_review:
            self.review_warning.clear()
            self.review_warning.setVisible(
                False
            )
            self.manual_review_card.setVisible(
                False
            )
            return

        count = state.manual_review_count

        self.review_warning.setText(
            f"⚠ {count} "
            f"{'record requires' if count == 1 else 'records require'} "
            "manual review before the weekly operation is finalized."
        )
        self.review_warning.setVisible(
            True
        )

        self.manual_review_card.setVisible(
            True
        )

        self.manual_review_table.setRowCount(
            len(items)
        )

        for row_index, review_item in enumerate(
            items
        ):
            values = (
                review_item.client_name,
                review_item.project_name,
                review_item.country,
                review_item.start_date,
                review_item.decision_reason,
                review_item.suggested_action,
            )

            for column_index, value in enumerate(
                values
            ):
                table_item = QTableWidgetItem(
                    value
                )

                table_item.setToolTip(
                    value
                )

                self.manual_review_table.setItem(
                    row_index,
                    column_index,
                    table_item,
                )

        self.manual_review_table.resizeRowsToContents()

        for row_index in range(
            self.manual_review_table.rowCount()
        ):
            if (
                self.manual_review_table.rowHeight(
                    row_index
                )
                < 56
            ):
                self.manual_review_table.setRowHeight(
                    row_index,
                    56,
                )

    def _open_excel(self) -> None:
        """
        Open the generated workbook with the system default application.
        """

        self.excel_message.clear()
        self.excel_message.setVisible(
            False
        )

        if not self._excel_path:
            return

        excel_path = Path(
            self._excel_path
        )

        if not excel_path.exists():
            self.excel_message.setText(
                "The generated Excel file could not be found."
            )
            self.excel_message.setVisible(
                True
            )
            self.open_excel_button.setEnabled(
                False
            )
            return

        opened = QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(excel_path.resolve())
            )
        )

        if not opened:
            self.excel_message.setText(
                "Windows could not open the generated Excel file."
            )
            self.excel_message.setVisible(
                True
            )

    def _grant_web_engine_feature_permission(
        self,
        security_origin: QUrl,
        feature: QWebEnginePage.Feature,
    ) -> None:
        if feature != QWebEnginePage.Feature.ClipboardReadWrite:
            return

        self.html_preview.page().setFeaturePermission(
            security_origin,
            feature,
            QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
        )

    def set_empty_state(self) -> None:
        self._excel_path = ""

        self.status_badge.set_status(
            text="No run",
            tone="neutral",
        )

        self.run_label.setText(
            "Run: -"
        )
        self.environment_label.setText(
            "Environment: -"
        )
        self.review_label.setText(
            "Manual review: 0"
        )

        self.review_warning.clear()
        self.review_warning.setVisible(
            False
        )

        self.html_preview.setHtml(
            """
            <div style="
                font-family: Segoe UI;
                color: #667085;
                padding: 24px;
            ">
                No weekly output is available yet.
            </div>
            """
        )

        self.excel_name_label.setText(
            "No Excel output is available."
        )
        self.excel_name_label.setToolTip(
            ""
        )
        self.open_excel_button.setEnabled(
            False
        )

        self.excel_message.clear()
        self.excel_message.setVisible(
            False
        )

        self.manual_review_table.clearContents()
        self.manual_review_table.setRowCount(
            0
        )
        self.manual_review_card.setVisible(
            False
        )

    @staticmethod
    def _display_status(
        status: str,
    ) -> str:
        return (
            (status or "NO RUN")
            .replace("_", " ")
            .strip()
            .title()
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#weeklyOutputView,
            QWidget#weeklyOutputContent {{
                background-color: transparent;
            }}

            QScrollArea#weeklyOutputScrollArea {{
                background-color: {Colors.APP_BACKGROUND};
                border: none;
            }}

            QScrollArea#weeklyOutputScrollArea
            > QWidget > QWidget {{
                background-color: {Colors.APP_BACKGROUND};
            }}

            QLabel#weeklyOutputTitle {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_PAGE_TITLE}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#weeklyOutputDescription {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_LARGE}px;
            }}

            QLabel#weeklyOutputContext {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
            }}

            QLabel#weeklyOutputExcelName {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_LARGE}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QLabel#weeklyOutputWarning {{
                color: {Colors.WARNING};
                background-color: {Colors.WARNING_BACKGROUND};
                border: 1px solid {Colors.WARNING};
                border-radius: 6px;
                padding: {Spacing.SM}px;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QLabel#weeklyOutputFileMessage {{
                color: {Colors.ERROR};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
            }}

            QWebEngineView#weeklyOutputHtmlPreview {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: 8px;
                padding: {Spacing.SM}px;
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
