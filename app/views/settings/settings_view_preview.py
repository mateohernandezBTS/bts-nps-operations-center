from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QWidget,
)

from app.controllers.ui_controller import UIController
from app.theme import Colors, Spacing
from app.views.settings.settings_view import SettingsView


def main() -> int:
    application = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle(
        "BTS SELAM - SettingsView Preview"
    )
    window.resize(1150, 800)

    root_layout = QVBoxLayout(window)
    root_layout.setContentsMargins(
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
    )

    settings_view = SettingsView()

    controller = UIController()
    state = controller.get_settings_state()

    settings_view.apply_state(state)

    settings_view.reset_session_requested.connect(
        lambda: print(
            "RESET CURRENT SESSION REQUESTED"
        )
    )

    root_layout.addWidget(settings_view)

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