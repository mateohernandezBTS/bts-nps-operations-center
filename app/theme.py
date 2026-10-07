from __future__ import annotations


class Colors:
    """
    Centralized color palette for the BTS SELAM desktop application.

    The current brand direction uses white surfaces, dark navigation
    and a provisional BTS pink accent.

    BTS_RED and BTS_RED_HOVER remain as compatibility aliases while
    existing components are migrated gradually.
    """

    # -----------------------------------------------------------------
    # Brand
    # -----------------------------------------------------------------

    BTS_PINK = "#E6007E"
    BTS_PINK_HOVER = "#C7006D"
    BTS_PINK_PRESSED = "#AD005F"
    BTS_PINK_BACKGROUND = "#FCE8F3"

    BTS_BLACK = "#111111"
    BTS_CHARCOAL = "#1B1B1F"
    BTS_CHARCOAL_LIGHT = "#29292F"

    # Compatibility aliases used by existing components.
    BTS_RED = BTS_PINK
    BTS_RED_HOVER = BTS_PINK_HOVER

    # Compatibility aliases for current navigation components.
    BTS_NAVY = BTS_CHARCOAL
    BTS_NAVY_LIGHT = BTS_CHARCOAL_LIGHT

    # -----------------------------------------------------------------
    # Backgrounds and surfaces
    # -----------------------------------------------------------------

    APP_BACKGROUND = "#F6F6F7"
    SURFACE = "#FFFFFF"
    SURFACE_ALT = "#F1F1F3"
    SURFACE_HOVER = "#EBEBEE"

    SIDEBAR_BACKGROUND = BTS_CHARCOAL
    SIDEBAR_BACKGROUND_HOVER = BTS_CHARCOAL_LIGHT
    SIDEBAR_ACTIVE = BTS_PINK

    # -----------------------------------------------------------------
    # Text
    # -----------------------------------------------------------------

    TEXT_PRIMARY = "#17171A"
    TEXT_SECONDARY = "#5F6068"
    TEXT_MUTED = "#92949E"

    TEXT_ON_DARK = "#FFFFFF"
    TEXT_ON_ACCENT = "#FFFFFF"

    # -----------------------------------------------------------------
    # Borders
    # -----------------------------------------------------------------

    BORDER = "#D7D8DE"
    BORDER_LIGHT = "#E8E8EC"
    BORDER_STRONG = "#B8BAC3"

    # -----------------------------------------------------------------
    # Functional status colors
    # -----------------------------------------------------------------

    SUCCESS = "#16865C"
    SUCCESS_BACKGROUND = "#E8F6F0"

    WARNING = "#B76E00"
    WARNING_BACKGROUND = "#FFF4DD"

    ERROR = "#C9362B"
    ERROR_BACKGROUND = "#FDECEA"

    INFO = "#3367A8"
    INFO_BACKGROUND = "#EAF2FB"

    NEUTRAL = "#667085"
    NEUTRAL_BACKGROUND = "#F2F4F7"


class Typography:
    """Typography tokens used throughout the application."""

    FONT_FAMILY = "Segoe UI"

    SIZE_CAPTION = 11
    SIZE_BODY_SMALL = 12
    SIZE_BODY = 13
    SIZE_BODY_LARGE = 14
    SIZE_SUBTITLE = 16
    SIZE_TITLE = 20
    SIZE_PAGE_TITLE = 26
    SIZE_METRIC = 30

    WEIGHT_NORMAL = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700


class Spacing:
    """Spacing scale in pixels."""

    XXS = 4
    XS = 8
    SM = 12
    MD = 16
    LG = 24
    XL = 32
    XXL = 40


class Radius:
    """Corner radius values."""

    SMALL = 6
    MEDIUM = 10
    LARGE = 14
    PILL = 999


class Sizes:
    """Shared dimensions for major application elements."""

    SIDEBAR_WIDTH = 232
    TOOLBAR_HEIGHT = 64
    STATUS_BAR_HEIGHT = 34

    BUTTON_HEIGHT = 40
    INPUT_HEIGHT = 40

    CARD_MIN_HEIGHT = 120
    METRIC_CARD_MIN_WIDTH = 190


