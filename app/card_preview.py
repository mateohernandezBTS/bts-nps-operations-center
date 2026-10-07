from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Spacing, Typography, apply_theme
from app.widgets.card import Card


class CardPreviewWindow(QMainWindow):
    """Visual validation window for the reusable Card component."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("BTS SELAM - Card Preview")
        self.setMinimumSize(900, 620)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
        )
        main_layout.setSpacing(Spacing.LG)

        page_title = QLabel("Card Component Preview")
        page_title.setStyleSheet(
            f"""
            font-size: {Typography.SIZE_PAGE_TITLE}px;
            font-weight: {Typography.WEIGHT_BOLD};
            color: {Colors.BTS_NAVY};
            """
        )

        page_subtitle = QLabel(
            "Visual validation of reusable surfaces for the Operations Center."
        )
        page_subtitle.setStyleSheet(
            f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_BODY_LARGE}px;
            """
        )

        status_card = Card(
            title="System Status",
            subtitle="Current backend availability and environment.",
        )

        status_label = QLabel("● Backend ready")
        status_label.setStyleSheet(
            f"""
            color: {Colors.SUCCESS};
            font-size: {Typography.SIZE_BODY_LARGE}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
            """
        )

        environment_label = QLabel("Environment: TEST")
        environment_label.setStyleSheet(
            f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_BODY}px;
            """
        )

        status_card.add_widget(status_label)
        status_card.add_widget(environment_label)

        action_card = Card(
            title="Weekly Run",
            subtitle="Prepare and execute the next SELAM weekly process.",
        )

        action_description = QLabel(
            "Run preflight validation before starting the weekly process."
        )
        action_description.setWordWrap(True)
        action_description.setStyleSheet(
            f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_BODY}px;
            """
        )

        run_button = QPushButton("Run Preflight")
        run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        run_button.setMaximumWidth(220)
        run_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Colors.BTS_RED};
                color: {Colors.TEXT_ON_ACCENT};
                border: none;
            }}

            QPushButton:hover {{
                background-color: {Colors.BTS_RED_HOVER};
            }}
            """
        )

        action_card.add_widget(action_description)
        action_card.add_widget(run_button)

        simple_card = Card(elevated=False)

        simple_message = QLabel(
            "This card has no header and no elevation."
        )
        simple_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        simple_message.setStyleSheet(
            f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_BODY}px;
            """
        )

        simple_card.add_widget(simple_message)

        main_layout.addWidget(page_title)
        main_layout.addWidget(page_subtitle)
        main_layout.addWidget(status_card)
        main_layout.addWidget(action_card)
        main_layout.addWidget(simple_card)
        main_layout.addStretch()

        self.setCentralWidget(central_widget)


def main() -> int:
    application = QApplication(sys.argv)
    apply_theme(application)

    window = CardPreviewWindow()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())