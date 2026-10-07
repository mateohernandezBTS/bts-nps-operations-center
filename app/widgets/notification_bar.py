from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QWidget,
)

from app.theme import Colors, Sizes, Spacing, Typography
from app.widgets.status_badge import StatusBadge


class NotificationBar(QFrame):
    """
    Persistent application notification and status bar.

    This widget only displays presentation state. It does not infer
    backend status or execute business logic.
    """

    VALID_TONES = {
        "neutral",
        "success",
        "warning",
        "error",
        "info",
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        message: str = "System ready",
        tone: str = "success",
        status_text: Optional[str] = None,
    ) -> None:
        super().__init__(parent)

        self._validate_tone(tone)

        self._message = message
        self._tone = tone
        self._status_text = status_text

        self.setObjectName("notificationBar")
        self.setFixedHeight(Sizes.STATUS_BAR_HEIGHT)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(
            Spacing.LG,
            0,
            Spacing.LG,
            0,
        )
        root_layout.setSpacing(Spacing.SM)

        self._indicator = QLabel("●", self)
        self._indicator.setObjectName("notificationIndicator")
        self._indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._message_label = QLabel(self._message, self)
        self._message_label.setObjectName("notificationMessage")

        root_layout.addWidget(self._indicator)
        root_layout.addWidget(self._message_label)
        root_layout.addStretch()

        if self._status_text:
            self._status_badge = StatusBadge(
                self._status_text,
                self,
                tone=self._tone,
                uppercase=False,
            )
            root_layout.addWidget(self._status_badge)
        else:
            self._status_badge = None

    def set_notification(
        self,
        *,
        message: Optional[str] = None,
        tone: Optional[str] = None,
        status_text: Optional[str] = None,
    ) -> None:
        """
        Update the notification message, tone and optional status badge.
        """

        if message is not None:
            self._message = message
            self._message_label.setText(message)

        if tone is not None:
            self._validate_tone(tone)
            self._tone = tone

        if status_text is not None:
            self._status_text = status_text

            if self._status_badge is None:
                self._status_badge = StatusBadge(
                    status_text,
                    self,
                    tone=self._tone,
                    uppercase=False,
                )

                self.layout().addWidget(self._status_badge)
            else:
                self._status_badge.set_status(
                    text=status_text,
                    tone=self._tone,
                )

        elif self._status_badge is not None:
            self._status_badge.set_tone(self._tone)

        self._apply_styles()

    def clear_status_badge(self) -> None:
        """
        Remove the optional status badge from the bar.
        """

        if self._status_badge is None:
            return

        self._status_badge.setParent(None)
        self._status_badge.deleteLater()
        self._status_badge = None
        self._status_text = None

    def _validate_tone(self, tone: str) -> None:
        if tone not in self.VALID_TONES:
            raise ValueError(
                f"Unsupported NotificationBar tone: {tone!r}. "
                f"Expected one of: {sorted(self.VALID_TONES)}"
            )

    def _tone_color(self) -> str:
        tone_map = {
            "neutral": Colors.NEUTRAL,
            "success": Colors.SUCCESS,
            "warning": Colors.WARNING,
            "error": Colors.ERROR,
            "info": Colors.INFO,
        }

        return tone_map[self._tone]

    def _apply_styles(self) -> None:
        tone_color = self._tone_color()

        self.setStyleSheet(
            f"""
            QFrame#notificationBar {{
                background-color: {Colors.SURFACE};
                border: none;
                border-top: 1px solid {Colors.BORDER_LIGHT};
            }}

            QLabel#notificationIndicator {{
                color: {tone_color};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#notificationMessage {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_NORMAL};
            }}
            """
        )