class Theme:
    """Generate the global Qt stylesheet for the application."""

    @staticmethod
    def global_stylesheet() -> str:
        return f"""
        QWidget {{
            font-family: "{Typography.FONT_FAMILY}";
            font-size: {Typography.SIZE_BODY}px;
            color: {Colors.TEXT_PRIMARY};
            background-color: transparent;
        }}

        QMainWindow {{
            background-color: {Colors.APP_BACKGROUND};
        }}

        QLabel {{
            background-color: transparent;
        }}

        QFrame {{
            background-color: transparent;
            border: none;
        }}

        QPushButton {{
            min-height: {Sizes.BUTTON_HEIGHT}px;
            padding: 0 {Spacing.MD}px;

            border-radius: {Radius.SMALL}px;
            border: 1px solid {Colors.BORDER};

            background-color: {Colors.SURFACE};
            color: {Colors.TEXT_PRIMARY};

            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}

        QPushButton:hover {{
            background-color: {Colors.SURFACE_HOVER};
            border-color: {Colors.BORDER_STRONG};
        }}

        QPushButton:pressed {{
            background-color: {Colors.BORDER_LIGHT};
        }}

        QPushButton:focus {{
            border: 1px solid {Colors.BTS_PINK};
        }}

        QPushButton:disabled {{
            background-color: {Colors.SURFACE_ALT};
            color: {Colors.TEXT_MUTED};
            border-color: {Colors.BORDER_LIGHT};
        }}

        QLineEdit,
        QComboBox,
        QDateEdit {{
            min-height: {Sizes.INPUT_HEIGHT}px;
            padding: 0 {Spacing.SM}px;

            border-radius: {Radius.SMALL}px;
            border: 1px solid {Colors.BORDER};

            background-color: {Colors.SURFACE};
            color: {Colors.TEXT_PRIMARY};

            selection-background-color: {Colors.BTS_PINK_BACKGROUND};
            selection-color: {Colors.TEXT_PRIMARY};
        }}

        QLineEdit:hover,
        QComboBox:hover,
        QDateEdit:hover {{
            border-color: {Colors.BORDER_STRONG};
        }}

        QLineEdit:focus,
        QComboBox:focus,
        QDateEdit:focus {{
            border: 1px solid {Colors.BTS_PINK};
        }}

        QComboBox QAbstractItemView {{
            background-color: {Colors.SURFACE};
            color: {Colors.TEXT_PRIMARY};

            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.SMALL}px;

            outline: none;

            selection-background-color: {Colors.BTS_PINK_BACKGROUND};
            selection-color: {Colors.TEXT_PRIMARY};
        }}

        QTableView,
        QTableWidget {{
            background-color: {Colors.SURFACE};
            alternate-background-color: {Colors.SURFACE_ALT};

            border: 1px solid {Colors.BORDER_LIGHT};
            border-radius: {Radius.MEDIUM}px;

            gridline-color: {Colors.BORDER_LIGHT};

            selection-background-color: {Colors.BTS_PINK_BACKGROUND};
            selection-color: {Colors.TEXT_PRIMARY};
        }}

        QHeaderView::section {{
            background-color: {Colors.SURFACE_ALT};
            color: {Colors.TEXT_SECONDARY};

            padding: {Spacing.SM}px;

            border: none;
            border-bottom: 1px solid {Colors.BORDER};

            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}

        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical {{
            background: {Colors.BORDER};
            border-radius: 5px;
            min-height: 28px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {Colors.TEXT_MUTED};
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QToolTip {{
            background-color: {Colors.BTS_CHARCOAL};
            color: {Colors.TEXT_ON_DARK};

            border: 1px solid {Colors.BTS_CHARCOAL_LIGHT};
            border-radius: {Radius.SMALL}px;

            padding: {Spacing.XS}px;
        }}
        """


def apply_theme(application) -> None:
    """Apply the global BTS SELAM theme to a QApplication instance."""

    application.setStyleSheet(
        Theme.global_stylesheet()
    )