from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QPushButton,
    QWidget,
)

from app.theme import (
    Colors,
    Radius,
    Spacing,
    Typography,
)


class SecondaryButton(QPushButton):
    """
    Reusable BTS secondary action button.
    """

    def __init__(
        self,
        text: str,
        parent: Optional[QWidget] = None,
        *,
        minimum_width: int = 165,
    ) -> None:
        super().__init__(text, parent)

        self.setObjectName("secondaryButton")
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.setMinimumHeight(40)
        self.setMinimumWidth(minimum_width)

        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QPushButton#secondaryButton {{
                background-color: {Colors.SURFACE};
                color: {Colors.BTS_NAVY};
                border: 1px solid {Colors.BTS_NAVY};
                border-radius: {Radius.SMALL}px;
                padding: 0 {Spacing.LG}px;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QPushButton#secondaryButton:hover {{
                background-color: {Colors.INFO_BACKGROUND};
            }}

            QPushButton#secondaryButton:pressed {{
                background-color: {Colors.SURFACE_ALT};
                padding-top: 1px;
            }}

            QPushButton#secondaryButton:focus {{
                border: 2px solid {Colors.INFO};
            }}

            QPushButton#secondaryButton:disabled {{
                background-color: {Colors.SURFACE_ALT};
                color: {Colors.TEXT_MUTED};
                border: 1px solid {Colors.BORDER};
            }}
            """
        )

    def refresh_style(self) -> None:
        """
        Force Qt to repaint the button after a state change.
        """

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()