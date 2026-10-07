from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QWidget,
)

from app.controllers.ui_controller import UIController
from app.theme import Colors, Spacing
from app.views.weekly_output.weekly_output_view import (
    WeeklyOutputView,
)


def main() -> int:
    application = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle(
        "BTS SELAM - WeeklyOutputView Preview"
    )
    window.resize(1300, 820)

    root_layout = QVBoxLayout(window)
    root_layout.setContentsMargins(
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
    )

    output_view = WeeklyOutputView()

    controller = UIController()
    state = controller.get_weekly_output_state()

    output_view.apply_state(state)

    root_layout.addWidget(output_view)

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