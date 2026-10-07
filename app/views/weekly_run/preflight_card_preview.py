from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Spacing
from app.views.weekly_run.preflight_card import (
    PreflightCard,
)
from app.widgets.secondary_button import SecondaryButton


def main() -> int:
    application = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle(
        "BTS SELAM - PreflightCard Preview"
    )
    window.resize(1000, 560)

    root_layout = QVBoxLayout(window)
    root_layout.setContentsMargins(
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
    )
    root_layout.setSpacing(Spacing.LG)

    preflight_card = PreflightCard()

    controls = QWidget(window)
    controls_layout = QHBoxLayout(controls)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(Spacing.MD)

    idle_button = SecondaryButton(
        "Not Run",
        controls,
    )

    running_button = SecondaryButton(
        "Running",
        controls,
    )

    ready_button = SecondaryButton(
        "Ready",
        controls,
    )

    blocked_button = SecondaryButton(
        "Blocked",
        controls,
    )

    failed_button = SecondaryButton(
        "Failed",
        controls,
    )

    idle_button.clicked.connect(
        preflight_card.set_idle_state
    )

    running_button.clicked.connect(
        preflight_card.set_running_state
    )

    ready_button.clicked.connect(
        lambda: preflight_card.set_ready_state(
            status="READY_TO_PROCESS",
            message=(
                "Weekly preflight completed successfully."
            ),
        )
    )

    blocked_button.clicked.connect(
        lambda: preflight_card.set_blocked_state(
            status="BLOCKED",
            message=(
                "Weekly preflight found blocking issues."
            ),
            issues=(
                "Missing required source: Brazil upcoming.",
                "Duplicate source detected for Mexico upcoming.",
            ),
        )
    )

    failed_button.clicked.connect(
        lambda: preflight_card.set_failed_state(
            message=(
                "Weekly preflight could not be completed."
            ),
            issues=(
                "Unexpected error while reading source inventory.",
            ),
        )
    )

    controls_layout.addWidget(idle_button)
    controls_layout.addWidget(running_button)
    controls_layout.addWidget(ready_button)
    controls_layout.addWidget(blocked_button)
    controls_layout.addWidget(failed_button)
    controls_layout.addStretch()

    root_layout.addWidget(preflight_card)
    root_layout.addWidget(controls)
    root_layout.addStretch()

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