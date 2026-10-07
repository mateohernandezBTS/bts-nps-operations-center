from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Spacing, Typography, apply_theme
from app.widgets.card import Card
from app.widgets.sidebar import Sidebar
from app.widgets.status_badge import StatusBadge


class SidebarPreviewWindow(QMainWindow):
    """Visual and interaction preview for the Sidebar component."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("BTS SELAM - Sidebar Preview")
        self.setMinimumSize(1120, 720)

        central_widget = QWidget()
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar(
            application_version="1.0.2",
            environment="TEST",
        )

        content_widget = QWidget()
        content_widget.setObjectName("previewContent")

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
        )
        content_layout.setSpacing(Spacing.LG)

        page_title = QLabel("Dashboard")
        page_title.setObjectName("pageTitle")
        page_title.setStyleSheet(
            f"""
            color: {Colors.BTS_NAVY};
            font-size: {Typography.SIZE_PAGE_TITLE}px;
            font-weight: {Typography.WEIGHT_BOLD};
            background-color: transparent;
            """
        )

        page_subtitle = QLabel(
            "Select a navigation item to validate the sidebar interaction."
        )
        page_subtitle.setStyleSheet(
            f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_BODY_LARGE}px;
            background-color: transparent;
            """
        )

        navigation_card = Card(
            title="Navigation Event",
            subtitle="The selected key is emitted by the Sidebar.",
        )

        selected_label = QLabel("dashboard")
        selected_label.setStyleSheet(
            f"""
            color: {Colors.BTS_NAVY};
            font-size: {Typography.SIZE_TITLE}px;
            font-weight: {Typography.WEIGHT_BOLD};
            background-color: transparent;
            """
        )

        state_row = QWidget()
        state_layout = QHBoxLayout(state_row)
        state_layout.setContentsMargins(0, 0, 0, 0)
        state_layout.setSpacing(Spacing.SM)

        state_text = QLabel("Current state:")
        state_text.setStyleSheet(
            f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_BODY}px;
            background-color: transparent;
            """
        )

        state_badge = StatusBadge(
            "Ready",
            tone="success",
        )

        state_layout.addWidget(state_text)
        state_layout.addWidget(state_badge)
        state_layout.addStretch()

        navigation_card.add_widget(selected_label)
        navigation_card.add_widget(state_row)

        content_layout.addWidget(page_title)
        content_layout.addWidget(page_subtitle)
        content_layout.addWidget(navigation_card)
        content_layout.addStretch()

        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(content_widget, 1)

        self._page_title = page_title
        self._selected_label = selected_label

        self.sidebar.navigation_requested.connect(
            self._handle_navigation
        )

        self.setCentralWidget(central_widget)

    def _handle_navigation(self, item_key: str) -> None:
        title_map = {
            "dashboard": "Dashboard",
            "weekly_run": "Weekly Run",
            "manual_review": "Manual Review",
            "history": "Run History",
            "settings": "Settings",
        }

        page_title = title_map.get(item_key, item_key)

        self._page_title.setText(page_title)
        self._selected_label.setText(item_key)


def main() -> int:
    application = QApplication(sys.argv)
    apply_theme(application)

    window = SidebarPreviewWindow()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
