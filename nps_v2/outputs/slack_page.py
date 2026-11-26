"""Slack page for V2: a BTS-styled preview plus a Slack-safe copy payload.

The page has two deliberately separate layers:

* **Preview** (what you see): BTS look and feel, QR codes generated in the browser
  (``qrcodejs``, like the ACT & SURVEYS tool), special-case notices as callouts.
* **Copy payload** (what "Copiar para Slack" puts on the clipboard): exactly the plain
  table the desktop renderer always copied (same ``<table id=…>``, columns, cell
  rendering and row order), built with the certified renderer's own helpers. It never
  contains styles, notices or warning rows (NPS-003 fixed by design). The only
  addition is the QR cell, which carries the QR image.

"Copiar QR" copies one QR as a PNG image, for pasting into a canvas cell by hand.
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
)

QRCODE_SCRIPT = "https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"
QR_PAYLOAD_SIZE = 150
QR_PREVIEW_SIZE = 96

Row = Mapping[str, str]


@dataclass(frozen=True, slots=True)
class PageContext:
    run_id: str
    title: str  # e.g. the selection label
    generated_at: str
    review_count: int


def qr_payload_cell(url: str) -> str:
    """QR cell of the copy payload: the QR image (empty when there is no survey)."""
    clean = " ".join(str(url or "").split())
    if not clean:
        return ""
    return (
        f'<img src="{html.escape(clean, quote=True)}" alt="QR" '
        f'width="{QR_PAYLOAD_SIZE}" height="{QR_PAYLOAD_SIZE}">'
    )


def payload_cell(record: Row, column: str) -> str:
    if column == "QR-Code":
        return qr_payload_cell(record.get(column, ""))
    return render_cell(dict(record), column)


def payload_table(client: str, records: Sequence[Row]) -> str:
    """The Slack copy payload for one client: the legacy plain table, no warnings."""
    header = "".join(f"<th>{html.escape(column)}</th>" for column in SLACK_COLUMNS)
    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{payload_cell(record, column)}</td>" for column in SLACK_COLUMNS
        )
        + "</tr>"
        for record in _sorted(records)
    )
    return (
        f'<table id="{build_client_table_id(client)}">'
        f"<thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>"
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
        f'<script src="{QRCODE_SCRIPT}"></script>\n'
        f"<script>{_JS}</script>\n</body>\n</html>\n"
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
        "<li><b>Copiar para Slack</b> copia la tabla del cliente en el formato de "
        "siempre (sin estilos ni avisos), lista para pegar en su canvas.</li>"
        "<li>La tabla copiada lleva la imagen del QR. Si Slack no la muestra, usá "
        "<b>Copiar QR</b> en la fila y pegala en la celda.</li>"
        "<li>Los avisos de mail personalizado se ven acá y <b>nunca</b> se copian.</li>"
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
        f'<template id="{template_id}">{payload_table(client, records)}</template>'
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
