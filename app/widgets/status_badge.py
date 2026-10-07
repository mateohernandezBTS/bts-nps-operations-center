from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from app.theme import Colors, Radius, Typography


class StatusBadge(QLabel):
    """
    Compact reusable badge for operational states.

    Supported tones:
    - neutral
    - success
    - warning
    - error
    - info
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
        text: str,
        parent: Optional[QWidget] = None,
        *,
        tone: str = "neutral",
        uppercase: bool = True,
    ) -> None:
        super().__init__(parent)

        self._validate_tone(tone)

        self._tone = tone
        self._uppercase = uppercase
        self._raw_text = text

        self.setObjectName("statusBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(24)
        self.setContentsMargins(0, 0, 0, 0)

        self.set_status(text=text, tone=tone)

    def set_status(
        self,
        *,
        text: Optional[str] = None,
        tone: Optional[str] = None,
    ) -> None:
        """
        Update the badge text and/or tone.
        """

        if text is not None:
            self._raw_text = text

        if tone is not None:
            self._validate_tone(tone)
            self._tone = tone

        display_text = (
            self._raw_text.upper()
            if self._uppercase
            else self._raw_text
        )

        self.setText(display_text)
        self._apply_styles()

    def set_tone(self, tone: str) -> None:
        """
        Update only the visual tone.
        """

        self.set_status(tone=tone)

    def set_badge_text(self, text: str) -> None:
        """
        Update only the visible text.
        """

        self.set_status(text=text)

    def _validate_tone(self, tone: str) -> None:
        if tone not in self.VALID_TONES:
            raise ValueError(
                f"Unsupported StatusBadge tone: {tone!r}. "
                f"Expected one of: {sorted(self.VALID_TONES)}"
            )

    def _tone_colors(self) -> tuple[str, str, str]:
        tone_map = {
            "neutral": (
                Colors.TEXT_SECONDARY,
                Colors.NEUTRAL_BACKGROUND,
                Colors.BORDER,
            ),
            "success": (
                Colors.SUCCESS,
                Colors.SUCCESS_BACKGROUND,
                Colors.SUCCESS,
            ),
            "warning": (
                Colors.WARNING,
                Colors.WARNING_BACKGROUND,
                Colors.WARNING,
            ),
            "error": (
                Colors.ERROR,
                Colors.ERROR_BACKGROUND,
                Colors.ERROR,
            ),
            "info": (
                Colors.INFO,
                Colors.INFO_BACKGROUND,
                Colors.INFO,
            ),
        }

        return tone_map[self._tone]

    def _apply_styles(self) -> None:
        text_color, background_color, border_color = (
            self._tone_colors()
        )

        self.setStyleSheet(
            f"""
            QLabel#statusBadge {{
                color: {text_color};
                background-color: {background_color};
                border: 1px solid {border_color};
                border-radius: {Radius.PILL}px;
                padding: 4px 10px;
                font-size: {Typography.SIZE_CAPTION}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}
            """
        )