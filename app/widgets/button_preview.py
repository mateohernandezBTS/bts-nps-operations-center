from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Spacing
from app.widgets.primary_button import PrimaryButton
from app.widgets.secondary_button import SecondaryButton


def main() -> int:
    application = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle(
        "BTS SELAM - Button Preview"
    )
    window.resize(600, 420)

    layout = QVBoxLayout(window)
    layout.setContentsMargins(
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
    )
    layout.setSpacing(Spacing.LG)

    title = QLabel(
        "Reusable Button Components",
        window,
    )

    primary_enabled = PrimaryButton(
        "Run Preflight",
        window,
    )

    primary_disabled = PrimaryButton(
        "Primary Disabled",
        window,
    )
    primary_disabled.setEnabled(False)

    secondary_enabled = SecondaryButton(
        "Secondary Action",
        window,
    )

    secondary_disabled = SecondaryButton(
        "Run Weekly Process",
        window,
        minimum_width=190,
    )
    secondary_disabled.setEnabled(False)

    layout.addWidget(title)
    layout.addWidget(primary_enabled)
    layout.addWidget(primary_disabled)
    layout.addWidget(secondary_enabled)
    layout.addWidget(secondary_disabled)
    layout.addStretch()

    window.setStyleSheet(
        f"""
        QWidget {{
            background-color: {Colors.APP_BACKGROUND};
        }}

        QLabel {{
            color: {Colors.TEXT_PRIMARY};
            background-color: transparent;
        }}
        """
    )

    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())