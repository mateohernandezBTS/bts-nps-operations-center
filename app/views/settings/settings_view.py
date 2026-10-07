from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.controllers.ui_controller import SettingsState
from app.theme import (
    Colors,
    Spacing,
    Typography,
)
from app.widgets.card import Card
from app.widgets.secondary_button import SecondaryButton
from app.widgets.status_badge import StatusBadge


class SettingsView(QWidget):
    """
    Read-only application settings and operational state.

    The only active control is Reset Current Session.

    The page uses an internal scroll area so cards are never vertically
    compressed by the application window.
    """

    reset_session_requested = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("settingsView")

        self._build_ui()
        self._connect_signals()
        self._apply_styles()

        self.set_empty_state()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("settingsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget()
        content.setObjectName("settingsContent")
        content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(
            Spacing.XL,
            Spacing.LG,
            Spacing.XL,
            Spacing.XL,
        )
        content_layout.setSpacing(Spacing.LG)
        content_layout.setSizeConstraint(
            QVBoxLayout.SizeConstraint.SetMinimumSize
        )

        title = QLabel("Settings", content)
        title.setObjectName("settingsTitle")

        description = QLabel(
            "Review application configuration, persisted session "
            "state and storage locations.",
            content,
        )
        description.setObjectName("settingsDescription")
        description.setWordWrap(True)

        application_card = self._build_application_card()
        session_card = self._build_session_card()
        storage_card = self._build_storage_card()

        # Prevent the cards from being compressed below their content.
        application_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        session_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        storage_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        application_card.setMinimumHeight(260)
        session_card.setMinimumHeight(250)
        storage_card.setMinimumHeight(230)

        content_layout.addWidget(title)
        content_layout.addWidget(description)
        content_layout.addWidget(application_card)
        content_layout.addWidget(session_card)
        content_layout.addWidget(storage_card)
        content_layout.addStretch()

        self.scroll_area.setWidget(content)
        root_layout.addWidget(self.scroll_area)

    def _build_application_card(self) -> Card:
        card = Card(
            title="Application",
            subtitle="Current application and backend status.",
        )

        container = QWidget(card)
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        container.setMinimumHeight(155)

        layout = QGridLayout(container)
        layout.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)
        layout.setHorizontalSpacing(Spacing.XL)
        layout.setVerticalSpacing(Spacing.MD)

        version_title = self._make_label("Version")
        environment_title = self._make_label("Environment")
        backend_title = self._make_label("Backend Status")
        session_title = self._make_label("Session Status")

        self.version_value = self._make_value("-")
        self.environment_value = self._make_value("-")

        self.backend_status_badge = StatusBadge(
            "Unknown",
            container,
            tone="neutral",
            uppercase=False,
        )

        self.session_status_badge = StatusBadge(
            "Unknown",
            container,
            tone="neutral",
            uppercase=False,
        )

        layout.addWidget(version_title, 0, 0)
        layout.addWidget(self.version_value, 0, 1)

        layout.addWidget(environment_title, 1, 0)
        layout.addWidget(self.environment_value, 1, 1)

        layout.addWidget(backend_title, 2, 0)
        layout.addWidget(
            self.backend_status_badge,
            2,
            1,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )

        layout.addWidget(session_title, 3, 0)
        layout.addWidget(
            self.session_status_badge,
            3,
            1,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )

        layout.setColumnMinimumWidth(0, 145)
        layout.setColumnStretch(1, 1)

        card.add_widget(container)

        return card

    def _build_session_card(self) -> Card:
        card = Card(
            title="Current Session",
            subtitle="Latest persisted application session.",
        )

        container = QWidget(card)
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        container.setMinimumHeight(155)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)
        layout.setSpacing(Spacing.MD)

        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.XL)
        grid.setVerticalSpacing(Spacing.MD)

        weekly_run_title = self._make_label("Weekly Run ID")
        reference_date_title = self._make_label("Reference Date")
        session_file_title = self._make_label("Session File")

        self.weekly_run_value = self._make_value("-")
        self.reference_date_value = self._make_value("-")
        self.session_file_field = self._make_read_only_field()

        grid.addWidget(weekly_run_title, 0, 0)
        grid.addWidget(self.weekly_run_value, 0, 1)

        grid.addWidget(reference_date_title, 1, 0)
        grid.addWidget(self.reference_date_value, 1, 1)

        grid.addWidget(session_file_title, 2, 0)
        grid.addWidget(self.session_file_field, 2, 1)

        grid.setColumnMinimumWidth(0, 145)
        grid.setColumnStretch(1, 1)

        self.reset_session_button = SecondaryButton(
            "Reset Current Session",
            container,
            minimum_width=190,
        )

        self.reset_help_label = QLabel(
            "Resetting the current session does not delete "
            "weekly outputs or run history.",
            container,
        )
        self.reset_help_label.setObjectName("settingsHelp")
        self.reset_help_label.setWordWrap(True)
        self.reset_help_label.setMinimumHeight(24)

        layout.addLayout(grid)
        layout.addSpacing(Spacing.XS)
        layout.addWidget(
            self.reset_session_button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        layout.addWidget(self.reset_help_label)

        card.add_widget(container)

        return card

    def _build_storage_card(self) -> Card:
        card = Card(
            title="Storage",
            subtitle="Persisted weekly-run and session locations.",
        )

        container = QWidget(card)
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        container.setMinimumHeight(135)

        layout = QGridLayout(container)
        layout.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)
        layout.setHorizontalSpacing(Spacing.XL)
        layout.setVerticalSpacing(Spacing.MD)

        test_title = self._make_label("TEST Weekly Runs")
        production_title = self._make_label("PRODUCTION Weekly Runs")
        session_directory_title = self._make_label("Session Directory")

        self.test_output_field = self._make_read_only_field()
        self.production_output_field = self._make_read_only_field()
        self.session_directory_field = self._make_read_only_field()

        layout.addWidget(test_title, 0, 0)
        layout.addWidget(self.test_output_field, 0, 1)

        layout.addWidget(production_title, 1, 0)
        layout.addWidget(self.production_output_field, 1, 1)

        layout.addWidget(session_directory_title, 2, 0)
        layout.addWidget(self.session_directory_field, 2, 1)

        layout.setColumnMinimumWidth(0, 190)
        layout.setColumnStretch(1, 1)

        card.add_widget(container)

        return card

    def _connect_signals(self) -> None:
        self.reset_session_button.clicked.connect(
            self.reset_session_requested.emit
        )

    def apply_state(
        self,
        state: SettingsState,
    ) -> None:
        """Apply presentation-ready settings state."""

        self.version_value.setText(state.application_version)
        self.environment_value.setText(state.environment)

        self.backend_status_badge.set_status(
            text=self._display_status(state.backend_status),
            tone=self._status_tone(state.backend_status),
        )

        self.session_status_badge.set_status(
            text=self._display_status(state.session_status),
            tone=self._status_tone(state.session_status),
        )

        self.weekly_run_value.setText(
            state.weekly_run_id or "-"
        )

        self.reference_date_value.setText(
            state.reference_date or "-"
        )

        self.session_file_field.setText(state.session_file)
        self.session_file_field.setToolTip(state.session_file)

        self.test_output_field.setText(state.test_output_root)
        self.test_output_field.setToolTip(state.test_output_root)

        self.production_output_field.setText(
            state.production_output_root
        )
        self.production_output_field.setToolTip(
            state.production_output_root
        )

        self.session_directory_field.setText(
            state.session_directory
        )
        self.session_directory_field.setToolTip(
            state.session_directory
        )

    def set_empty_state(self) -> None:
        self.version_value.setText("-")
        self.environment_value.setText("-")

        self.backend_status_badge.set_status(
            text="Unknown",
            tone="neutral",
        )

        self.session_status_badge.set_status(
            text="Unknown",
            tone="neutral",
        )

        self.weekly_run_value.setText("-")
        self.reference_date_value.setText("-")

        self.session_file_field.clear()
        self.test_output_field.clear()
        self.production_output_field.clear()
        self.session_directory_field.clear()

    def _make_label(
        self,
        text: str,
    ) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName("settingsLabel")
        label.setMinimumHeight(24)
        return label

    def _make_value(
        self,
        text: str,
    ) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName("settingsValue")
        label.setMinimumHeight(24)
        return label

    def _make_read_only_field(self) -> QLineEdit:
        field = QLineEdit(self)
        field.setReadOnly(True)
        field.setObjectName("settingsPathField")
        field.setFixedHeight(40)
        field.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        return field

    @staticmethod
    def _display_status(
        status: str,
    ) -> str:
        return (
            (status or "UNKNOWN")
            .replace("_", " ")
            .strip()
            .title()
        )

    @staticmethod
    def _status_tone(
        status: str,
    ) -> str:
        normalized = (status or "").upper()

        if normalized in {"FAILED", "ERROR"}:
            return "error"

        if normalized == "BLOCKED":
            return "warning"

        if normalized in {
            "RUNNING",
            "PROCESSING",
            "STARTED",
            "PREFLIGHT_RUNNING",
        }:
            return "info"

        if normalized in {
            "READY",
            "COMPLETED",
            "COMPLETED_WITH_REVIEW",
        }:
            return "success"

        return "neutral"

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#settingsView,
            QWidget#settingsContent {{
                background-color: transparent;
            }}

            QScrollArea#settingsScrollArea {{
                background-color: {Colors.APP_BACKGROUND};
                border: none;
            }}

            QScrollArea#settingsScrollArea
            > QWidget > QWidget {{
                background-color: {Colors.APP_BACKGROUND};
            }}

            QLabel#settingsTitle {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_PAGE_TITLE}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#settingsDescription {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_LARGE}px;
            }}

            QLabel#settingsLabel {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QLabel#settingsValue {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
            }}

            QLabel#settingsHelp {{
                color: {Colors.TEXT_MUTED};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
            }}

            QLineEdit#settingsPathField {{
                background-color: {Colors.SURFACE_ALT};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: 6px;
                padding: 0 {Spacing.SM}px;
                font-size: {Typography.SIZE_BODY_SMALL}px;
            }}

            QLineEdit#settingsPathField:focus {{
                border: 1px solid {Colors.BTS_PINK};
            }}
            """
        )