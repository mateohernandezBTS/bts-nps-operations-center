from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Spacing
from app.views.weekly_run.sources_card import SourcesCard
from app.widgets.secondary_button import SecondaryButton


def main() -> int:
    application = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle(
        "BTS SELAM - SourcesCard Preview"
    )
    window.resize(950, 440)

    root_layout = QVBoxLayout(window)
    root_layout.setContentsMargins(
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
    )
    root_layout.setSpacing(Spacing.LG)

    sources_card = SourcesCard()

    controls = QWidget(window)
    controls_layout = QHBoxLayout(controls)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(Spacing.MD)

    not_checked_button = SecondaryButton(
        "Not Checked",
        controls,
    )

    partial_button = SecondaryButton(
        "2 / 3 Received",
        controls,
    )

    all_received_button = SecondaryButton(
        "All Received",
        controls,
    )

    not_checked_button.clicked.connect(
        sources_card.set_not_checked
    )

    partial_button.clicked.connect(
        lambda: sources_card.set_sources_received(2)
    )

    all_received_button.clicked.connect(
        sources_card.set_all_received
    )

    controls_layout.addWidget(not_checked_button)
    controls_layout.addWidget(partial_button)
    controls_layout.addWidget(all_received_button)
    controls_layout.addStretch()

    root_layout.addWidget(sources_card)
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