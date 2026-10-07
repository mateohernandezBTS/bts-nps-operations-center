from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
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


class WeeklyRunView(QWidget):
    """
    Operational screen for preparing a SELAM weekly NPS run.

    The user may select any calendar date. The view derives the
    corresponding reference Monday and weekly processing window.

    Backend execution is requested through signals. This view does not
    call the engine or contain NPS business logic.
    """

    preflight_requested = Signal(str, bool)
    weekly_process_requested = Signal(str, bool)

    EXPECTED_SOURCES = (
        "Argentina Upcoming NPS",
        "Brazil Upcoming NPS",
        "Mexico Upcoming NPS",
    )

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("weeklyRunView")

        self._source_badges: list[StatusBadge] = []
        self._reference_monday: date | None = None
        self._window_start: date | None = None
        self._window_end: date | None = None

        self._build_ui()
        self._connect_signals()
        self._apply_styles()

        self._set_default_reference_date()
        self.environment_combo.setCurrentText("PRODUCTION")
        self._handle_environment_change("PRODUCTION")
        self._update_window_preview()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("weeklyRunScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        content = QWidget()
        content.setObjectName("weeklyRunContent")
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
            "Prepare Weekly Process",
            content,
        )
        section_title.setObjectName("weeklyRunSectionTitle")

        section_description = QLabel(
            "Select a reference date, validate all expected sources "
            "and run preflight before starting the weekly process.",
            content,
        )
        section_description.setObjectName(
            "weeklyRunSectionDescription"
        )
        section_description.setWordWrap(True)

        content_layout.addWidget(section_title)
        content_layout.addWidget(section_description)
        content_layout.addWidget(self._build_setup_card())
        content_layout.addWidget(self._build_sources_card())
        content_layout.addWidget(self._build_preflight_card())
        content_layout.addWidget(self._build_actions_card())
        content_layout.addStretch()

        self.scroll_area.setWidget(content)
        outer_layout.addWidget(self.scroll_area)

    def _build_setup_card(self) -> Card:
        card = Card(
            title="Run Configuration",
            subtitle="Define the execution date and environment.",
        )

        form = QWidget(card)
        form.setObjectName("weeklyRunForm")

        form_layout = QGridLayout(form)
        form_layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        form_layout.setHorizontalSpacing(Spacing.XL)
        form_layout.setVerticalSpacing(Spacing.MD)

        reference_date_label = QLabel(
            "Reference Date",
            form,
        )
        reference_date_label.setObjectName(
            "weeklyRunFieldLabel"
        )

        self.reference_date_edit = QDateEdit(form)
        self.reference_date_edit.setObjectName(
            "weeklyRunDateEdit"
        )
        self.reference_date_edit.setCalendarPopup(True)

        calendar = self.reference_date_edit.calendarWidget()

        calendar_palette = calendar.palette()
        calendar_palette.setColor(
            QPalette.ColorRole.Window,
            QColor(Colors.SURFACE),
        )
        calendar_palette.setColor(
            QPalette.ColorRole.Base,
            QColor(Colors.SURFACE),
        )
        calendar_palette.setColor(
            QPalette.ColorRole.AlternateBase,
            QColor(Colors.SURFACE),
        )
        calendar_palette.setColor(
            QPalette.ColorRole.Text,
            QColor(Colors.TEXT_PRIMARY),
        )
        calendar_palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor(Colors.TEXT_PRIMARY),
        )
        calendar_palette.setColor(
            QPalette.ColorRole.ButtonText,
            QColor(Colors.TEXT_PRIMARY),
        )
        calendar_palette.setColor(
            QPalette.ColorRole.Highlight,
            QColor(Colors.INFO),
        )
        calendar_palette.setColor(
            QPalette.ColorRole.HighlightedText,
            QColor(Colors.TEXT_ON_ACCENT),
        )
        calendar.setPalette(calendar_palette)

        self.reference_date_edit.setKeyboardTracking(False)
        self.reference_date_edit.setDisplayFormat("M/d/yyyy")
        self.reference_date_edit.setMinimumWidth(190)

        environment_label = QLabel(
            "Environment",
            form,
        )
        environment_label.setObjectName(
            "weeklyRunFieldLabel"
        )

        self.environment_combo = QComboBox(form)
        self.environment_combo.setObjectName(
            "weeklyRunEnvironmentCombo"
        )
        self.environment_combo.addItems(
            (
                "PRODUCTION",
                "TEST",
            )
        )
        self.environment_combo.setMinimumWidth(190)

        reference_monday_label = QLabel(
            "Reference Monday",
            form,
        )
        reference_monday_label.setObjectName(
            "weeklyRunFieldLabel"
        )

        self.reference_monday_value = QLabel(
            "-",
            form,
        )
        self.reference_monday_value.setObjectName(
            "weeklyRunFieldValue"
        )

        execution_mode_label = QLabel(
            "Execution Mode",
            form,
        )
        execution_mode_label.setObjectName(
            "weeklyRunFieldLabel"
        )

        self.environment_badge = StatusBadge(
            "PRODUCTION",
            form,
            tone="error",
        )

        weekly_window_label = QLabel(
            "Weekly Window",
            form,
        )
        weekly_window_label.setObjectName(
            "weeklyRunFieldLabel"
        )

        self.window_value = QLabel(
            "-",
            form,
        )
        self.window_value.setObjectName(
            "weeklyRunFieldValue"
        )

        selected_date_help = QLabel(
            "Any calendar date can be selected. The corresponding "
            "Monday is calculated automatically.",
            form,
        )
        selected_date_help.setObjectName(
            "weeklyRunHelpText"
        )
        selected_date_help.setWordWrap(True)

        form_layout.addWidget(
            reference_date_label,
            0,
            0,
        )
        form_layout.addWidget(
            self.reference_date_edit,
            0,
            1,
        )
        form_layout.addWidget(
            environment_label,
            0,
            2,
        )
        form_layout.addWidget(
            self.environment_combo,
            0,
            3,
        )

        form_layout.addWidget(
            reference_monday_label,
            1,
            0,
        )
        form_layout.addWidget(
            self.reference_monday_value,
            1,
            1,
        )
        form_layout.addWidget(
            execution_mode_label,
            1,
            2,
        )
        form_layout.addWidget(
            self.environment_badge,
            1,
            3,
            Qt.AlignmentFlag.AlignLeft,
        )

        form_layout.addWidget(
            weekly_window_label,
            2,
            0,
        )
        form_layout.addWidget(
            self.window_value,
            2,
            1,
        )
        form_layout.addWidget(
            selected_date_help,
            2,
            2,
            1,
            2,
        )

        form_layout.setColumnStretch(1, 1)
        form_layout.setColumnStretch(3, 1)

        card.add_widget(form)

        return card

    def _build_sources_card(self) -> Card:
        card = Card(
            title="Expected Sources",
            subtitle=(
                "Upcoming NPS reports required before the weekly run."
            ),
        )

        sources_container = QWidget(card)
        sources_container.setObjectName(
            "weeklyRunSourcesContainer"
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
            Spacing.MD
        )

        for row, source_name in enumerate(
            self.EXPECTED_SOURCES
        ):
            indicator = QLabel(
                "●",
                sources_container,
            )
            indicator.setObjectName(
                "weeklyRunSourceIndicator"
            )

            source_label = QLabel(
                source_name,
                sources_container,
            )
            source_label.setObjectName(
                "weeklyRunSourceLabel"
            )

            source_badge = StatusBadge(
                "Not checked",
                sources_container,
                tone="neutral",
                uppercase=False,
            )

            self._source_badges.append(
                source_badge
            )

            sources_layout.addWidget(
                indicator,
                row,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )
            sources_layout.addWidget(
                source_label,
                row,
                1,
                Qt.AlignmentFlag.AlignVCenter,
            )
            sources_layout.addWidget(
                source_badge,
                row,
                2,
                Qt.AlignmentFlag.AlignVCenter,
            )

        sources_layout.setColumnStretch(1, 1)

        card.add_widget(sources_container)

        return card

    def _build_preflight_card(self) -> Card:
        card = Card(
            title="Preflight Validation",
            subtitle=(
                "Preflight checks source completeness, duplicates, "
                "unknown reports and the weekly window."
            ),
        )

        status_container = QWidget(card)
        status_container.setObjectName(
            "weeklyRunPreflightContainer"
        )

        status_layout = QVBoxLayout(
            status_container
        )
        status_layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        status_layout.setSpacing(Spacing.MD)

        status_row = QWidget(
            status_container
        )
        status_row.setObjectName(
            "weeklyRunStatusRow"
        )

        status_row_layout = QHBoxLayout(
            status_row
        )
        status_row_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        status_row_layout.setSpacing(
            Spacing.SM
        )

        status_label = QLabel(
            "Status",
            status_row,
        )
        status_label.setObjectName(
            "weeklyRunFieldLabel"
        )

        self.preflight_badge = StatusBadge(
            "Not run",
            status_row,
            tone="neutral",
            uppercase=False,
        )

        status_row_layout.addWidget(
            status_label
        )
        status_row_layout.addStretch()
        status_row_layout.addWidget(
            self.preflight_badge
        )

        self.preflight_message = QLabel(
            "Run preflight to validate the selected weekly process.",
            status_container,
        )
        self.preflight_message.setObjectName(
            "weeklyRunMessage"
        )
        self.preflight_message.setWordWrap(True)

        self.issues_title = QLabel(
            "Issues",
            status_container,
        )
        self.issues_title.setObjectName(
            "weeklyRunIssuesTitle"
        )

        self.issues_label = QLabel(
            "No issues detected.",
            status_container,
        )
        self.issues_label.setObjectName(
            "weeklyRunIssuesText"
        )
        self.issues_label.setWordWrap(True)

        status_layout.addWidget(status_row)
        status_layout.addWidget(
            self.preflight_message
        )
        status_layout.addSpacing(Spacing.XS)
        status_layout.addWidget(
            self.issues_title
        )
        status_layout.addWidget(
            self.issues_label
        )

        card.add_widget(status_container)

        return card

    def _build_actions_card(self) -> Card:
        card = Card(
            title="Process Actions",
            subtitle=(
                "Preflight must finish successfully before processing."
            ),
        )

        actions_container = QWidget(card)
        actions_container.setObjectName(
            "weeklyRunActionsContainer"
        )

        actions_layout = QHBoxLayout(
            actions_container
        )
        actions_layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        actions_layout.setSpacing(Spacing.MD)

        self.preflight_button = QPushButton(
            "Run Preflight",
            actions_container,
        )
        self.preflight_button.setObjectName(
            "weeklyRunPrimaryButton"
        )
        self.preflight_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.preflight_button.setMinimumHeight(40)

        self.process_button = QPushButton(
            "Run Weekly Process",
            actions_container,
        )
        self.process_button.setObjectName(
            "weeklyRunProcessButton"
        )
        self.process_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.process_button.setMinimumHeight(40)
        self.process_button.setEnabled(False)

        self.production_warning = QLabel(
            "Production mode writes operational outputs.",
            actions_container,
        )
        self.production_warning.setObjectName(
            "weeklyRunProductionWarning"
        )
        self.production_warning.setWordWrap(True)
        self.production_warning.setVisible(True)

        actions_layout.addWidget(
            self.preflight_button
        )
        actions_layout.addWidget(
            self.process_button
        )
        actions_layout.addSpacing(
            Spacing.MD
        )
        actions_layout.addWidget(
            self.production_warning
        )
        actions_layout.addStretch()

        card.add_widget(actions_container)

        return card

    def _connect_signals(self) -> None:
        self.reference_date_edit.dateChanged.connect(
            self._update_window_preview
        )

        self.environment_combo.currentTextChanged.connect(
            self._handle_environment_change
        )

        self.preflight_button.clicked.connect(
            self._emit_preflight_request
        )

        self.process_button.clicked.connect(
            self._emit_process_request
        )

    def _set_default_reference_date(self) -> None:
        today = date.today()

        self.reference_date_edit.setDate(
            QDate(
                today.year,
                today.month,
                today.day,
            )
        )

    def _update_window_preview(self) -> None:
        selected_date = (
            self.reference_date_edit
            .date()
            .toPython()
        )

        self._reference_monday = (
            selected_date
            - timedelta(
                days=selected_date.weekday()
            )
        )

        self._window_start = (
            self._reference_monday
            + timedelta(days=1)
        )

        self._window_end = (
            self._reference_monday
            + timedelta(days=7)
        )

        self.reference_monday_value.setText(
            self._format_date(
                self._reference_monday
            )
        )

        self.window_value.setText(
            f"{self._format_date(self._window_start)}"
            " - "
            f"{self._format_date(self._window_end)}"
        )

        self.set_idle_state()

    def _handle_environment_change(
        self,
        environment: str,
    ) -> None:
        normalized = environment.upper()

        if normalized == "PRODUCTION":
            self.environment_badge.set_status(
                text="PRODUCTION",
                tone="error",
            )
            self.production_warning.setVisible(
                True
            )
        else:
            self.environment_badge.set_status(
                text="TEST",
                tone="info",
            )
            self.production_warning.setVisible(
                False
            )

        self.set_idle_state()

    def _emit_preflight_request(self) -> None:
        self.preflight_requested.emit(
            self.reference_date_text(),
            self.is_test_mode(),
        )

    def _emit_process_request(self) -> None:
        self.weekly_process_requested.emit(
            self.reference_date_text(),
            self.is_test_mode(),
        )

    def selected_date_text(self) -> str:
        selected = self.reference_date_edit.date()

        return (
            f"{selected.month()}/"
            f"{selected.day()}/"
            f"{selected.year()}"
        )

    def reference_date_text(self) -> str:
        if self._reference_monday is None:
            self._update_window_preview()

        assert self._reference_monday is not None

        return self._format_date(
            self._reference_monday
        )

    def weekly_window_text(self) -> str:
        if (
            self._window_start is None
            or self._window_end is None
        ):
            self._update_window_preview()

        assert self._window_start is not None
        assert self._window_end is not None

        return (
            f"{self._format_date(self._window_start)}"
            " - "
            f"{self._format_date(self._window_end)}"
        )

    def is_test_mode(self) -> bool:
        return (
            self.environment_combo
            .currentText()
            .upper()
            == "TEST"
        )

    def set_idle_state(self) -> None:
        self.preflight_badge.set_status(
            text="Not run",
            tone="neutral",
        )

        self.preflight_message.setText(
            "Run preflight to validate the selected weekly process."
        )

        self.issues_label.setText(
            "No issues detected."
        )

        self.preflight_button.setEnabled(True)
        self.process_button.setEnabled(False)

        for badge in self._source_badges:
            badge.set_status(
                text="Not checked",
                tone="neutral",
            )

    def set_preflight_running(self) -> None:
        self.preflight_badge.set_status(
            text="Running",
            tone="info",
        )

        self.preflight_message.setText(
            "Validating weekly sources and execution conditions..."
        )

        self.issues_label.setText(
            "Validation in progress."
        )

        self.preflight_button.setEnabled(False)
        self.process_button.setEnabled(False)

    def set_processing_running(self) -> None:
        self.preflight_badge.set_status(
            text="Processing",
            tone="info",
        )

        self.preflight_message.setText(
            "The weekly process is currently running."
        )

        self.issues_label.setText(
            "Weekly processing in progress."
        )

        self.preflight_button.setEnabled(False)
        self.process_button.setEnabled(False)

    def set_preflight_result(
        self,
        *,
        ready: bool,
        status: str,
        message: str,
        issues: tuple[str, ...] = (),
        sources_received: int = 0,
    ) -> None:
        tone = (
            "success"
            if ready
            else "warning"
        )

        self.preflight_badge.set_status(
            text=self._display_status(status),
            tone=tone,
        )

        self.preflight_message.setText(message)

        self.issues_label.setText(
            "\n".join(
                f"• {issue}"
                for issue in issues
            )
            if issues
            else "No issues detected."
        )

        self.preflight_button.setEnabled(True)
        self.process_button.setEnabled(ready)

        for index, badge in enumerate(
            self._source_badges
        ):
            received = (
                index < sources_received
            )

            badge.set_status(
                text=(
                    "Received"
                    if received
                    else "Missing"
                ),
                tone=(
                    "success"
                    if received
                    else "error"
                ),
            )

    def set_process_result(
        self,
        *,
        success: bool,
        status: str,
        message: str,
        issues: tuple[str, ...] = (),
    ) -> None:
        tone = (
            "success"
            if success
            else "error"
        )

        self.preflight_badge.set_status(
            text=self._display_status(status),
            tone=tone,
        )

        self.preflight_message.setText(
            message
        )

        self.issues_label.setText(
            "\n".join(
                f"• {issue}"
                for issue in issues
            )
            if issues
            else "No processing issues."
        )

        self.preflight_button.setEnabled(True)
        self.process_button.setEnabled(False)

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
    def _format_date(
        value: date,
    ) -> str:
        return (
            f"{value.month}/"
            f"{value.day}/"
            f"{value.year}"
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#weeklyRunView,
            QWidget#weeklyRunContent,
            QWidget#weeklyRunForm,
            QWidget#weeklyRunSourcesContainer,
            QWidget#weeklyRunPreflightContainer,
            QWidget#weeklyRunStatusRow,
            QWidget#weeklyRunActionsContainer {{
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
                color: {Colors.BTS_NAVY};
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

            QLabel#weeklyRunFieldLabel,
            QLabel#weeklyRunIssuesTitle {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QLabel#weeklyRunFieldValue {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_MEDIUM};
            }}

            QLabel#weeklyRunHelpText {{
                color: {Colors.TEXT_MUTED};
                background-color: transparent;
                font-size: {Typography.SIZE_CAPTION}px;
                font-weight: {Typography.WEIGHT_NORMAL};
            }}

            QLabel#weeklyRunSourceIndicator {{
                color: {Colors.INFO};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#weeklyRunSourceLabel {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
            }}

            QLabel#weeklyRunMessage {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
            }}

            QLabel#weeklyRunIssuesText {{
                color: {Colors.TEXT_SECONDARY};
                background-color: {Colors.SURFACE_ALT};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {Radius.SMALL}px;
                padding: {Spacing.SM}px;
                font-size: {Typography.SIZE_BODY_SMALL}px;
            }}

            QLabel#weeklyRunProductionWarning {{
                color: {Colors.ERROR};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QPushButton#weeklyRunPrimaryButton {{
                background-color: {Colors.BTS_RED};
                color: {Colors.TEXT_ON_ACCENT};
                border: none;
                border-radius: {Radius.SMALL}px;
                min-width: 165px;
                padding: 0 {Spacing.LG}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QPushButton#weeklyRunPrimaryButton:hover {{
                background-color: {Colors.BTS_RED_HOVER};
            }}

            QPushButton#weeklyRunPrimaryButton:disabled {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_MUTED};
            }}

            QPushButton#weeklyRunProcessButton {{
                background-color: {Colors.BTS_RED};
                color: {Colors.TEXT_ON_ACCENT};
                border: none;
                border-radius: {Radius.SMALL}px;
                min-width: 190px;
                padding: 0 {Spacing.LG}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QPushButton#weeklyRunProcessButton:hover {{
                background-color: {Colors.BTS_RED_HOVER};
            }}

            QPushButton#weeklyRunProcessButton:disabled {{
                background-color: {Colors.SURFACE_ALT};
                color: {Colors.TEXT_MUTED};
                border: 1px solid {Colors.BORDER};
            }}

            QDateEdit#weeklyRunDateEdit,
            QComboBox#weeklyRunEnvironmentCombo {{
                min-height: 38px;
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.SMALL}px;
                padding: 0 36px 0 {Spacing.SM}px;
                selection-background-color: {Colors.INFO_BACKGROUND};
                selection-color: {Colors.TEXT_PRIMARY};
            }}

            QDateEdit#weeklyRunDateEdit:hover,
            QComboBox#weeklyRunEnvironmentCombo:hover {{
                border-color: {Colors.INFO};
            }}

            QDateEdit#weeklyRunDateEdit:focus,
            QComboBox#weeklyRunEnvironmentCombo:focus {{
                border: 1px solid {Colors.INFO};
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}

            QDateEdit#weeklyRunDateEdit::drop-down,
            QComboBox#weeklyRunEnvironmentCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                background-color: {Colors.SURFACE_ALT};
                border: none;
                border-left: 1px solid {Colors.BORDER_LIGHT};
                border-top-right-radius: {Radius.SMALL}px;
                border-bottom-right-radius: {Radius.SMALL}px;
            }}

            QDateEdit#weeklyRunDateEdit::drop-down:hover,
            QComboBox#weeklyRunEnvironmentCombo::drop-down:hover {{
                background-color: {Colors.INFO_BACKGROUND};
            }}

            QComboBox#weeklyRunEnvironmentCombo QAbstractItemView {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.SMALL}px;
                padding: 4px;
                outline: none;
                selection-background-color: {Colors.INFO_BACKGROUND};
                selection-color: {Colors.TEXT_PRIMARY};
            }}

            QComboBox#weeklyRunEnvironmentCombo QAbstractItemView::item {{
                min-height: 34px;
                padding: 4px 10px;
                border: none;
            }}

            QComboBox#weeklyRunEnvironmentCombo QAbstractItemView::item:hover {{
                background-color: {Colors.SURFACE_ALT};
                color: {Colors.TEXT_PRIMARY};
            }}

            QComboBox#weeklyRunEnvironmentCombo QAbstractItemView::item:selected {{
                background-color: {Colors.INFO_BACKGROUND};
                color: {Colors.INFO};
            }}

            QCalendarWidget {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}

            QCalendarWidget QWidget {{
                alternate-background-color: {Colors.SURFACE};
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}

            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {Colors.BTS_NAVY};
                color: {Colors.TEXT_ON_DARK};
                min-height: 36px;
            }}

            QCalendarWidget QToolButton {{
                background-color: transparent;
                color: {Colors.TEXT_ON_DARK};
                border: none;
                border-radius: {Radius.SMALL}px;
                padding: 6px 10px;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QCalendarWidget QToolButton:hover {{
                background-color: {Colors.BTS_NAVY_LIGHT};
            }}

            QCalendarWidget QToolButton::menu-indicator {{
                image: none;
            }}

            QCalendarWidget QMenu {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
            }}

            QCalendarWidget QSpinBox {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.SMALL}px;
                padding: 4px;
                selection-background-color: {Colors.INFO_BACKGROUND};
                selection-color: {Colors.TEXT_PRIMARY};
            }}

            QCalendarWidget QAbstractItemView {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                alternate-background-color: {Colors.SURFACE};
                selection-background-color: {Colors.INFO};
                selection-color: {Colors.TEXT_ON_ACCENT};
                border: none;
                outline: none;
            }}

            QCalendarWidget QAbstractItemView:enabled {{
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.SURFACE};
            }}

            QCalendarWidget QAbstractItemView:disabled {{
                color: {Colors.TEXT_MUTED};
            }}
            """
        )