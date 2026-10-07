from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.theme import (
    Colors,
    Radius,
    Spacing,
    Typography,
)


class Card(QFrame):
    """
    Reusable BTS card container.

    The visual card surface lives in an internal QFrame. This prevents
    subclasses from accidentally removing the card background or border
    when they apply their own stylesheets.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        elevated: bool = True,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("btsCardHost")

        self._title_text = title
        self._subtitle_text = subtitle
        self._elevated = elevated

        self._build_card_structure()
        self._apply_surface_styles()

    def _build_card_structure(self) -> None:
        # Transparent host.
        host_layout = QVBoxLayout(self)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)

        # Permanent visual surface.
        self.surface_frame = QFrame(self)
        self.surface_frame.setObjectName(
            "btsCardSurface"
        )

        host_layout.addWidget(
            self.surface_frame
        )

        # Keep root_layout for compatibility with existing code.
        self.root_layout = QVBoxLayout(
            self.surface_frame
        )
        self.root_layout.setContentsMargins(
            Spacing.LG,
            Spacing.LG,
            Spacing.LG,
            Spacing.LG,
        )
        self.root_layout.setSpacing(
            Spacing.MD
        )

        if self._title_text:
            self.title_label = QLabel(
                self._title_text,
                self.surface_frame,
            )
            self.title_label.setObjectName(
                "btsCardTitle"
            )
            self.root_layout.addWidget(
                self.title_label
            )
        else:
            self.title_label = None

        if self._subtitle_text:
            self.subtitle_label = QLabel(
                self._subtitle_text,
                self.surface_frame,
            )
            self.subtitle_label.setObjectName(
                "btsCardSubtitle"
            )
            self.subtitle_label.setWordWrap(True)

            self.root_layout.addWidget(
                self.subtitle_label
            )
        else:
            self.subtitle_label = None

        self.content_widget = QWidget(
            self.surface_frame
        )
        self.content_widget.setObjectName(
            "btsCardContent"
        )

        self.content_layout = QVBoxLayout(
            self.content_widget
        )
        self.content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.content_layout.setSpacing(
            Spacing.MD
        )

        self.root_layout.addWidget(
            self.content_widget
        )

    def add_widget(
        self,
        widget: QWidget,
    ) -> None:
        self.content_layout.addWidget(
            widget
        )

    def add_stretch(
        self,
        stretch: int = 1,
    ) -> None:
        self.content_layout.addStretch(
            stretch
        )

    def set_title(
        self,
        title: str,
    ) -> None:
        self._title_text = title

        if self.title_label is None:
            self.title_label = QLabel(
                title,
                self.surface_frame,
            )
            self.title_label.setObjectName(
                "btsCardTitle"
            )

            self.root_layout.insertWidget(
                0,
                self.title_label,
            )
        else:
            self.title_label.setText(
                title
            )

    def set_subtitle(
        self,
        subtitle: str,
    ) -> None:
        self._subtitle_text = subtitle

        if self.subtitle_label is None:
            self.subtitle_label = QLabel(
                subtitle,
                self.surface_frame,
            )
            self.subtitle_label.setObjectName(
                "btsCardSubtitle"
            )
            self.subtitle_label.setWordWrap(
                True
            )

            insert_index = (
                1
                if self.title_label is not None
                else 0
            )

            self.root_layout.insertWidget(
                insert_index,
                self.subtitle_label,
            )
        else:
            self.subtitle_label.setText(
                subtitle
            )

    def set_elevated(
        self,
        elevated: bool,
    ) -> None:
        self._elevated = elevated
        self._apply_surface_styles()

    def _apply_surface_styles(self) -> None:
        """
        Style the internal surface directly.

        Subclasses may safely call self.setStyleSheet() afterwards
        without deleting these card surface styles.
        """

        border_color = (
            Colors.BORDER_LIGHT
            if self._elevated
            else Colors.BORDER
        )

        self.surface_frame.setStyleSheet(
            f"""
            QFrame#btsCardSurface {{
                background-color: {Colors.SURFACE};
                border: 1px solid {border_color};
                border-radius: {Radius.LARGE}px;
            }}

            QLabel#btsCardTitle {{
                color: {Colors.TEXT_PRIMARY};
                background-color: transparent;
                border: none;
                font-size: {Typography.SIZE_SUBTITLE}px;
                font-weight: {Typography.WEIGHT_SEMIBOLD};
            }}

            QLabel#btsCardSubtitle {{
                color: {Colors.TEXT_SECONDARY};
                background-color: transparent;
                border: none;
                font-size: {Typography.SIZE_BODY_SMALL}px;
                font-weight: {Typography.WEIGHT_NORMAL};
            }}

            QWidget#btsCardContent {{
                background-color: transparent;
                border: none;
            }}
            """
        )