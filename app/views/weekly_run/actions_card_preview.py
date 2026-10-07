from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Spacing
from app.views.weekly_run.actions_card import (
    ActionsCard,
)


def main() -> int:
    application = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle(
        "BTS SELAM - ActionsCard Preview"
    )
    window.resize(900, 300)

    layout = QVBoxLayout(window)
    layout.setContentsMargins(
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
    )

    card = ActionsCard()
    layout.addWidget(card)
    layout.addStretch()

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