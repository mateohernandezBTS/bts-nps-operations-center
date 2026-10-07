from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.main_window import ApplicationShell
from app.theme import apply_theme


def main() -> int:
    application = QApplication(sys.argv)

    application.setApplicationName(
        "BTS SELAM NPS Operations Center"
    )
    application.setOrganizationName("BTS")

    apply_theme(application)

    window = ApplicationShell()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())