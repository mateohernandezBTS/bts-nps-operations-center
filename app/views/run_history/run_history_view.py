from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.controllers.ui_controller import (
    RunHistoryItem,
    RunHistoryState,
)
from app.theme import (
    Colors,
    Spacing,
    Typography,
)
from app.widgets.card import Card
from app.widgets.secondary_button import SecondaryButton


class RunHistoryView(QWidget):
    """
    Read-only list of persisted weekly runs.

    The view does not read files or resolve outputs directly.
    It displays RunHistoryState and emits the selected run when
    the user requests to inspect its outputs.
    """

    view_output_requested = Signal(object)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("runHistoryView")

        self._runs: tuple[
            RunHistoryItem,
            ...
        ] = ()

        self._build_ui()
        self._connect_signals()
        self._apply_styles()

        self.set_empty_state()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            Spacing.XL,
            Spacing.LG,
            Spacing.XL,
            Spacing.XL,
        )
        root_layout.setSpacing(
            Spacing.LG
        )

        title = QLabel(
            "Run History",
            self,
        )
        title.setObjectName(
            "runHistoryTitle"
        )

        description = QLabel(
            "Review previous TEST and PRODUCTION weekly runs "
            "and inspect their generated outputs.",
            self,
        )
        description.setObjectName(
            "runHistoryDescription"
        )
        description.setWordWrap(True)

        root_layout.addWidget(title)
        root_layout.addWidget(description)

        root_layout.addWidget(
            self._build_history_card()
        )

        root_layout.addStretch()

    def _build_history_card(self) -> Card:
        card = Card(
            title="Weekly Runs",
            subtitle=(
                "Persisted weekly executions discovered from "
                "TEST and PRODUCTION outputs."
            ),
        )

        container = QWidget(card)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            0,
            Spacing.XS,
            0,
            0,
        )
        layout.setSpacing(
            Spacing.MD
        )

        self.history_table = QTableWidget(
            0,
            8,
            container,
        )

        self.history_table.setHorizontalHeaderLabels(
            (
                "Weekly Run",
                "Environment",
                "Status",
                "Reference Monday",
                "Window",
                "Ready",
                "Review",
                "Clients",
            )
        )

        self.history_table.verticalHeader().setVisible(
            False
        )

        self.history_table.setAlternatingRowColors(
            True
        )

        self.history_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.history_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )

        self.history_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.history_table.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus
        )

        self.history_table.setMinimumHeight(
            300
        )

        header = self.history_table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            6,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            7,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        self.empty_label = QLabel(
            "No persisted weekly runs were found.",
            container,
        )
        self.empty_label.setObjectName(
            "runHistoryEmpty"
        )
        self.empty_label.setWordWrap(True)

        self.view_output_button = SecondaryButton(
            "View Output",
            container,
            minimum_width=160,
        )
        self.view_output_button.setEnabled(
            False
        )

        layout.addWidget(
            self.history_table
        )
        layout.addWidget(
            self.empty_label
        )
        layout.addWidget(
            self.view_output_button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )

        card.add_widget(container)

        return card

    def _connect_signals(self) -> None:
        self.history_table.itemSelectionChanged.connect(
            self._handle_selection_changed
        )

        self.history_table.itemDoubleClicked.connect(
            self._handle_double_click
        )

        self.view_output_button.clicked.connect(
            self._emit_selected_run
        )

    def apply_state(
        self,
        state: RunHistoryState,
    ) -> None:
        """
        Display persisted runs ordered by the controller.
        """

        self._runs = tuple(
            state.runs or ()
        )

        self.history_table.clearContents()
        self.history_table.setRowCount(
            len(self._runs)
        )

        for row_index, run in enumerate(
            self._runs
        ):
            values = (
                run.weekly_run_id,
                run.environment,
                self._display_status(
                    run.status
                ),
                run.reference_date,
                self._window_text(
                    run
                ),
                str(run.ready_records),
                str(run.review_records),
                str(run.clients),
            )

            for column_index, value in enumerate(
                values
            ):
                item = QTableWidgetItem(
                    value
                )

                if column_index in {
                    5,
                    6,
                    7,
                }:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                self.history_table.setItem(
                    row_index,
                    column_index,
                    item,
                )

            self.history_table.setRowHeight(
                row_index,
                42,
            )

        has_runs = bool(
            self._runs
        )

        self.history_table.setVisible(
            has_runs
        )

        self.empty_label.setVisible(
            not has_runs
        )

        self.view_output_button.setEnabled(
            False
        )

        self.history_table.clearSelection()

    def set_empty_state(self) -> None:
        self._runs = ()

        self.history_table.clearContents()
        self.history_table.setRowCount(0)
        self.history_table.setVisible(False)

        self.empty_label.setVisible(True)

        self.view_output_button.setEnabled(
            False
        )

    def selected_run(
        self,
    ) -> RunHistoryItem | None:
        """
        Return the currently selected history record.
        """

        selected_rows = (
            self.history_table
            .selectionModel()
            .selectedRows()
        )

        if not selected_rows:
            return None

        row_index = (
            selected_rows[0].row()
        )

        if not (
            0
            <= row_index
            < len(self._runs)
        ):
            return None

        return self._runs[
            row_index
        ]

    def _handle_selection_changed(
        self,
    ) -> None:
        self.view_output_button.setEnabled(
            self.selected_run()
            is not None
        )

    def _handle_double_click(
        self,
        item: QTableWidgetItem,
    ) -> None:
        if item is None:
            return

        self._emit_selected_run()

    def _emit_selected_run(
        self,
    ) -> None:
        run = self.selected_run()

        if run is None:
            return

        self.view_output_requested.emit(
            run
        )

    @staticmethod
    def _window_text(
        run: RunHistoryItem,
    ) -> str:
        if (
            run.window_start
            and run.window_end
        ):
            return (
                f"{run.window_start}"
                " - "
                f"{run.window_end}"
            )

        return "-"

    @staticmethod
    def _display_status(
        status: str,
    ) -> str:
        return (
            (status or "UNKNOWN")
            .replace("_", " ")
            .strip()
            .title()
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget#runHistoryView {{
                background-color: transparent;
            }}

            QLabel#runHistoryTitle {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {Typography.SIZE_PAGE_TITLE}px;
                font-weight: {Typography.WEIGHT_BOLD};
            }}

            QLabel#runHistoryDescription {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY_LARGE}px;
            }}

            QLabel#runHistoryEmpty {{
                color: {Colors.TEXT_MUTED};
                background-color: transparent;
                font-size: {Typography.SIZE_BODY}px;
                padding: {Spacing.MD}px 0;
            }}

            QTableWidget {{
                background-color: {Colors.SURFACE};
                alternate-background-color: {Colors.SURFACE_ALT};
                color: {Colors.TEXT_PRIMARY};

                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: 8px;

                gridline-color: {Colors.BORDER_LIGHT};

                selection-background-color: {Colors.BTS_PINK_BACKGROUND};
                selection-color: {Colors.TEXT_PRIMARY};
            }}

            QHeaderView::section {{
                background-color: {Colors.SURFACE_ALT};
                color: {Colors.TEXT_SECONDARY};

                border: none;
                border-bottom: 1px solid {Colors.BORDER};

                padding: {Spacing.SM}px;

                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}
            """
        )