from __future__ import annotations

from PySide6.QtWidgets import QLayout, QWidget


def clear_layout(layout: QLayout) -> None:
    """
    Remove and delete every widget and nested layout contained in a layout.

    This helper is used when replacing the active application view.
    """

    while layout.count():
        item = layout.takeAt(0)

        widget = item.widget()
        child_layout = item.layout()

        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
            continue

        if child_layout is not None:
            clear_layout(child_layout)
            child_layout.deleteLater()


def replace_widget(
    current_widget: QWidget | None,
    new_widget: QWidget,
) -> QWidget:
    """
    Safely detach the current widget and return the replacement.

    The caller remains responsible for inserting the new widget into
    the appropriate layout.
    """

    if current_widget is not None:
        current_widget.setParent(None)
        current_widget.deleteLater()

    return new_widget