from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Spacing
from app.views.weekly_run.configuration_card import (
    ConfigurationCard,
)


def main() -> int:
    application = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle(
        "BTS SELAM - ConfigurationCard Preview"
    )
    window.resize(1000, 360)

    layout = QVBoxLayout(window)
    layout.setContentsMargins(
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
    )

    configuration_card = ConfigurationCard()
    layout.addWidget(configuration_card)
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