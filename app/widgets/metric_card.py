from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from app.theme import (
    Colors,
    Radius,
    Sizes,
    Spacing,
    Typography,
)
from app.widgets.card import Card


class MetricCard(Card):
    """
    Executive metric card for BTS SELAM Operations Center.

    Displays:
    - metric label;
    - primary value;
    - optional helper text;
    - optional status chip;
    - visual tone indicator.
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
        label: str,
        value: str,
        parent: Optional[QWidget] = None,
        *,
        helper_text: Optional[str] = None,
        tone: str = "neutral",
        accent_text: Optional[str] = None,
    ) -> None:
        self._validate_tone(tone)

        self._tone = tone
        self._label_text = label
        self._value_text = value
        self._helper_text = helper_text
        self._accent_text = accent_text

        super().__init__(
            parent=parent,
            elevated=True,
        )

        self.setObjectName("metricCard")
        self.setMinimumWidth(
            Sizes.METRIC_CARD_MIN_WIDTH
        )
        self.setMinimumHeight(168)

        self.content_layout.setSpacing(
            Spacing.SM
        )

        self._build_ui()
        self._apply_metric_styles()

    def _build_ui(self) -> None:
        tone_color, _ = self._tone_colors()

        self._tone_bar = QFrame(self)
        self._tone_bar.setObjectName(
            "metricToneBar"
        )
        self._tone_bar.setFixedHeight(4)
        self._tone_bar.setStyleSheet(
            f"""
            QFrame#metricToneBar {{
                background-color: {tone_color};
                border: none;
                border-radius: 2px;
            }}
            """
        )

        self._header_widget = QWidget(self)
        self._header_widget.setObjectName(
            "metricHeader"
        )
        self._header_widget.setStyleSheet(
            "background-color: transparent;"
        )

        self._header_layout = QHBoxLayout(
            self._header_widget
        )
        self._header_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self._header_layout.setSpacing(
            Spacing.SM
        )

        self._label = QLabel(
            self._label_text,
            self._header_widget,
        )
        self._label.setObjectName(
            "metricLabel"
        )
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        self._header_layout.addWidget(
            self._label
        )
        self._header_layout.addStretch()

        self._accent: Optional[QLabel] = None

        if self._accent_text:
            self._accent = QLabel(
                self._accent_text,
                self._header_widget,
            )
            self._accent.setObjectName(
                "metricAccent"
            )
            self._accent.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            self._accent.setMinimumHeight(24)

            self._header_layout.addWidget(
                self._accent
            )

        self._value = QLabel(
            self._value_text,
            self,
        )
        self._value.setObjectName(
            "metricValue"
        )
        self._value.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )
        self._value.setWordWrap(False)

        self._helper: Optional[QLabel] = None

        self.content_layout.addWidget(
            self._tone_bar
        )
        self.content_layout.addSpacing(
            Spacing.XS
        )
        self.content_layout.addWidget(
            self._header_widget
        )
        self.content_layout.addSpacing(
            Spacing.XS
        )
        self.content_layout.addWidget(
            self._value
        )

        if self._helper_text:
            self._helper = QLabel(
                self._helper_text,
                self,
            )
            self._helper.setObjectName(
                "metricHelper"
            )
            self._helper.setWordWrap(True)

            self.content_layout.addSpacing(
                Spacing.XXS
            )
            self.content_layout.addWidget(
                self._helper
            )

        self.content_layout.addStretch()

    def set_value(
        self,
        value: str,
    ) -> None:
        """Update the primary metric value."""

        self._value_text = value
        self._value.setText(value)

    def set_helper_text(
        self,
        helper_text: str,
    ) -> None:
        """Update or create the helper text."""

        self._helper_text = helper_text

        if self._helper is None:
            self._helper = QLabel(
                helper_text,
                self,
            )
            self._helper.setObjectName(
                "metricHelper"
            )
            self._helper.setWordWrap(True)

            insert_index = max(
                0,
                self.content_layout.count() - 1,
            )

            self.content_layout.insertWidget(
                insert_index,
                self._helper,
            )
        else:
            self._helper.setText(
                helper_text
            )

        self._apply_metric_styles()

    def set_accent_text(
        self,
        accent_text: str,
    ) -> None:
        """
        Update or create the status chip shown in the metric header.
        """

        self._accent_text = accent_text

        if self._accent is None:
            self._accent = QLabel(
                accent_text,
                self._header_widget,
            )
            self._accent.setObjectName(
                "metricAccent"
            )
            self._accent.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            self._accent.setMinimumHeight(24)

            self._header_layout.addWidget(
                self._accent
            )
        else:
            self._accent.setText(
                accent_text
            )

        self._apply_metric_styles()

    def set_tone(
        self,
        tone: str,
    ) -> None:
        """Change the visual status tone."""

        self._validate_tone(tone)
        self._tone = tone
        self._apply_metric_styles()

    def _validate_tone(
        self,
        tone: str,
    ) -> None:
        if tone not in self.VALID_TONES:
            raise ValueError(
                f"Unsupported MetricCard tone: {tone!r}. "
                f"Expected one of: "
                f"{sorted(self.VALID_TONES)}"
            )

    def _tone_colors(
        self,
    ) -> tuple[str, str]:
        tone_map = {
            "neutral": (
                Colors.TEXT_PRIMARY,
                Colors.NEUTRAL_BACKGROUND,
            ),
            "success": (
                Colors.SUCCESS,
                Colors.SUCCESS_BACKGROUND,
            ),
            "warning": (
                Colors.WARNING,
                Colors.WARNING_BACKGROUND,
            ),
            "error": (
                Colors.ERROR,
                Colors.ERROR_BACKGROUND,
            ),
            "info": (
                Colors.INFO,
                Colors.INFO_BACKGROUND,
            ),
        }

        return tone_map[self._tone]

    def _apply_metric_styles(
        self,
    ) -> None:
        tone_color, tone_background = (
            self._tone_colors()
        )

        self._tone_bar.setStyleSheet(
            f"""
            QFrame#metricToneBar {{
                background-color: {tone_color};
                border: none;
                border-radius: 2px;
            }}
            """
        )

        self.setStyleSheet(
            f"""
            QFrame#metricCard {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {Radius.LARGE}px;
            }}

            QLabel#metricLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
                background-color: transparent;
            }}

            QLabel#metricValue {{
                color: {tone_color};
                font-size: 34px;
                font-weight: {Typography.WEIGHT_BOLD};
                background-color: transparent;
            }}

            QLabel#metricHelper {{
                color: {Colors.TEXT_SECONDARY};
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_NORMAL};
                background-color: transparent;
            }}

            QLabel#metricAccent {{
                color: {tone_color};
                background-color: {tone_background};
                border: 1px solid {tone_color};
                border-radius: {Radius.PILL}px;
                padding: 4px 10px;
                font-size: {Typography.SIZE_CAPTION}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}
            """
        )