"""Slack page for V2: a BTS-styled preview plus a Slack-safe copy payload.

The page has two deliberately separate layers:

* **Preview** (what you see): BTS look and feel, QR codes generated in the browser
  (``qrcodejs``, like the ACT & SURVEYS tool), special-case notices as callouts.
* **Copy payload** (what "Copiar para Slack" puts on the clipboard): one card per
  session (title, date, facilitator, links, results and the QR image), in plain HTML
  that a Slack canvas accepts. A canvas table cannot hold images (verified by the
  product owner on 2026-11-26), so the payload is not a table. It never contains
  styles, notices or warning rows (NPS-003 fixed by design).

The QR image in the payload is the one drawn in the browser (embedded as PNG when
copying), so it never depends on an external image service. "Copiar QR" copies a
single QR.
"""

from __future__ import annotations

import html
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from engine.slack_canvas_renderer import (
    SLACK_COLUMNS,
    build_client_table_id,
    get_record_sort_key,
    render_cell,
    render_link,
)

QRCODE_SCRIPT = "https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"
QR_PAYLOAD_SIZE = 150

Row = Mapping[str, str]


@dataclass(frozen=True, slots=True)
class PageContext:
    run_id: str
    title: str  # e.g. the selection label
    generated_at: str
    review_count: int


def payload_cards(records: Sequence[Row]) -> str:
    """The Slack copy payload for one client: one card per session, no warnings.

    Each QR is a placeholder ``<img data-row="i">`` pointing at the hosted QR (the same
    image as the Salesforce QR formula); the page swaps it for the PNG drawn in the
    browser when copying and removes the marker attribute.
    """
    return "".join(
        _card(index, record) for index, record in enumerate(_sorted(records))
    )


def _card(index: int, record: Row) -> str:
    """One session card. Sections always appear in the same order, with bold labels:

    Fecha / Facilitador · Encuestas (links) · QR · Link Resultados (Home) ·
    Resultados (``NO`` until the result file exists; then the file replaces it) ·
    divider. "Resultados: NO" is a stable marker a later step can find and fill.
    """

    def text(column: str) -> str:
        return html.escape(" ".join(record.get(column, "").split()))

    surveys = [
        render_link(label, record.get(column, ""))
        for label, column in (
            ("NPS", "Link NPS Survey"),
            ("Facilitators", "Link Insights Facilitators"),
        )
        if record.get(column, "").strip()
    ]
    results_link = render_link("Home", record.get("Link for Results", "")) or "—"

    qr = " ".join(record.get("QR-Code", "").split())
    qr_block = (
        f'<p><img src="{html.escape(qr, quote=True)}" alt="QR" data-row="{index}" '
        f'width="{QR_PAYLOAD_SIZE}" height="{QR_PAYLOAD_SIZE}"></p>'
        if qr
        else "<p><b>QR:</b> pendiente de crear la encuesta</p>"
    )
    return (
        f"<h3>{text('Session')}</h3>"
        f"<p><b>Fecha:</b> {text('Date')} · "
        f"<b>Facilitador:</b> {text('Facilitator') or '—'}</p>"
        f"<p><b>Encuestas:</b> {' · '.join(surveys) or 'pendientes'}</p>"
        f"{qr_block}"
        f"<p><b>Link Resultados:</b> {results_link}</p>"
        f"<p><b>Resultados:</b> {text('Results') or 'NO'}</p>"
        "<hr>"
    )


