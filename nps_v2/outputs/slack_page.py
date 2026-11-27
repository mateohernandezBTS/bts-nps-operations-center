"""Slack page for V2: an Ionic + BTS preview plus a Slack-safe copy payload.

The page has two deliberately separate layers:

* **Preview** (what you see): built on the shared UI kit (``ui_kit``: Ionic, iOS mode,
  BTS theme, mandatory fallback). Search by client, session or facilitator, tabs by
  country, one card per client with its sessions, QR codes drawn in the browser
  (``qrcodejs``; click a QR to copy it), special-case notices as callouts, and "See
  how it looks in Slack".
* **Copy payload** (what "Copy for Slack" puts on the clipboard): one card per
  session (title, date, facilitator, links, results and the QR image), in plain HTML
  that a Slack canvas accepts. A canvas table cannot hold images (verified by the
  product owner on 2026-11-26), so the payload is not a table. It never contains
  styles, notices or warning rows (NPS-003 fixed by design).

The QR image in the payload is the one drawn in the browser (embedded as PNG when
copying), so it never depends on an external image service. "Copy QR" copies a
single QR.
"""

from __future__ import annotations

import html
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from engine.slack_canvas_renderer import (
    build_client_table_id,
    get_record_sort_key,
    render_link,
)
from nps_v2.outputs import special_email
from nps_v2.outputs.ui_kit import (
    Tile,
    attr,
    brandbar,
    kpi_tiles,
    render_document,
    safe_url,
    text,
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
    week_start: date | None = None  # first day of the selection (e-mail subject)


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

    Date / Facilitator · Surveys (links) · QR · Link for Results (Home) ·
    Results (``NO`` until the result file exists; then the file replaces it) ·
    divider. "Results: NO" is a stable marker a later step can find and fill.
    Labels follow the desktop Slack columns (``SLACK_COLUMNS``).
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
        else "<p><b>QR:</b> survey not created yet</p>"
    )
    return (
        f"<h3>{text('Session')}</h3>"
        f"<p><b>Date:</b> {text('Date')} · "
        f"<b>Facilitator:</b> {text('Facilitator') or '—'}</p>"
        f"<p><b>Surveys:</b> {' · '.join(surveys) or 'not created yet'}</p>"
        f"{qr_block}"
        f"<p><b>Link for Results:</b> {results_link}</p>"
        f"<p><b>Results:</b> {text('Results') or 'NO'}</p>"
        "<hr>"
    )


def render_page(
    rows: Sequence[Row],
    *,
    context: PageContext,
    country_order: Sequence[str],
    special_cases: Mapping[str, Sequence[str]],
    email_languages: Mapping[str, special_email.EmailLanguage] | None = None,
) -> str:
    """Whole HTML page. ``special_cases``: Project ID → matched facilitator names;
    ``email_languages``: facilitator name → language of their e-mail (Spanish when
    missing)."""
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
    tiles = kpi_tiles(
        (
            Tile("Sessions ready", len(rows)),
            Tile("Clients", sum(len(c) for c in grouped.values())),
            Tile("Personalised e-mail", len(special_rows), warn=True),
            Tile("Manual review", context.review_count, warn=True),
        )
    )
    empty = (
        '<p class="empty">No sessions are ready in this selection.</p>'
        if not sections
        else '<p id="no-results" class="empty" hidden>No sessions match the search.</p>'
    )
    header = brandbar(
        "NPS · Slack table",
        f"{context.title} · run {context.run_id} · generated {context.generated_at}",
    ) + _tools(countries)
    return render_document(
        title=f"Slack table · {context.run_id}",
        header=header,
        body=_HELP
        + tiles
        + _emails(rows, special_cases, context, email_languages or {})
        + sections
        + empty,
        css=_CSS,
        js=_JS,
        scripts=(QRCODE_SCRIPT,),
    )


