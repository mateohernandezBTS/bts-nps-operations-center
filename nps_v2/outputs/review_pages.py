"""Read-only review views on the shared UI kit (D-V2-11): the Upcoming preview and the
parallel-run comparison.

They show the same content as ``preview.md`` and ``compare.md`` (which stay, as plain
text), with search, country tabs and collapsible long lists. Nothing on them writes
anywhere.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date
from typing import Any

from nps_v2.outputs.ui_kit import (
    Tile,
    attr,
    brandbar,
    kpi_tiles,
    render_document,
    safe_url,
    text,
)
from nps_v2.selection import display_date

Row = Mapping[str, Any]
Cells = Callable[[Row], tuple[str, str]]  # (detail HTML, end chips HTML)


# --- Upcoming preview -----------------------------------------------------------------


def render_preview_page(
    report: Mapping[str, Any], *, country_names: Mapping[str, str]
) -> str:
    """``country_names``: country code → name, in display order."""
    summary = report["summary"]
    selection = report["selection"]
    tiles = kpi_tiles(
        (
            Tile("Sessions to create", summary["pending"]),
            Tile("Surveys to create", summary["surveys_to_create"]),
            Tile("Already created", summary["complete"]),
            Tile(
                "Manual review",
                summary["review"] + summary["worklist_review"],
                warn=True,
            ),
            Tile("Excluded", summary["excluded"]),
            Tile("Outside the scope", summary["out_of_scope"]),
            Tile("Special cases", summary["special_cases"], warn=True),
            Tile("Data-quality notes", summary["quality_notes"], warn=True),
        )
    )
    notes = (
        '<div class="banner info">Read-only: nothing was created or published.</div>'
    )
    filters = _filters(selection)
    if filters:
        notes += f'<p class="meta">Filters: {text(filters)}.</p>'
    if not report["watchlist_configured"]:
        notes += (
            '<div class="callout"><b>Note:</b> the special-case list is not installed; '
            "no facilitators were flagged for a personalised e-mail.</div>"
        )
    review_rows = [*report["review"], *report["worklist_review"]]
    body = (
        notes
        + tiles
        + _group("Surveys to create", report["pending"], country_names, _pending)
        + _special_cases(report["special_cases"], country_names)
        + _group("Manual review", review_rows, country_names, _review)
        + _group("Already created", report["complete"], country_names, _complete)
        + _group(
            "Data quality",
            report["quality"],
            country_names,
            _note("note"),
            collapsed=True,
        )
        + _group(
            "Excluded by rules",
            report["excluded"],
            country_names,
            _note("reasons"),
            collapsed=True,
        )
        + _group(
            "Outside the report scope",
            report["out_of_scope"],
            country_names,
            _note("reason"),
            collapsed=True,
        )
        + '<p id="no-results" class="empty" hidden>No sessions match the search.</p>'
    )
    countries = _present_countries(report, country_names)
    header = brandbar(
        "NPS · Upcoming — preview",
        f"{selection['label']} · run {report['run_id']} · generated "
        f"{report['generated_at']}",
    ) + _tools(countries)
    return render_document(
        title=f"NPS Upcoming · {report['run_id']}",
        header=header,
        body=body,
        css=_CSS,
        js=_FILTER_JS,
    )


def rest_of_week(report: Mapping[str, Any], *, country_names: Mapping[str, str]) -> str:
    """Everything of the run except the sessions to create, for the plan page: special
    cases, manual review and data quality open; already created, excluded and outside
    the scope collapsed. Read-only content, same wording as the preview."""
    summary = report["summary"]
    tiles = kpi_tiles(
        (
            Tile("Already created", summary["complete"]),
            Tile(
                "Manual review",
                summary["review"] + summary["worklist_review"],
                warn=True,
            ),
            Tile("Excluded", summary["excluded"]),
            Tile("Outside the scope", summary["out_of_scope"]),
            Tile("Data-quality notes", summary["quality_notes"], warn=True),
        )
    )
    note = (
        ""
        if report["watchlist_configured"]
        else '<div class="callout"><b>Note:</b> the special-case list is not '
        "installed; no facilitators were flagged for a personalised e-mail.</div>"
    )
    review_rows = [*report["review"], *report["worklist_review"]]
    return (
        '<h2 class="part-title">Rest of the week</h2>'
        + note
        + tiles
        + _special_cases(report["special_cases"], country_names)
        + _group("Manual review", review_rows, country_names, _review)
        + _group("Data quality", report["quality"], country_names, _note("note"))
        + _group(
            "Already created",
            report["complete"],
            country_names,
            _complete,
            collapsed=True,
        )
        + _group(
            "Excluded by rules",
            report["excluded"],
            country_names,
            _note("reasons"),
            collapsed=True,
        )
        + _group(
            "Outside the report scope",
            report["out_of_scope"],
            country_names,
            _note("reason"),
            collapsed=True,
        )
    )


def _pending(row: Row) -> tuple[str, str]:
    chips = "".join(
        f'<ion-chip class="pending" outline="true">{text(s["label"])} · '
        f"{text(s['language'])}</ion-chip>"
        for s in row["surveys_to_create"]
    )
    detail = "To create: " + "; ".join(
        f"{s['label']} ({s['survey_name']})" for s in row["surveys_to_create"]
    )
    return f"<p>{text(detail)}</p>" + _warnings(row), chips + _salesforce(row)


def _complete(row: Row) -> tuple[str, str]:
    links = "".join(
        _link_chip(label, row.get(key, ""))
        for label, key in (
            ("NPS", "nps_link"),
            ("Facilitators", "facilitators_link"),
        )
    )
    qr = safe_url(str(row.get("qr_code", "")))
    qr_chip = _link_chip("QR", qr) if qr else ""
    return _warnings(row), links + qr_chip


def _review(row: Row) -> tuple[str, str]:
    reasons = "; ".join(row.get("reasons", [])) or str(row.get("issues", ""))
    return f'<p class="reason">{text(reasons)}</p>', _salesforce(row)


def _note(key: str) -> Cells:
    def cells(row: Row) -> tuple[str, str]:
        value = row.get(key, "")
        reason = "; ".join(value) if isinstance(value, list) else str(value)
        return f'<p class="reason">{text(reason)}</p>', _salesforce(row)

    return cells


def _special_cases(cases: Sequence[Row], country_names: Mapping[str, str]) -> str:
    if not cases:
        return ""
    pending = "survey not created yet"
    cards = "".join(
        f'<div class="callout case"><b>{text(case["client"])} — '
        f"{text(case['project'])}</b><br>"
        f"{text(_country(case, country_names))} · {text(_date(case['start_date']))} · "
        f"facilitator {text(', '.join(case['matched_facilitators']))}<br>"
        f"NPS: {_inline_link(case.get('nps_link', '')) or pending} · "
        f"QR: {_inline_link(case.get('qr_code', '')) or pending} · "
        f"Facilitators: {_inline_link(case.get('facilitators_link', '')) or pending}"
        "</div>"
        for case in cases
    )
    return (
        '<section class="group"><h2 class="section-title">Special cases: personalised '
        f'e-mail<ion-badge class="count">{len(cases)}</ion-badge></h2>'
        '<p class="meta">Surveys are created as usual; these details are for the '
        f"personalised e-mail.</p>{cards}</section>"
    )


# --- parallel-run comparison -----------------------------------------------------


def render_compare_page(
    comparison: Any, *, run_id: str, desktop_name: str, generated_at: str
) -> str:
    """``comparison``: ``nps_v2.compare.Comparison``."""
    tiles = kpi_tiles(
        (
            Tile("Matching", comparison.matching),
            Tile("Only on desktop", len(comparison.only_desktop), warn=True),
            Tile("Only in V2", len(comparison.only_v2), warn=True),
            Tile("To check", comparison.unexplained, warn=True),
        )
    )
    verdict = (
        '<div class="banner ok">Both lists match: nothing to check.</div>'
        if not comparison.only_desktop and not comparison.only_v2
        else '<div class="banner info">Differences are listed below with what V2 '
        "knows about them. Only the ones marked <b>To check</b> need a look in "
        "Salesforce.</div>"
    )
    hint = (
        '<p class="meta">For each session only in V2, check <code>CreatedDate</code> '
        "and <code>LastModifiedDate</code> in Salesforce: if they are later than the "
        "report e-mail, the difference is timing only.</p>"
        if comparison.only_v2
        else ""
    )
    body = (
        verdict
        + tiles
        + _difference_list("Only on desktop", comparison.only_desktop)
        + _difference_list("Only in V2", comparison.only_v2)
        + hint
    )
    return render_document(
        title=f"Parallel run · {run_id}",
        header=brandbar(
            "NPS · Parallel run — comparison",
            f"V2 run {run_id} vs {desktop_name} · generated {generated_at}",
        ),
        body=body,
        css=_CSS,
    )


def _difference_list(title: str, rows: Sequence[Any]) -> str:
    if not rows:
        items = '<p class="empty">None.</p>'
    else:
        items = (
            '<ion-card><ion-list lines="full">'
            + "".join(
                '<ion-item lines="full" class="row"><ion-label class="ion-text-wrap">'
                f"<h3>{text(row.session) or '—'}</h3>"
                f"<p>{text(row.client) or '—'} · {text(row.project_id)}</p>"
                f'<p class="reason">{text(row.explanation) or _UNKNOWN}</p>'
                "</ion-label>"
                + (
                    '<ion-chip class="warn" outline="true">To check</ion-chip>'
                    if not row.explanation
                    else '<ion-chip class="neutral" outline="true">Explained</ion-chip>'
                )
                + "</ion-item>"
                for row in rows
            )
            + "</ion-list></ion-card>"
        )
    return (
        f'<section class="group"><h2 class="section-title">{text(title)}'
        f'<ion-badge class="count">{len(rows)}</ion-badge></h2>{items}</section>'
    )


# --- building blocks --------------------------------------------------------------


def _group(
    title: str,
    rows: Sequence[Row],
    country_names: Mapping[str, str],
    cells: Cells,
    *,
    collapsed: bool = False,
) -> str:
    heading = (
        f'<h2 class="section-title">{text(title)}'
        f'<ion-badge class="count">{len(rows)}</ion-badge></h2>'
    )
    if not rows:
        return f'<section class="group">{heading}<p class="meta">None.</p></section>'
    items = "".join(
        _item(row, country_names, cells) for row in _sorted(rows, country_names)
    )
    listing = f'<ion-list lines="full">{items}</ion-list>'
    if collapsed:
        listing = (
            '<ion-accordion-group><ion-accordion value="list">'
            '<ion-item slot="header" lines="none"><ion-label>'
            f"Show the {len(rows)} session{'s' if len(rows) != 1 else ''}"
            f'</ion-label></ion-item><div slot="content">{listing}</div>'
            "</ion-accordion></ion-accordion-group>"
        )
    return f'<section class="group">{heading}<ion-card>{listing}</ion-card></section>'


def _item(row: Row, country_names: Mapping[str, str], cells: Cells) -> str:
    detail, end = cells(row)
    country = _country(row, country_names)
    facilitators = " ".join(str(row.get("facilitators", "")).split())
    meta = " · ".join(
        part
        for part in (
            country,
            _date(str(row.get("start_date", ""))),
            str(row.get("client", "")),
            facilitators,
        )
        if part.strip()
    )
    special = (
        '<ion-chip class="warn" outline="true">Personalised e-mail</ion-chip>'
        if row.get("special_case")
        else ""
    )
    search = " ".join(
        str(row.get(key, "")) for key in ("client", "project", "facilitators")
    ).casefold()
    return (
        f'<ion-item lines="full" class="row" data-country="{attr(country)}" '
        f'data-search="{attr(search)}"><ion-label class="ion-text-wrap">'
        f"<h3>{text(row.get('project', '')) or '—'}</h3><p>{text(meta)}</p>{detail}"
        f'<div class="chips">{special}{end}</div></ion-label></ion-item>'
    )


def _sorted(rows: Sequence[Row], country_names: Mapping[str, str]) -> list[Row]:
    order = {code: index for index, code in enumerate(country_names)}
    return sorted(
        rows,
        key=lambda r: (
            str(r.get("start_date", "")),
            order.get(str(r.get("country", "")), len(order)),
            str(r.get("client", "")).casefold(),
            str(r.get("project", "")).casefold(),
        ),
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


def _present_countries(
    report: Mapping[str, Any], country_names: Mapping[str, str]
) -> list[str]:
    sections = (
        "pending",
        "complete",
        "review",
        "worklist_review",
        "excluded",
        "out_of_scope",
    )
    codes = {str(row.get("country", "")) for s in sections for row in report[s]}
    known = [name for code, name in country_names.items() if code in codes]
    others = sorted(c for c in codes if c and c not in country_names)
    return known + others


def _country(row: Row, country_names: Mapping[str, str]) -> str:
    code = str(row.get("country", ""))
    return country_names.get(code, code)


def _filters(selection: Mapping[str, Any]) -> str:
    parts = []
    if selection["country_codes"]:
        parts.append("countries " + ", ".join(selection["country_codes"]))
    for key, label in (
        ("project", "project"),
        ("client", "client"),
        ("facilitator", "facilitator"),
        ("sub_type", "sub-type"),
    ):
        if selection["filters"].get(key):
            parts.append(f'{label} contains "{selection["filters"][key]}"')
    return "; ".join(parts)


def _warnings(row: Row) -> str:
    warnings = row.get("warnings") or []
    return "".join(f'<p class="reason">{text(w)}</p>' for w in warnings)


def _salesforce(row: Row) -> str:
    return _link_chip("Salesforce", str(row.get("salesforce_url", "")))


def _link_chip(label: str, url: str) -> str:
    safe = safe_url(str(url))
    if not safe:
        return ""
    return (
        f'<a href="{attr(safe)}" target="_blank" rel="noopener">'
        f'<ion-chip class="link" outline="true">{text(label)}</ion-chip></a>'
    )


def _inline_link(url: str) -> str:
    safe = safe_url(str(url))
    return (
        f'<a href="{attr(safe)}" target="_blank" rel="noopener">open</a>'
        if safe
        else ""
    )


def _date(iso: str) -> str:
    try:
        return display_date(date.fromisoformat(iso))
    except ValueError:
        return iso


_UNKNOWN = "V2 cannot tell why: check it in Salesforce."

_FILTER_JS = """
(function(){
  var query='',country='all';
  function apply(){
    var any=false;
    document.querySelectorAll('section.group').forEach(function(section){
      var items=section.querySelectorAll('ion-item.row');
      if(!items.length){section.hidden=!!(query||country!=='all');return;}
      var shown=0;
      items.forEach(function(item){
        var ok=(country==='all'||item.getAttribute('data-country')===country)
          &&(!query||item.getAttribute('data-search').indexOf(query)>=0);
        item.hidden=!ok;if(ok){shown++;}
      });
      section.hidden=shown===0;any=any||shown>0;
    });
    var none=document.getElementById('no-results');if(none){none.hidden=any;}
  }
  document.addEventListener('ionInput',function(ev){
    if(ev.target.tagName==='ION-SEARCHBAR'){
      query=(ev.detail.value||'').trim().toLowerCase();apply();}
  });
  document.addEventListener('ionChange',function(ev){
    if(ev.target.tagName==='ION-SEGMENT'){country=ev.detail.value||'all';apply();}
  });
})();
"""

_CSS = """
section.group{margin:0 0 6px}
ion-item.row{--padding-start:18px;--inner-padding-end:14px;--min-height:60px}
ion-item.row h3{font-size:14.5px;font-weight:650;margin:0 0 2px}
ion-item.row p{font-size:12.5px;color:var(--grey-text);margin:0}
ion-item.row p.reason{color:#5e3a12;margin-top:2px}
.chips{display:flex;flex-wrap:wrap;gap:2px;margin:6px 0 0 -4px}
.chips a{text-decoration:none;color:inherit}
ion-chip.pending,ion-chip.link{--color:#CA1C68;color:#CA1C68;
--background:rgba(202,28,104,.06);border-color:rgba(202,28,104,.35)}
ion-chip.neutral{--color:#5e6367;color:#5e6367;--background:#F7F8F9;border-color:#D5D9DD}
ion-chip.warn{--color:#9a5b12;color:#9a5b12;--background:#FFF6EA;border-color:#F2D2A6}
.banner{padding:12px 16px;border-radius:12px;margin:0 0 12px;font-size:13.5px}
.banner.ok{background:#EDF7F6;color:#1D7279;border:1px solid #BFE0DC}
.banner.info{background:#F7F8F9;color:#3d4246;border:1px solid #D5D9DD}
.meta{margin:0 0 12px;color:var(--grey-text);font-size:13px}
.callout.case{line-height:1.6}
.callout a{color:#CA1C68}
.part-title{font-size:22px;font-weight:800;margin:34px 0 10px;padding-top:18px;
border-top:1px solid var(--grey-light)}
"""
REVIEW_CSS = _CSS
