from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.theme import (
    Colors,
    Spacing,
    Typography,
)
from app.widgets.card import Card
from app.widgets.primary_button import PrimaryButton
from app.widgets.secondary_button import SecondaryButton


class ActionsCard(Card):
    """
    Weekly Run action controls.

    Emits UI intents only. No business logic.
    """

    preflight_requested = Signal()
    weekly_process_requested = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(
            parent=parent,
            title="Process Actions",
            subtitle=(
                "Preflight must finish successfully before processing."
            ),
        )

        self.setObjectName("weeklyRunActionsCard")

        self._build_ui()
        self._connect_signals()
        self._apply_styles()

        self.preflight_button.setEnabled(True)
        self.process_button.setEnabled(False)
        self.production_warning.setVisible(True)

        self._refresh_button_styles()

    def _build_ui(self) -> None:
        container = QWidget(self)
        container.setObjectName("weeklyRunActionsContainer")

        root_layout = QVBoxLayout(container)
        root_layout.setContentsMargins(0, Spacing.XS, 0, 0)
        root_layout.setSpacing(Spacing.MD)

        buttons_row = QWidget(container)
        buttons_row.setObjectName("weeklyRunButtonsRow")

        buttons_layout = QHBoxLayout(buttons_row)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(Spacing.MD)

        self.preflight_button = PrimaryButton(
            "Run Preflight",
            buttons_row,
            minimum_width=165,
        )

        self.process_button = SecondaryButton(
            "Run Weekly Process",
            buttons_row,
            minimum_width=190,
        )

        buttons_layout.addWidget(self.preflight_button)
        buttons_layout.addWidget(self.process_button)
        buttons_layout.addStretch()

        self.production_warning = QLabel(
            "Production mode writes operational outputs.",
            container,
        )
        self.production_warning.setObjectName(
            "weeklyRunProductionWarning"
        )
        self.production_warning.setWordWrap(True)

        root_layout.addWidget(buttons_row)
        root_layout.addWidget(self.production_warning)

        self.add_widget(container)

    def _connect_signals(self) -> None:
        self.preflight_button.clicked.connect(
            self.preflight_requested.emit
        )
        self.process_button.clicked.connect(
            self.weekly_process_requested.emit
        )

    def set_idle_state(self) -> None:
        self.preflight_button.setEnabled(True)
        self.process_button.setEnabled(False)
        self._refresh_button_styles()

    def set_preflight_running(self) -> None:
        self.preflight_button.setEnabled(False)
        self.process_button.setEnabled(False)
        self._refresh_button_styles()

    def set_preflight_ready(self) -> None:
        self.preflight_button.setEnabled(True)
        self.process_button.setEnabled(True)
        self._refresh_button_styles()

    def set_preflight_blocked(self) -> None:
        self.preflight_button.setEnabled(True)
        self.process_button.setEnabled(False)
        self._refresh_button_styles()

    def set_processing_running(self) -> None:
        self.preflight_button.setEnabled(False)
        self.process_button.setEnabled(False)
        self._refresh_button_styles()

    def set_process_finished(self) -> None:
        self.preflight_button.setEnabled(True)
        self.process_button.setEnabled(False)
        self._refresh_button_styles()

    def set_production_mode(self, enabled: bool) -> None:
        self.production_warning.setVisible(enabled)

    def _refresh_button_styles(self) -> None:
        self.preflight_button.refresh_style()
        self.process_button.refresh_style()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#weeklyRunActionsContainer,
            QWidget#weeklyRunButtonsRow {{
                background-color: transparent;
            }}

            QLabel#weeklyRunProductionWarning {{
                color: {Colors.ERROR};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}
            """
        )