def _emails(
    rows: Sequence[Row],
    special_cases: Mapping[str, Sequence[str]],
    context: PageContext,
    languages: Mapping[str, special_email.EmailLanguage],
) -> str:
    """One card per watch-listed facilitator: the personalised e-mail to copy."""
    grouped = special_email.by_facilitator(_sorted(rows), special_cases)
    if not grouped:
        return ""
    subject = special_email.subject(context.week_start)
    cards = "".join(
        _email_card(
            index,
            name,
            records,
            subject,
            languages.get(name) or special_email.EmailLanguage("es", "default"),
        )
        for index, (name, records) in enumerate(grouped.items())
    )
    return (
        '<section class="emails"><h2 class="section-title">Personalised e-mails'
        f'<ion-badge class="count">{len(grouped)}</ion-badge></h2>'
        '<p class="meta">These facilitators get their links by e-mail. Copy the '
        "subject and the e-mail, paste them into a new Outlook message and send it "
        f"yourself.</p>{cards}</section>"
    )


def _email_card(
    index: int,
    name: str,
    sessions: Sequence[Row],
    subject: str,
    language: special_email.EmailLanguage,
) -> str:
    template_id = f"email-{index}"
    records = special_email.day_first(sessions)
    missing = [r.get("Session", "") for r in records if not r.get("Link NPS Survey")]
    warning = (
        '<div class="callout"><b>Surveys not created yet:</b> '
        f"{text('; '.join(missing))}. Create them first, or the e-mail goes without "
        "their links and QR.</div>"
        if missing
        else ""
    )
    items = "".join(_session_item(i, record, {}) for i, record in enumerate(records))
    count = len(records)
    body = (
        special_email.intro(name, count, language.code)
        + payload_cards(records)
        + special_email.closing(language.code)
    )
    return (
        f'<ion-card class="email" data-facilitator="{attr(name)}">'
        '<div class="card-head"><div>'
        f"<ion-card-title>E-mail to {text(name)}</ion-card-title>"
        f"<ion-card-subtitle>{count} session{'s' if count != 1 else ''} · "
        f"Subject: {text(subject)} · {text(special_email.label(language.code))} "
        f"({text(language.source)})</ion-card-subtitle></div>"
        '<div class="email-actions">'
        f'<ion-button fill="outline" data-copy-subject="{attr(subject)}">'
        "Copy subject</ion-button>"
        f'<ion-button data-copy="{template_id}" data-done="E-mail copied ✓" '
        'data-paste="a new Outlook message">'
        f"{_COPY_ICON}Copy e-mail</ion-button></div></div>"
        f'{warning}<ion-list lines="full">{items}</ion-list>'
        f'<template id="{template_id}">{body}</template></ion-card>'
    )


def _tools(countries: Sequence[str]) -> str:
    tabs = "".join(
        f'<ion-segment-button value="{attr(value)}"><ion-label>{text(label)}'
        "</ion-label></ion-segment-button>"
        for value, label in (("all", "All"), *((c, c) for c in countries))
    )
    return (
        '<div class="tools"><ion-searchbar placeholder="Search client, session or '
        'facilitator" debounce="150" show-clear-button="focus"></ion-searchbar>'
        f'<ion-segment value="all" scrollable="true">{tabs}</ion-segment></div>'
    )


_HELP = (
    '<ion-card class="help"><ion-accordion-group><ion-accordion value="help">'
    '<ion-item slot="header" lines="none"><ion-label>How to use</ion-label></ion-item>'
    '<div slot="content"><ul>'
    "<li><b>Copy for Slack</b> copies the client's sessions as cards (title, date, "
    "facilitator, links and QR), ready to paste into the client's canvas.</li>"
    "<li>Click a QR (or <b>Copy QR</b>) to copy a single QR, in case one needs "
    "replacing.</li>"
    "<li>Personalised e-mail notices are shown here and are <b>never</b> copied.</li>"
    "<li>If the viewer blocks copying (for example, a preview inside another app), "
    "the content opens already selected: copy it with Ctrl+C. For the best result, "
    "open this file in Chrome or Edge.</li>"
    "</ul></div></ion-accordion></ion-accordion-group></ion-card>"
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
        f'<section class="country" data-country="{attr(country)}">'
        f'<h2 class="section-title country-title">{text(country)}'
        f'<ion-badge class="count">{total}</ion-badge></h2>{blocks}</section>'
    )


