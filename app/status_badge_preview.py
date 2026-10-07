from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Spacing, Typography, apply_theme
from app.widgets.card import Card
from app.widgets.status_badge import StatusBadge


class StatusBadgePreviewWindow(QMainWindow):
    """Visual validation window for the StatusBadge component."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("BTS SELAM - StatusBadge Preview")
        self.setMinimumSize(920, 560)

        central_widget = QWidget()

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
        )
        main_layout.setSpacing(Spacing.LG)

        page_title = QLabel("StatusBadge Component Preview")
        page_title.setStyleSheet(
            f"""
            font-size: {Typography.SIZE_PAGE_TITLE}px;
            font-weight: {Typography.WEIGHT_BOLD};
            color: {Colors.BTS_NAVY};
            """
        )

        page_subtitle = QLabel(
            "Compact operational states for dashboards, tables and workflows."
        )
        page_subtitle.setStyleSheet(
            f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_BODY_LARGE}px;
            """
        )

        states_card = Card(
            title="Operational States",
            subtitle="Primary statuses used throughout the application.",
        )

        first_row = QWidget()
        first_row_layout = QHBoxLayout(first_row)
        first_row_layout.setContentsMargins(0, 0, 0, 0)
        first_row_layout.setSpacing(Spacing.SM)

        first_row_layout.addWidget(
            StatusBadge("Ready", tone="success")
        )
        first_row_layout.addWidget(
            StatusBadge("Review", tone="warning")
        )
        first_row_layout.addWidget(
            StatusBadge("Failed", tone="error")
        )
        first_row_layout.addWidget(
            StatusBadge("Running", tone="info")
        )
        first_row_layout.addWidget(
            StatusBadge("Blocked", tone="neutral")
        )
        first_row_layout.addStretch()

        second_row = QWidget()
        second_row_layout = QHBoxLayout(second_row)
        second_row_layout.setContentsMargins(0, 0, 0, 0)
        second_row_layout.setSpacing(Spacing.SM)

        second_row_layout.addWidget(
            StatusBadge("Completed", tone="success")
        )
        second_row_layout.addWidget(
            StatusBadge("Test", tone="info")
        )
        second_row_layout.addWidget(
            StatusBadge("Production", tone="error")
        )
        second_row_layout.addWidget(
            StatusBadge(
                "Manual review required",
                tone="warning",
                uppercase=False,
            )
        )
        second_row_layout.addStretch()

        states_card.add_widget(first_row)
        states_card.add_widget(second_row)

        dynamic_card = Card(
            title="Dynamic Status",
            subtitle="The badge can be updated without recreating the widget.",
        )

        dynamic_row = QWidget()
        dynamic_row_layout = QHBoxLayout(dynamic_row)
        dynamic_row_layout.setContentsMargins(0, 0, 0, 0)
        dynamic_row_layout.setSpacing(Spacing.MD)

        dynamic_label = QLabel("Current backend state:")
        dynamic_label.setStyleSheet(
            f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_BODY}px;
            """
        )

        dynamic_badge = StatusBadge(
            "Completed",
            tone="success",
        )

        dynamic_row_layout.addWidget(dynamic_label)
        dynamic_row_layout.addWidget(dynamic_badge)
        dynamic_row_layout.addStretch()

        dynamic_card.add_widget(dynamic_row)

        main_layout.addWidget(page_title)
        main_layout.addWidget(page_subtitle)
        main_layout.addWidget(states_card)
        main_layout.addWidget(dynamic_card)
        main_layout.addStretch()

        self.setCentralWidget(central_widget)


def main() -> int:
    application = QApplication(sys.argv)
    apply_theme(application)

    window = StatusBadgePreviewWindow()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())