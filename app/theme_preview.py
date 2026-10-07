from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Spacing, Typography, apply_theme


class ThemePreviewWindow(QMainWindow):
    """Minimal window used to validate the global BTS SELAM theme."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("BTS SELAM Operations Center")
        self.setMinimumSize(760, 460)

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
        )
        main_layout.setSpacing(Spacing.LG)

        title = QLabel("BTS SELAM Operations Center")
        title.setStyleSheet(
            f"""
            font-size: {Typography.SIZE_PAGE_TITLE}px;
            font-weight: {Typography.WEIGHT_BOLD};
            color: {Colors.BTS_NAVY};
            """
        )

        subtitle = QLabel("Dashboard Preview")
        subtitle.setStyleSheet(
            f"""
            font-size: {Typography.SIZE_SUBTITLE}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
            color: {Colors.TEXT_SECONDARY};
            """
        )

        card = QFrame()
        card.setObjectName("previewCard")
        card.setStyleSheet(
            f"""
            QFrame#previewCard {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: 14px;
            }}
            """
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            Spacing.LG,
            Spacing.LG,
            Spacing.LG,
            Spacing.LG,
        )
        card_layout.setSpacing(Spacing.MD)

        message = QLabel("Theme validation successful")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setStyleSheet(
            f"""
            font-size: {Typography.SIZE_BODY_LARGE}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
            color: {Colors.SUCCESS};
            """
        )

        run_button = QPushButton("Run Weekly Process")
        run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        run_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Colors.BTS_RED};
                color: {Colors.TEXT_ON_ACCENT};
                border: none;
                border-radius: 6px;
                padding: 0 20px;
            }}

            QPushButton:hover {{
                background-color: {Colors.BTS_RED_HOVER};
            }}
            """
        )

        card_layout.addWidget(message)
        card_layout.addWidget(run_button)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(card)
        main_layout.addStretch()

        self.setCentralWidget(central_widget)


def main() -> int:
    application = QApplication(sys.argv)
    apply_theme(application)

    window = ThemePreviewWindow()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())