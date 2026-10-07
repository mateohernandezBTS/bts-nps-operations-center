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


class PrimaryButton(QPushButton):
    """
    Reusable BTS primary action button.

    The component owns its complete visual style and can be safely
    reused across views without defining QPushButton CSS locally.
    """

    def __init__(
        self,
        text: str,
        parent: Optional[QWidget] = None,
        *,
        minimum_width: int = 165,
    ) -> None:
        super().__init__(text, parent)

        self.setObjectName("primaryButton")
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.setMinimumHeight(40)
        self.setMinimumWidth(minimum_width)

        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QPushButton#primaryButton {{
                background-color: {Colors.BTS_RED};
                color: {Colors.TEXT_ON_ACCENT};
                border: none;
                border-radius: {Radius.SMALL}px;
                padding: 0 {Spacing.LG}px;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QPushButton#primaryButton:hover {{
                background-color: {Colors.BTS_RED_HOVER};
            }}

            QPushButton#primaryButton:pressed {{
                background-color: {Colors.BTS_RED};
                padding-top: 1px;
            }}

            QPushButton#primaryButton:focus {{
                border: 2px solid {Colors.INFO};
            }}

            QPushButton#primaryButton:disabled {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_MUTED};
                border: none;
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