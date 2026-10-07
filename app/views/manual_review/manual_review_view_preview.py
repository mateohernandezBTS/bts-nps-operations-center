from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Spacing
from app.views.manual_review.manual_review_view import (
    ManualReviewView,
)
from app.widgets.secondary_button import SecondaryButton


def main() -> int:
    application = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle(
        "BTS SELAM - ManualReviewView Preview"
    )
    window.resize(1200, 720)

    root_layout = QVBoxLayout(window)
    root_layout.setContentsMargins(
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
    )
    root_layout.setSpacing(Spacing.LG)

    manual_review_view = ManualReviewView()

    controls = QWidget(window)
    controls_layout = QHBoxLayout(controls)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(Spacing.MD)

    review_button = SecondaryButton(
        "Review Required",
        controls,
    )

    empty_button = SecondaryButton(
        "No Review",
        controls,
    )

    review_button.clicked.connect(
        manual_review_view.set_preview_state
    )

    empty_button.clicked.connect(
        manual_review_view.set_empty_state
    )

    controls_layout.addWidget(review_button)
    controls_layout.addWidget(empty_button)
    controls_layout.addStretch()

    root_layout.addWidget(manual_review_view)
    root_layout.addWidget(controls)

    window.setStyleSheet(
        f"""
        QWidget {{
            background-color: {Colors.APP_BACKGROUND};
        }}
        """
    )

    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())