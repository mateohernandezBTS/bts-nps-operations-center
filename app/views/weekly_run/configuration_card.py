from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import QDate, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGridLayout,
    QLabel,
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


class ConfigurationCard(Card):
    """
    Weekly Run configuration controls.

    Responsibilities:
    - allow selection of any calendar date;
    - derive the corresponding reference Monday;
    - derive the Tuesday-to-Monday weekly window;
    - expose TEST or PRODUCTION mode;
    - notify the parent view when configuration changes.

    This component contains no backend or NPS processing logic.
    """

    configuration_changed = Signal(str, bool)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(
            parent=parent,
            title="Run Configuration",
            subtitle="Define the execution date and environment.",
        )

        self.setObjectName("weeklyRunConfigurationCard")

        self._reference_monday: date | None = None
        self._window_start: date | None = None
        self._window_end: date | None = None

        self._build_ui()
        self._connect_signals()
        self._apply_styles()

        self._set_default_date()
        self.environment_combo.setCurrentText("TEST")
        self._refresh_configuration(
            emit_signal=False,
        )

    def _build_ui(self) -> None:
        form = QWidget(self)
        form.setObjectName("weeklyRunConfigurationForm")

        layout = QGridLayout(form)
        layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        layout.setHorizontalSpacing(Spacing.XL)
        layout.setVerticalSpacing(Spacing.MD)

        reference_date_label = QLabel(
            "Reference Date",
            form,
        )
        reference_date_label.setObjectName(
            "weeklyRunConfigurationLabel"
        )

        self.reference_date_edit = QDateEdit(form)
        self.reference_date_edit.setObjectName(
            "weeklyRunDateEdit"
        )
        self.reference_date_edit.setCalendarPopup(True)
        self.reference_date_edit.setKeyboardTracking(False)
        self.reference_date_edit.setDisplayFormat("M/d/yyyy")
        self.reference_date_edit.setMinimumWidth(190)

        self._configure_calendar_palette()

        environment_label = QLabel(
            "Environment",
            form,
        )
        environment_label.setObjectName(
            "weeklyRunConfigurationLabel"
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

        environment_view = self.environment_combo.view()

        environment_view.setStyleSheet(
    f"""
    QAbstractItemView {{
        background-color: {Colors.SURFACE};
        color: {Colors.TEXT_PRIMARY};
        border: 1px solid {Colors.BORDER};
        outline: none;
        padding: 4px;
        selection-background-color: {Colors.BTS_PINK_BACKGROUND};
        selection-color: {Colors.TEXT_PRIMARY};
    }}

    QAbstractItemView::item {{
        min-height: 34px;
        padding: 4px 10px;
        background-color: {Colors.SURFACE};
        color: {Colors.TEXT_PRIMARY};
    }}

    QAbstractItemView::item:hover {{
        background-color: {Colors.SURFACE_ALT};
        color: {Colors.TEXT_PRIMARY};
    }}

    QAbstractItemView::item:selected {{
        background-color: {Colors.BTS_PINK_BACKGROUND};
        color: {Colors.BTS_PINK};
    }}
    """
)
        self.environment_combo.setMinimumWidth(190)

        reference_monday_label = QLabel(
            "Reference Monday",
            form,
        )
        reference_monday_label.setObjectName(
            "weeklyRunConfigurationLabel"
        )

        self.reference_monday_value = QLabel(
            "-",
            form,
        )
        self.reference_monday_value.setObjectName(
            "weeklyRunConfigurationValue"
        )

        execution_mode_label = QLabel(
            "Execution Mode",
            form,
        )
        execution_mode_label.setObjectName(
            "weeklyRunConfigurationLabel"
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
            "weeklyRunConfigurationLabel"
        )

        self.window_value = QLabel(
            "-",
            form,
        )
        self.window_value.setObjectName(
            "weeklyRunConfigurationValue"
        )

        help_text = QLabel(
            "Any calendar date can be selected. "
            "The corresponding Monday is calculated automatically.",
            form,
        )
        help_text.setObjectName(
            "weeklyRunConfigurationHelp"
        )
        help_text.setWordWrap(True)

        layout.addWidget(
            reference_date_label,
            0,
            0,
        )
        layout.addWidget(
            self.reference_date_edit,
            0,
            1,
        )
        layout.addWidget(
            environment_label,
            0,
            2,
        )
        layout.addWidget(
            self.environment_combo,
            0,
            3,
        )

        layout.addWidget(
            reference_monday_label,
            1,
            0,
        )
        layout.addWidget(
            self.reference_monday_value,
            1,
            1,
        )
        layout.addWidget(
            execution_mode_label,
            1,
            2,
        )
        layout.addWidget(
            self.environment_badge,
            1,
            3,
        )

        layout.addWidget(
            weekly_window_label,
            2,
            0,
        )
        layout.addWidget(
            self.window_value,
            2,
            1,
        )
        layout.addWidget(
            help_text,
            2,
            2,
            1,
            2,
        )

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        self.add_widget(form)

    def _configure_calendar_palette(self) -> None:
        calendar = self.reference_date_edit.calendarWidget()
        palette = calendar.palette()

        palette.setColor(
            QPalette.ColorRole.Window,
            QColor(Colors.SURFACE),
        )
        palette.setColor(
            QPalette.ColorRole.Base,
            QColor(Colors.SURFACE),
        )
        palette.setColor(
            QPalette.ColorRole.AlternateBase,
            QColor(Colors.SURFACE),
        )
        palette.setColor(
            QPalette.ColorRole.Text,
            QColor(Colors.TEXT_PRIMARY),
        )
        palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor(Colors.TEXT_PRIMARY),
        )
        palette.setColor(
            QPalette.ColorRole.ButtonText,
            QColor(Colors.TEXT_PRIMARY),
        )
        palette.setColor(
            QPalette.ColorRole.Highlight,
            QColor(Colors.BTS_PINK),
        )
        palette.setColor(
            QPalette.ColorRole.HighlightedText,
            QColor(Colors.TEXT_ON_ACCENT),
        )

        calendar.setPalette(palette)
        calendar.setStyleSheet(
    f"""
    QCalendarWidget {{
        background-color: {Colors.SURFACE};
        color: {Colors.TEXT_PRIMARY};
    }}

    QCalendarWidget QWidget {{
        background-color: {Colors.SURFACE};
        color: {Colors.TEXT_PRIMARY};
    }}

    QCalendarWidget QWidget#qt_calendar_navigationbar {{
        background-color: {Colors.BTS_CHARCOAL};
        color: {Colors.TEXT_ON_DARK};
        min-height: 36px;
    }}

    QCalendarWidget QToolButton {{
        background-color: transparent;
        color: {Colors.TEXT_ON_DARK};
        border: none;
        padding: 6px 8px;
        font-weight: {Typography.WEIGHT_SEMIBOLD};
    }}

    QCalendarWidget QToolButton:hover {{
        background-color: {Colors.BTS_CHARCOAL_LIGHT};
    }}

    QCalendarWidget QSpinBox {{
        background-color: {Colors.SURFACE};
        color: {Colors.TEXT_PRIMARY};
        border: 1px solid {Colors.BORDER};
    }}

    QCalendarWidget QAbstractItemView {{
        background-color: {Colors.SURFACE};
        color: {Colors.TEXT_PRIMARY};
        alternate-background-color: {Colors.SURFACE};
        selection-background-color: {Colors.BTS_PINK};
        selection-color: {Colors.TEXT_ON_ACCENT};
        border: none;
        outline: none;
    }}

    QCalendarWidget QAbstractItemView:enabled {{
        background-color: {Colors.SURFACE};
        color: {Colors.TEXT_PRIMARY};
    }}
    """
)

    def _connect_signals(self) -> None:
        self.reference_date_edit.dateChanged.connect(
            self._handle_configuration_change
        )

        self.environment_combo.currentTextChanged.connect(
            self._handle_configuration_change
        )

    def _set_default_date(self) -> None:
        today = date.today()

        self.reference_date_edit.setDate(
            QDate(
                today.year,
                today.month,
                today.day,
            )
        )

    def _handle_configuration_change(self) -> None:
        self._refresh_configuration(
            emit_signal=True,
        )

    def _refresh_configuration(
        self,
        *,
        emit_signal: bool,
    ) -> None:
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

        if self.is_test_mode():
            self.environment_badge.set_status(
                text="TEST",
                tone="info",
            )
        else:
            self.environment_badge.set_status(
                text="PRODUCTION",
                tone="error",
            )

        if emit_signal:
            self.configuration_changed.emit(
                self.reference_date_text(),
                self.is_test_mode(),
            )

    def reference_date_text(self) -> str:
        """
        Return the calculated reference Monday expected by the backend.
        """

        if self._reference_monday is None:
            self._refresh_configuration(
                emit_signal=False,
            )

        assert self._reference_monday is not None

        return self._format_date(
            self._reference_monday
        )

    def selected_date_text(self) -> str:
        """
        Return the date selected directly by the user.
        """

        selected = self.reference_date_edit.date()

        return (
            f"{selected.month()}/"
            f"{selected.day()}/"
            f"{selected.year()}"
        )

    def weekly_window_text(self) -> str:
        """
        Return the calculated Tuesday-to-Monday window.
        """

        if (
            self._window_start is None
            or self._window_end is None
        ):
            self._refresh_configuration(
                emit_signal=False,
            )

        assert self._window_start is not None
        assert self._window_end is not None

        return (
            f"{self._format_date(self._window_start)}"
            " - "
            f"{self._format_date(self._window_end)}"
        )

    def is_test_mode(self) -> bool:
        return (
            self.environment_combo.currentText().upper()
            == "TEST"
        )

    def is_production_mode(self) -> bool:
        return not self.is_test_mode()

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
            QWidget#weeklyRunConfigurationForm {{
                background-color: transparent;
            }}

            QLabel#weeklyRunConfigurationLabel {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QLabel#weeklyRunConfigurationValue {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_MEDIUM};
            }}

            QLabel#weeklyRunConfigurationHelp {{
                color: {Colors.TEXT_MUTED};
                background-color: transparent;
                font-size: {Typography.SIZE_CAPTION}px;
            }}

            QDateEdit#weeklyRunDateEdit,
            QComboBox#weeklyRunEnvironmentCombo {{
                min-height: 38px;
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radius.SMALL}px;
                padding: 0 36px 0 {Spacing.SM}px;
                selection-background-color: {Colors.BTS_PINK_BACKGROUND};
                selection-color: {Colors.TEXT_PRIMARY};
            }}

            QDateEdit#weeklyRunDateEdit:hover,
            QComboBox#weeklyRunEnvironmentCombo:hover {{
                border-color: {Colors.BORDER_STRONG};
            }}

            QDateEdit#weeklyRunDateEdit:focus,
            QComboBox#weeklyRunEnvironmentCombo:focus {{
                border: 1px solid {Colors.BTS_PINK};
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

            QComboBox#weeklyRunEnvironmentCombo QAbstractItemView {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                selection-background-color: {Colors.BTS_PINK_BACKGROUND};
                selection-color: {Colors.TEXT_PRIMARY};
                outline: none;
            }}

            QCalendarWidget {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}

            QCalendarWidget QWidget {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}

            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {Colors.BTS_CHARCOAL};
                color: {Colors.TEXT_ON_DARK};
            }}

            QCalendarWidget QToolButton {{
                background-color: transparent;
                color: {Colors.TEXT_ON_DARK};
                border: none;
                padding: 6px;
            }}

            QCalendarWidget QToolButton:hover {{
                background-color: {Colors.BTS_CHARCOAL_LIGHT};
            }}

            QCalendarWidget QAbstractItemView {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.BTS_PINK};
                selection-color: {Colors.TEXT_ON_ACCENT};
                border: none;
                outline: none;
            }}
            """
        )