def _client_card(
    client: str, records: Sequence[Row], special_cases: Mapping[str, Sequence[str]]
) -> str:
    template_id = f"payload-{build_client_table_id(client)}"
    ordered = _sorted(records)
    notices = "".join(
        '<div class="callout"><b>Send by e-mail separately:</b> '
        f"{text(record.get('Session', ''))} · "
        f"{text(', '.join(special_cases[record.get('Project ID', '')]))}</div>"
        for record in ordered
        if record.get("Project ID", "") in special_cases
    )
    items = "".join(
        _session_item(index, record, special_cases)
        for index, record in enumerate(ordered)
    )
    count = len(records)
    return (
        f'<ion-card class="client" data-client="{attr(client)}">'
        '<div class="card-head"><div>'
        f"<ion-card-title>{text(client)}</ion-card-title>"
        f"<ion-card-subtitle>{count} session{'s' if count != 1 else ''}"
        "</ion-card-subtitle></div>"
        f'<ion-button data-copy="{template_id}">{_COPY_ICON}Copy for Slack'
        "</ion-button></div>"
        f'{notices}<ion-list lines="full">{items}</ion-list>'
        '<ion-accordion-group class="slack-view"><ion-accordion value="slack">'
        '<ion-item slot="header" lines="none"><ion-label>See how it looks in Slack'
        '</ion-label></ion-item><div slot="content" class="slack-cards"></div>'
        "</ion-accordion></ion-accordion-group>"
        f'<template id="{template_id}">{payload_cards(records)}</template>'
        "</ion-card>"
    )


def _session_item(
    index: int, record: Row, special_cases: Mapping[str, Sequence[str]]
) -> str:
    link = safe_url(record.get("Link NPS Survey", ""))
    hosted = safe_url(record.get("QR-Code", ""))
    qr = (
        f'<div slot="start" class="qr" title="Click to copy this QR" '
        f'data-text="{attr(link)}" data-fallback="{attr(hosted)}" data-no-label></div>'
        if link
        else '<div slot="start" class="qr qr-empty">No QR yet</div>'
    )
    chips = [
        _chip_link(label, record.get(column, ""), "link")
        for label, column in (
            ("NPS", "Link NPS Survey"),
            ("Facilitators", "Link Insights Facilitators"),
        )
        if safe_url(record.get(column, ""))
    ] or ['<ion-chip class="pending">Surveys not created yet</ion-chip>']
    results = f"Results: {' '.join(record.get('Results', '').split()) or 'NO'}"
    chips.append(_chip_link(results, record.get("Link for Results", ""), "results"))
    copy_qr = (
        '<ion-button slot="end" fill="outline" size="small" data-copy-qr>Copy QR'
        "</ion-button>"
        if link
        else ""
    )
    special = " special" if record.get("Project ID", "") in special_cases else ""
    facilitator = text(record.get("Facilitator", "")) or "—"
    search = " ".join(
        record.get(k, "")
        for k in ("Client", "Session", "Facilitator", "Date", "Country")
    ).casefold()
    return (
        f'<ion-item lines="full" class="session{special}" data-index="{index}" '
        f'data-search="{attr(search)}">{qr}<ion-label class="ion-text-wrap">'
        f"<h3>{text(record.get('Session', ''))}</h3>"
        f"<p>{text(record.get('Date', ''))} · {facilitator}"
        f'</p><div class="chips">{"".join(chips)}</div></ion-label>{copy_qr}</ion-item>'
    )


def _chip_link(label: str, url: str, css: str) -> str:
    chip = f'<ion-chip class="{css}" outline="true">{text(label)}</ion-chip>'
    target = safe_url(url)
    if not target:
        return chip
    return f'<a href="{attr(target)}" target="_blank" rel="noopener">{chip}</a>'


_COPY_ICON = (
    '<svg slot="start" class="ico" viewBox="0 0 24 24" aria-hidden="true">'
    '<rect x="8" y="8" width="12" height="12" rx="2"/>'
    '<path d="M4 16V6a2 2 0 0 1 2-2h10"/></svg>'
)


def _sorted(records: Sequence[Row]) -> list[Row]:
    return sorted(records, key=lambda r: get_record_sort_key(dict(r)))


# --- static assets -----------------------------------------------------------------

_ASSETS = Path(__file__).resolve().parent / "assets"
_CSS = (_ASSETS / "slack_page.css").read_text(encoding="utf-8")
_JS = (_ASSETS / "slack_page.js").read_text(encoding="utf-8")
