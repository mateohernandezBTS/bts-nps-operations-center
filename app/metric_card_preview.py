from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.theme import Colors, Spacing, Typography, apply_theme
from app.widgets.metric_card import MetricCard


class MetricCardPreviewWindow(QMainWindow):
    """Visual validation window for the MetricCard component."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("BTS SELAM - MetricCard Preview")
        self.setMinimumSize(980, 640)

        central_widget = QWidget()

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
            Spacing.XL,
        )
        main_layout.setSpacing(Spacing.LG)

        page_title = QLabel("MetricCard Component Preview")
        page_title.setStyleSheet(
            f"""
            font-size: {Typography.SIZE_PAGE_TITLE}px;
            font-weight: {Typography.WEIGHT_BOLD};
            color: {Colors.BTS_NAVY};
            """
        )

        page_subtitle = QLabel(
            "Operational metrics for the BTS SELAM Operations Center."
        )
        page_subtitle.setStyleSheet(
            f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_BODY_LARGE}px;
            """
        )

        metrics_container = QWidget()
        metrics_layout = QGridLayout(metrics_container)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setHorizontalSpacing(Spacing.LG)
        metrics_layout.setVerticalSpacing(Spacing.LG)

        ready_card = MetricCard(
            label="READY",
            value="21",
            helper_text="Records ready for NPS creation",
            tone="success",
            accent_text="Complete",
        )

        review_card = MetricCard(
            label="REVIEW",
            value="1",
            helper_text="Record requiring manual attention",
            tone="warning",
            accent_text="Action needed",
        )

        sources_card = MetricCard(
            label="SOURCES",
            value="3 / 3",
            helper_text="Argentina, Brazil and Mexico received",
            tone="info",
            accent_text="Ready",
        )

        environment_card = MetricCard(
            label="ENVIRONMENT",
            value="TEST",
            helper_text="Current execution environment",
            tone="neutral",
            accent_text="Safe mode",
        )

        failed_card = MetricCard(
            label="FAILED",
            value="0",
            helper_text="No failed records in the latest run",
            tone="error",
            accent_text="No issues",
        )

        last_run_card = MetricCard(
            label="LAST RUN",
            value="Completed",
            helper_text="Weekly process finished successfully",
            tone="success",
        )

        metrics_layout.addWidget(ready_card, 0, 0)
        metrics_layout.addWidget(review_card, 0, 1)
        metrics_layout.addWidget(sources_card, 0, 2)

        metrics_layout.addWidget(environment_card, 1, 0)
        metrics_layout.addWidget(failed_card, 1, 1)
        metrics_layout.addWidget(last_run_card, 1, 2)

        for column in range(3):
            metrics_layout.setColumnStretch(column, 1)

        main_layout.addWidget(page_title)
        main_layout.addWidget(page_subtitle)
        main_layout.addWidget(metrics_container)
        main_layout.addStretch()

        self.setCentralWidget(central_widget)


def main() -> int:
    application = QApplication(sys.argv)
    apply_theme(application)

    window = MetricCardPreviewWindow()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())