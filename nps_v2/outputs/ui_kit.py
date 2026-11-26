"""Shared look and feel of every V2 HTML view: Ionic components with the BTS theme.

Decision D-V2-11 (PO, 2026-11-26): every page a user sees or operates (the Slack page
today; the survey-creation preview and approval in V2-2, and later views) is built on
this kit, so all views look and behave the same.

* **Ionic** web components (``@ionic/core``, exact version, iOS mode) are loaded from
  the CDN at view time; nothing is installed in the repository or the skill.
* **BTS theme** through Ionic's CSS variables (magenta, charcoal, Inter).
* **Fallback is mandatory:** every ``ion-*`` element used by a view has a
  ``:not(:defined)`` rule, so if the viewer blocks the CDN the page still works in the
  plain BTS style (without search, tabs or animations). Tests enforce it.
* Shared behaviour in ``window.BTSUI``: ``ready``, ``notify`` (toast, or a short label
  on the clicked control without Ionic), ``copyRich`` (clipboard with three fallbacks)
  and ``manualCopy`` (selected content for Ctrl+C).
"""

from __future__ import annotations

import html
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

IONIC_VERSION = "8.8.19"
IONIC_MODE = "ios"
IONIC_SCRIPT = (
    f"https://cdn.jsdelivr.net/npm/@ionic/core@{IONIC_VERSION}/dist/ionic/ionic.esm.js"
)
FONT_STYLESHEET = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
_SAFE_URL = re.compile(r"^https?://", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Tile:
    label: str
    value: int
    warn: bool = False


def text(value: object) -> str:
    """Escaped text with whitespace collapsed."""
    return html.escape(" ".join(str(value).split()))


def attr(value: object) -> str:
    """Escaped attribute value with whitespace collapsed."""
    return html.escape(" ".join(str(value).split()), quote=True)


def safe_url(value: str) -> str:
    """The URL if it is http(s); otherwise empty (never a script or data URL)."""
    url = " ".join(value.split())
    return url if _SAFE_URL.match(url) else ""


def brandbar(title: str, subtitle: str) -> str:
    return (
        '<div class="brandbar"><span class="mark">BTS</span>'
        f"<div><h1>{text(title)}</h1><p>{text(subtitle)}</p></div></div>"
    )


def kpi_tiles(tiles: Sequence[Tile]) -> str:
    return (
        '<section class="kpis">'
        + "".join(
            f'<div class="tile{" warn" if tile.warn and tile.value else ""}">'
            f'<span class="tile-n">{tile.value}</span>'
            f'<span class="tile-l">{text(tile.label)}</span></div>'
            for tile in tiles
        )
        + "</section>"
    )


def render_document(
    *,
    title: str,
    header: str,
    body: str,
    css: str = "",
    js: str = "",
    scripts: Sequence[str] = (),
) -> str:
    """A complete page: sticky header (``header`` HTML), main body, kit and page assets.

    ``scripts`` are extra classic scripts (exact versions) loaded before the page JS.
    """
    extra = "".join(f'<script src="{attr(src)}"></script>\n' for src in scripts)
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, '
        'viewport-fit=cover">\n'
        f"<title>{text(title)}</title>\n"
        f'<link rel="stylesheet" href="{FONT_STYLESHEET}">\n'
        f"<style>{KIT_CSS}{css}</style>\n"
        f"<script>window.Ionic={{config:{{mode:'{IONIC_MODE}'}}}};</script>\n"
        f'<script type="module" src="{IONIC_SCRIPT}"></script>\n'
        "</head>\n<body>\n"
        f'<header class="topbar">{header}</header>\n'
        f'<main class="shell">\n{body}\n</main>\n'
        f"{_OVERLAYS}\n{extra}"
        f"<script>{KIT_JS}</script>\n<script>{js}</script>\n</body>\n</html>\n"
    )


_OVERLAYS = (
    '<ion-toast id="bts-toast" duration="1800" position="bottom"></ion-toast>'
    '<div id="manual-copy" hidden><div class="mc-box" role="dialog" aria-modal="true">'
    '<div class="mc-head"><p class="mc-msg"></p>'
    '<button type="button" class="mc-close" data-close-manual>Close</button></div>'
    '<div class="mc-area"></div></div></div>'
)

_ASSETS = Path(__file__).resolve().parent / "assets"
KIT_CSS = (_ASSETS / "ui_kit.css").read_text(encoding="utf-8")
KIT_JS = (_ASSETS / "ui_kit.js").read_text(encoding="utf-8")
