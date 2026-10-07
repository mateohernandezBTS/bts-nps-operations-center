from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Sizes, Spacing, Typography
from app.widgets.status_badge import StatusBadge


@dataclass(frozen=True)
class SidebarItem:
    """Definition of a navigation option displayed in the sidebar."""

    key: str
    label: str
    icon_text: str


class SidebarButton(QPushButton):
    """
    Internal navigation button used by Sidebar.

    The button only represents navigation state. It does not execute
    backend operations or contain application business logic.
    """

    def __init__(
        self,
        item: SidebarItem,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.item = item

        self.setObjectName("sidebarButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(46)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._build_content()
        self._apply_styles()

    def _build_content(self) -> None:
        self.setText(f"{self.item.icon_text}    {self.item.label}")
        self.setToolTip(self.item.label)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QPushButton#sidebarButton {{
                min-height: 46px;
                padding: 0 {Spacing.MD}px;
                border: none;
                border-radius: 8px;
                background-color: transparent;
                color: {Colors.TEXT_MUTED};
                text-align: left;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_MEDIUM};
            }}

            QPushButton#sidebarButton:hover {{
                background-color: {Colors.BTS_NAVY_LIGHT};
                color: {Colors.TEXT_ON_DARK};
            }}

            QPushButton#sidebarButton:checked {{
                background-color: {Colors.BTS_RED};
                color: {Colors.TEXT_ON_ACCENT};
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QPushButton#sidebarButton:pressed {{
                background-color: {Colors.BTS_RED_HOVER};
            }}
            """
        )


class Sidebar(QFrame):
    """
    Main navigation sidebar for BTS SELAM Operations Center.

    Signals:
        navigation_requested(str):
            Emitted with the key of the selected navigation item.
    """

    navigation_requested = Signal(str)

    DEFAULT_ITEMS = (
        SidebarItem(
            key="dashboard",
            label="Dashboard",
            icon_text="●",
        ),
        SidebarItem(
            key="weekly_run",
            label="Weekly Run",
            icon_text="▶",
        ),
        SidebarItem(
            key="weekly_output",
            label="Weekly Output",
            icon_text="!",
        ),
        SidebarItem(
            key="history",
            label="Run History",
            icon_text="◷",
        ),
        SidebarItem(
            key="settings",
            label="Settings",
            icon_text="⚙",
        ),
    )

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        application_version: str = "1.0.2",
        environment: str = "TEST",
    ) -> None:
        super().__init__(parent)

        self._application_version = application_version
        self._environment = environment.upper()
        self._buttons: dict[str, SidebarButton] = {}

        self.setObjectName("sidebar")
        self.setFixedWidth(Sizes.SIDEBAR_WIDTH)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding,
        )

        self._build_ui()
        self._apply_styles()
        self.set_active_item("dashboard", emit_signal=False)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            Spacing.MD,
            Spacing.LG,
            Spacing.MD,
            Spacing.MD,
        )
        root_layout.setSpacing(Spacing.MD)

        brand_widget = QWidget(self)
        brand_widget.setObjectName("sidebarBrand")

        brand_layout = QVBoxLayout(brand_widget)
        brand_layout.setContentsMargins(
            Spacing.XS,
            0,
            Spacing.XS,
            0,
        )
        brand_layout.setSpacing(Spacing.XXS)

        brand_title = QLabel("BTS SELAM", brand_widget)
        brand_title.setObjectName("sidebarBrandTitle")

        brand_subtitle = QLabel(
            "NPS Operations Center",
            brand_widget,
        )
        brand_subtitle.setObjectName("sidebarBrandSubtitle")
        brand_subtitle.setWordWrap(True)

        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_subtitle)

        section_label = QLabel("WORKSPACE", self)
        section_label.setObjectName("sidebarSectionLabel")

        navigation_widget = QWidget(self)
        navigation_widget.setObjectName("sidebarNavigation")

        navigation_layout = QVBoxLayout(navigation_widget)
        navigation_layout.setContentsMargins(0, 0, 0, 0)
        navigation_layout.setSpacing(Spacing.XS)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        for item in self.DEFAULT_ITEMS:
            button = SidebarButton(item, navigation_widget)

            button.clicked.connect(
                lambda checked=False, item_key=item.key: (
                    self._handle_navigation(item_key)
                )
            )

            self._button_group.addButton(button)
            self._buttons[item.key] = button
            navigation_layout.addWidget(button)

        root_layout.addWidget(brand_widget)
        root_layout.addSpacing(Spacing.LG)
        root_layout.addWidget(section_label)
        root_layout.addWidget(navigation_widget)
        root_layout.addStretch()

        system_card = QFrame(self)
        system_card.setObjectName("sidebarSystemCard")

        system_layout = QVBoxLayout(system_card)
        system_layout.setContentsMargins(
            Spacing.SM,
            Spacing.SM,
            Spacing.SM,
            Spacing.SM,
        )
        system_layout.setSpacing(Spacing.XS)

        system_title = QLabel("SYSTEM", system_card)
        system_title.setObjectName("sidebarSystemTitle")

        version_label = QLabel(
            f"Backend {self._application_version}",
            system_card,
        )
        version_label.setObjectName("sidebarSystemText")
        version_label.setWordWrap(True)

        release_status_label = QLabel(
            "Production Ready",
            system_card,
        )
        release_status_label.setObjectName("sidebarSystemText")
        release_status_label.setWordWrap(True)

        environment_row = QWidget(system_card)
        environment_row.setObjectName("sidebarEnvironmentRow")

        environment_layout = QHBoxLayout(environment_row)
        environment_layout.setContentsMargins(0, 0, 0, 0)
        environment_layout.setSpacing(Spacing.XS)

        environment_label = QLabel(
            "Environment",
            environment_row,
        )
        environment_label.setObjectName("sidebarSystemText")

        self._environment_badge = StatusBadge(
            self._environment,
            environment_row,
            tone=self._environment_tone(),
        )

        environment_layout.addWidget(environment_label)
        environment_layout.addStretch()
        environment_layout.addWidget(self._environment_badge)

        system_layout.addWidget(system_title)
        system_layout.addWidget(version_label)
        system_layout.addWidget(release_status_label)
        system_layout.addWidget(environment_row)

        root_layout.addWidget(system_card)

    def _handle_navigation(self, item_key: str) -> None:
        self.set_active_item(item_key, emit_signal=True)

    def set_active_item(
        self,
        item_key: str,
        *,
        emit_signal: bool = False,
    ) -> None:
        """
        Select a navigation item programmatically.
        """

        if item_key not in self._buttons:
            raise KeyError(
                f"Unknown sidebar item: {item_key!r}. "
                f"Available items: {sorted(self._buttons)}"
            )

        self._buttons[item_key].setChecked(True)

        if emit_signal:
            self.navigation_requested.emit(item_key)

    def active_item(self) -> str:
        """
        Return the currently selected navigation key.
        """

        for key, button in self._buttons.items():
            if button.isChecked():
                return key

        return ""

    def set_environment(self, environment: str) -> None:
        """
        Update the displayed execution environment.
        """

        self._environment = environment.upper()
        self._environment_badge.set_status(
            text=self._environment,
            tone=self._environment_tone(),
        )

    def _environment_tone(self) -> str:
        if self._environment == "PRODUCTION":
            return "error"

        if self._environment == "TEST":
            return "info"

        return "neutral"

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QFrame#sidebar {{
                background-color: {Colors.SIDEBAR_BACKGROUND};
                border: none;
            }}

            QWidget#sidebarBrand,
            QWidget#sidebarNavigation,
            QWidget#sidebarEnvironmentRow {{
                background-color: transparent;
            }}

            QLabel#sidebarBrandTitle {{
                color: {Colors.TEXT_ON_DARK};
                background-color: transparent;
                font-size: {Typography.SIZE_TITLE}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#sidebarBrandSubtitle {{
                color: {Colors.TEXT_MUTED};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_NORMAL};
            }}

            QLabel#sidebarSectionLabel {{
                color: {Colors.TEXT_MUTED};
                background-color: transparent;
                font-size: {Typography.SIZE_CAPTION}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QFrame#sidebarSystemCard {{
                background-color: {Colors.BTS_NAVY_LIGHT};
                border: 1px solid {Colors.BTS_NAVY_LIGHT};
                border-radius: 10px;
            }}

            QLabel#sidebarSystemTitle {{
                color: {Colors.TEXT_MUTED};
                background-color: transparent;
                font-size: {Typography.SIZE_CAPTION}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QLabel#sidebarSystemText {{
                color: {Colors.TEXT_ON_DARK};
                background-color: transparent;
                font-size: {Typography.SIZE_CAPTION}px;
                font-weight: {Typography.WEIGHT_NORMAL};
            }}
            """
        )
