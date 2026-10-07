from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QWidget,
)

from app.theme import (
    Colors,
    Spacing,
    Typography,
)
from app.widgets.card import Card
from app.widgets.status_badge import StatusBadge


class SourcesCard(Card):
    """
    Expected source inventory for a Weekly Run.

    The component contains presentation logic only.
    Source detection remains the responsibility of the backend.
    """

    SOURCE_NAMES = (
        "Argentina Upcoming NPS",
        "Brazil Upcoming NPS",
        "Mexico Upcoming NPS",
    )

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(
            parent=parent,
            title="Expected Sources",
            subtitle=(
                "Upcoming NPS reports required before the weekly run."
            ),
        )

        self.setObjectName("weeklyRunSourcesCard")

        self._source_badges: list[StatusBadge] = []

        self._build_ui()
        self._apply_styles()

        self.set_not_checked()

    def _build_ui(self) -> None:
        container = QWidget(self)
        container.setObjectName(
            "weeklyRunSourcesContainer"
        )

        layout = QGridLayout(container)
        layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        layout.setHorizontalSpacing(
            Spacing.MD
        )
        layout.setVerticalSpacing(
            Spacing.MD
        )

        for row, source_name in enumerate(
            self.SOURCE_NAMES
        ):
            indicator = QLabel(
                "●",
                container,
            )
            indicator.setObjectName(
                "weeklyRunSourceIndicator"
            )

            source_label = QLabel(
                source_name,
                container,
            )
            source_label.setObjectName(
                "weeklyRunSourceLabel"
            )

            status_badge = StatusBadge(
                "Not checked",
                container,
                tone="neutral",
                uppercase=False,
            )

            self._source_badges.append(
                status_badge
            )

            layout.addWidget(
                indicator,
                row,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )
            layout.addWidget(
                source_label,
                row,
                1,
                Qt.AlignmentFlag.AlignVCenter,
            )
            layout.addWidget(
                status_badge,
                row,
                2,
                Qt.AlignmentFlag.AlignVCenter,
            )

        layout.setColumnStretch(1, 1)

        self.add_widget(container)

    def set_not_checked(self) -> None:
        """
        Reset every expected source to its initial state.
        """

        for badge in self._source_badges:
            badge.set_status(
                text="Not checked",
                tone="neutral",
            )

    def set_sources_received(
        self,
        received_count: int,
    ) -> None:
        """
        Mark sources as received or missing using backend inventory count.

        The order corresponds to the fixed expected source order used
        by the Weekly Run presentation.
        """

        safe_count = max(
            0,
            min(
                int(received_count),
                len(self._source_badges),
            ),
        )

        for index, badge in enumerate(
            self._source_badges
        ):
            received = index < safe_count

            badge.set_status(
                text=(
                    "Received"
                    if received
                    else "Missing"
                ),
                tone=(
                    "success"
                    if received
                    else "error"
                ),
            )

    def set_all_received(self) -> None:
        """
        Mark all expected sources as received.
        """

        self.set_sources_received(
            len(self._source_badges)
        )

    def source_count(self) -> int:
        """
        Return the number of expected source entries.
        """

        return len(self._source_badges)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#weeklyRunSourcesContainer {{
                background-color: transparent;
            }}

            QLabel#weeklyRunSourceIndicator {{
                color: {Colors.BTS_PINK};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#weeklyRunSourceLabel {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
                font-weight: {Typography.WEIGHT_NORMAL};
            }}
            """
        )