def render_page(
    rows: Sequence[Row],
    *,
    context: PageContext,
    country_order: Sequence[str],
    special_cases: Mapping[str, Sequence[str]],
) -> str:
    """Whole HTML page. ``special_cases``: Project ID → matched facilitator names."""
    grouped: dict[str, dict[str, list[Row]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row.get("Country", "")][row.get("Client", "")].append(row)

    order = {name: index for index, name in enumerate(country_order)}
    countries = sorted(grouped, key=lambda c: (order.get(c, len(order)), c.casefold()))
    special_rows = [r for r in rows if r.get("Project ID", "") in special_cases]

    sections = "".join(
        _country_section(country, grouped[country], special_cases)
        for country in countries
    )
    body = (
        _brandbar(context)
        + _howto()
        + _kpis(
            len(rows), sum(len(c) for c in grouped.values()), len(special_rows), context
        )
        + (sections or '<p class="empty">No hay sesiones listas en esta selección.</p>')
    )
    return (
        '<!DOCTYPE html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>Tabla para Slack · {html.escape(context.run_id)}</title>\n"
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Inter:wght@400;500;600;700&display=swap">\n'
        f"<style>{_CSS}</style>\n</head>\n<body>\n"
        f'<main class="shell">\n{body}\n</main>\n'
        f"{_MANUAL_COPY}\n"
        f'<script src="{QRCODE_SCRIPT}"></script>\n'
        f"<script>{_JS}</script>\n</body>\n</html>\n"
    )


_MANUAL_COPY = (
    '<div id="manual-copy" hidden><div class="mc-box" role="dialog" aria-modal="true">'
    '<div class="mc-head"><p class="mc-msg"></p>'
    '<button type="button" class="btn" data-close-manual>Cerrar</button></div>'
    '<div class="mc-area"></div></div></div>'
)


# --- sections ----------------------------------------------------------------------


def _brandbar(context: PageContext) -> str:
    return (
        '<header class="brandbar"><span class="mark" aria-hidden="true">BTS</span>'
        '<div class="bb-text"><h1>NPS · Tabla para Slack</h1>'
        f"<p>{html.escape(context.title)} · corrida {html.escape(context.run_id)} · "
        f"generada {html.escape(context.generated_at)}</p></div></header>"
    )


def _howto() -> str:
    return (
        '<section class="card howto"><h2 class="card-title">Cómo usar</h2><ul>'
        "<li><b>Copiar para Slack</b> copia las sesiones del cliente como tarjetas "
        "(título, fecha, facilitador, links y QR), listas para pegar en su canvas.</li>"
        "<li><b>Copiar QR</b> copia un QR suelto, por si hace falta reponer uno.</li>"
        "<li>Los avisos de mail personalizado se ven acá y <b>nunca</b> se copian.</li>"
        "<li>Si el visor no deja copiar (por ejemplo, una vista previa dentro de otra "
        "app), se abre la tabla ya seleccionada: copiala con Ctrl+C. Para el mejor "
        "resultado, abrí este archivo en Chrome o Edge.</li>"
        "</ul></section>"
    )


def _kpis(sessions: int, clients: int, special: int, context: PageContext) -> str:
    tiles = (
        ("Sesiones listas", sessions, ""),
        ("Clientes", clients, ""),
        ("Mail personalizado", special, " tile-warn" if special else ""),
        (
            "Revisión manual",
            context.review_count,
            " tile-warn" if context.review_count else "",
        ),
    )
    return (
        '<section class="kpis">'
        + "".join(
            f'<div class="tile{extra}"><span class="tile-n">{value}</span>'
            f'<span class="tile-l">{label}</span></div>'
            for label, value, extra in tiles
        )
        + "</section>"
    )


def _country_section(
    country: str,
    clients: Mapping[str, Sequence[Row]],
    special_cases: Mapping[str, Sequence[str]],
) -> str:
    total = sum(len(records) for records in clients.values())
    blocks = "".join(
        _client_card(client, clients[client], special_cases)
        for client in sorted(clients, key=str.casefold)
    )
    return (
        f'<section class="country"><h2 class="country-title">{html.escape(country)}'
        f'<span class="pill">{total}</span></h2>{blocks}</section>'
    )


def _client_card(
    client: str, records: Sequence[Row], special_cases: Mapping[str, Sequence[str]]
) -> str:
    table_id = build_client_table_id(client)
    template_id = f"payload-{table_id}"
    ordered = _sorted(records)
    notices = "".join(
        '<div class="callout"><b>Envío por mail por separado:</b> '
        f"{html.escape(record.get('Session', ''))} · "
        f"{html.escape(', '.join(special_cases[record.get('Project ID', '')]))}</div>"
        for record in ordered
        if record.get("Project ID", "") in special_cases
    )
    header = "".join(f"<th>{html.escape(c)}</th>" for c in SLACK_COLUMNS)
    rows = "".join(_preview_row(record, special_cases) for record in ordered)
    return (
        '<article class="card client">'
        f'<div class="client-head"><h3>{html.escape(client)}'
        f'<span class="badge">{len(records)}</span></h3>'
        f'<button type="button" class="btn btn-primary" data-copy="{template_id}">'
        "Copiar para Slack</button></div>"
        f"{notices}"
        '<div class="table-wrap"><table class="preview">'
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
        f'<template id="{template_id}">{payload_cards(records)}</template>'
        '<details class="slack-view"><summary>Ver cómo queda en Slack</summary>'
        '<div class="slack-cards"></div></details>'
        "</article>"
    )


def _preview_row(record: Row, special_cases: Mapping[str, Sequence[str]]) -> str:
    special = record.get("Project ID", "") in special_cases
    cells = []
    for column in SLACK_COLUMNS:
        if column == "QR-Code":
            cells.append(_preview_qr(record))
        else:
            cells.append(f"<td>{render_cell(dict(record), column)}</td>")
    css = ' class="row-special"' if special else ""
    return f"<tr{css}>{''.join(cells)}</tr>"


def _preview_qr(record: Row) -> str:
    link = " ".join(record.get("Link NPS Survey", "").split())
    hosted = " ".join(record.get("QR-Code", "").split())
    if not link:
        return '<td class="qr-cell"><span class="muted">—</span></td>'
    return (
        '<td class="qr-cell">'
        f'<div class="qr" data-text="{html.escape(link, quote=True)}" '
        f'data-fallback="{html.escape(hosted, quote=True)}"></div>'
        '<button type="button" class="btn btn-sm" data-copy-qr>Copiar QR</button></td>'
    )


def _sorted(records: Sequence[Row]) -> list[Row]:
    return sorted(records, key=lambda r: get_record_sort_key(dict(r)))


# --- static assets -----------------------------------------------------------------

_ASSETS = Path(__file__).resolve().parent / "assets"
_CSS = (_ASSETS / "slack_page.css").read_text(encoding="utf-8")
_JS = (_ASSETS / "slack_page.js").read_text(encoding="utf-8")
