from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Sizes, Spacing, Typography
from app.widgets.status_badge import StatusBadge


class Toolbar(QFrame):
    """
    Permanent application toolbar.

    The toolbar displays presentation state only. It does not execute
    backend operations or contain NPS business logic.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        title: str = "Dashboard",
        subtitle: str = "Operational overview",
        environment: str = "TEST",
        backend_status: str = "READY",
    ) -> None:
        super().__init__(parent)

        self._environment = environment.upper()
        self._backend_status = backend_status.upper()

        self.setObjectName("applicationToolbar")
        self.setFixedHeight(Sizes.TOOLBAR_HEIGHT)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._build_ui(
            title=title,
            subtitle=subtitle,
        )
        self._apply_styles()

    def _build_ui(
        self,
        *,
        title: str,
        subtitle: str,
    ) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(
            Spacing.LG,
            Spacing.XS,
            Spacing.LG,
            Spacing.XS,
        )
        root_layout.setSpacing(Spacing.MD)

        title_container = QWidget(self)
        title_container.setObjectName("toolbarTitleContainer")

        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        self._title_label = QLabel(title, title_container)
        self._title_label.setObjectName("toolbarTitle")

        self._subtitle_label = QLabel(subtitle, title_container)
        self._subtitle_label.setObjectName("toolbarSubtitle")

        title_layout.addWidget(self._title_label)
        title_layout.addWidget(self._subtitle_label)

        self._environment_badge = StatusBadge(
            self._environment,
            self,
            tone=self._environment_tone(),
        )

        self._backend_badge = StatusBadge(
            self._backend_label(),
            self,
            tone=self._backend_tone(),
            uppercase=False,
        )

        root_layout.addWidget(title_container)
        root_layout.addStretch()
        root_layout.addWidget(self._environment_badge)
        root_layout.addWidget(self._backend_badge)

    def set_page(
        self,
        *,
        title: str,
        subtitle: str,
    ) -> None:
        """Update the active page title and subtitle."""

        self._title_label.setText(title)
        self._subtitle_label.setText(subtitle)

    def set_environment(self, environment: str) -> None:
        """Update the displayed execution environment."""

        self._environment = environment.upper()

        self._environment_badge.set_status(
            text=self._environment,
            tone=self._environment_tone(),
        )

    def set_backend_status(self, status: str) -> None:
        """Update the displayed backend status."""

        self._backend_status = status.upper()

        self._backend_badge.set_status(
            text=self._backend_label(),
            tone=self._backend_tone(),
        )

    def _environment_tone(self) -> str:
        if self._environment == "PRODUCTION":
            return "error"

        if self._environment == "TEST":
            return "info"

        return "neutral"

    def _backend_label(self) -> str:
        labels = {
            "READY": "Backend Ready",
            "RUNNING": "Backend Running",
            "FAILED": "Backend Failed",
            "BLOCKED": "Backend Blocked",
            "IDLE": "Backend Idle",
        }

        return labels.get(
            self._backend_status,
            self._backend_status.title(),
        )

    def _backend_tone(self) -> str:
        tones = {
            "READY": "success",
            "RUNNING": "info",
            "FAILED": "error",
            "BLOCKED": "warning",
            "IDLE": "neutral",
        }

        return tones.get(
            self._backend_status,
            "neutral",
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QFrame#applicationToolbar {{
                background-color: {Colors.SURFACE};
                border: none;
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}

            QWidget#toolbarTitleContainer {{
                background-color: transparent;
            }}

            QLabel#toolbarTitle {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_LARGE}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QLabel#toolbarSubtitle {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_CAPTION}px;
                font-weight: {Typography.WEIGHT_NORMAL};
            }}
            """
        )