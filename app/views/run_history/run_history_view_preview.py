from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QWidget,
)

from app.controllers.ui_controller import UIController
from app.theme import Colors, Spacing
from app.views.run_history.run_history_view import (
    RunHistoryView,
)


def main() -> int:
    application = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle(
        "BTS SELAM - RunHistoryView Preview"
    )
    window.resize(1350, 650)

    root_layout = QVBoxLayout(window)
    root_layout.setContentsMargins(
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
        Spacing.XL,
    )

    history_view = RunHistoryView()

    controller = UIController()
    state = controller.get_run_history_state()

    history_view.apply_state(state)

    history_view.view_output_requested.connect(
        lambda run: print(
            "SELECTED:",
            run.environment,
            run.weekly_run_id,
            run.status,
            run.run_directory,
        )
    )

    root_layout.addWidget(history_view)

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