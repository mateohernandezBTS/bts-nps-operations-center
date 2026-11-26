"""Markdown preview of a run report, in English, for the product owner.

Warnings and special-case notices are always written outside the data tables, so a
table can be copied without them (the NPS-003 lesson).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from nps_v2.selection import display_date

Row = Mapping[str, Any]


def render_preview(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    selection = report["selection"]
    lines = [
        f"# NPS Upcoming — {selection['label']}",
        "",
        f"Run `{report['run_id']}` · generated {report['generated_at']} · "
        "read-only (nothing was created or published).",
        "",
    ]
    lines += _filters(selection)
    if not report["watchlist_configured"]:
        lines += [
            "> **Note:** the special-case list is not installed; "
            "no facilitators were flagged for a personalised e-mail.",
            "",
        ]

    lines += [
        "## Summary",
        "",
        "| Group | Projects |",
        "|---|---|",
        f"| Surveys to create | {summary['pending']} "
        f"({summary['surveys_to_create']} surveys) |",
        f"| Already created | {summary['complete']} |",
        f"| Manual review | {summary['review'] + summary['worklist_review']} |",
        f"| Excluded by rules | {summary['excluded']} |",
        f"| Outside the report scope | {summary['out_of_scope']} |",
        f"| Filtered out by the search | {summary['filtered_out']} |",
        f"| Special cases | {summary['special_cases']} |",
        f"| Data-quality notes | {summary['quality_notes']} |",
        "",
    ]

    lines += _section(
        "Surveys to create",
        report["pending"],
        ["Country", "Date", "Client", "Session", "Facilitator", "Create", "Project"],
        lambda r: [
            r["country"],
            _date(r["start_date"]),
            r["client"],
            r["project"],
            _facilitators(r),
            "; ".join(
                f"{s['label']}: {s['survey_name']} ({s['language']})"
                for s in r["surveys_to_create"]
            ),
            _link("Salesforce", r["salesforce_url"]),
        ],
    )
    lines += _section(
        "Already created",
        report["complete"],
        [
            "Country",
            "Date",
            "Client",
            "Session",
            "Facilitator",
            "NPS",
            "QR",
            "Facilitators",
        ],
        lambda r: [
            r["country"],
            _date(r["start_date"]),
            r["client"],
            r["project"],
            _facilitators(r),
            _link("Link", r["nps_link"]),
            _link("QR", r["qr_code"]),
            _link("Link", r["facilitators_link"]),
        ],
    )
    lines += _special_cases(report["special_cases"])
    lines += _section(
        "Manual review",
        [*report["review"], *report["worklist_review"]],
        ["Country", "Date", "Client", "Session", "Reason", "Project"],
        lambda r: [
            r["country"],
            _date(r["start_date"]),
            r["client"],
            r["project"],
            "; ".join(r.get("reasons", [])) or r.get("issues", ""),
            _link("Salesforce", r["salesforce_url"]),
        ],
    )
    lines += _section(
        "Excluded by rules",
        report["excluded"],
        ["Country", "Date", "Client", "Session", "Reason"],
        lambda r: [
            r["country"],
            _date(r["start_date"]),
            r["client"],
            r["project"],
            "; ".join(r["reasons"]),
        ],
    )
    lines += _section(
        "Outside the report scope",
        report["out_of_scope"],
        ["Country", "Date", "Client", "Session", "Reason"],
        lambda r: [
            r["country"],
            _date(r["start_date"]),
            r["client"],
            r["project"],
            r["reason"],
        ],
    )
    lines += _section(
        "Data quality",
        report["quality"],
        ["Country", "Date", "Client", "Session", "Note"],
        lambda r: [
            r["country"],
            _date(r["start_date"]),
            r["client"],
            r["project"],
            r["note"],
        ],
    )
    return "\n".join(lines).rstrip() + "\n"


def _filters(selection: Mapping[str, Any]) -> list[str]:
    parts = []
    if selection["country_codes"]:
        parts.append("countries " + ", ".join(selection["country_codes"]))
    labels = {
        "project": "project",
        "client": "client",
        "facilitator": "facilitator",
        "sub_type": "sub-type",
    }
    for key, label in labels.items():
        if selection["filters"].get(key):
            parts.append(f'{label} contains "{selection["filters"][key]}"')
    return [f"Filters: {'; '.join(parts)}.", ""] if parts else []


def _section(
    title: str,
    rows: Sequence[Row],
    headers: Sequence[str],
    cells: Callable[[Row], Iterable[str]],
) -> list[str]:
    lines = [f"## {title} ({len(rows)})", ""]
    if not rows:
        return [*lines, "None.", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "---|" * len(headers))
    for row in rows:
        lines.append("| " + " | ".join(_cell(c) for c in cells(row)) + " |")
    return [*lines, ""]


def _special_cases(cases: Sequence[Row]) -> list[str]:
    lines = [f"## Special cases: personalised e-mail ({len(cases)})", ""]
    if not cases:
        return [*lines, "None.", ""]
    lines += [
        "Surveys are created as usual; these details are for the personalised e-mail.",
        "",
    ]
    pending = "survey not created yet"
    for number, case in enumerate(cases, start=1):
        lines += [
            f"{number}. **{_plain(case['client'])} — {_plain(case['project'])}**",
            f"   - Date: {_date(case['start_date'])} · Country: {case['country']}",
            f"   - Facilitator: {_plain(', '.join(case['matched_facilitators']))}",
            f"   - NPS link: {case['nps_link'] or pending}",
            f"   - QR: {case['qr_code'] or pending}",
            f"   - Facilitators link: {case['facilitators_link'] or pending}",
        ]
    return [*lines, ""]


def _facilitators(row: Row) -> str:
    suffix = " (personalised e-mail)" if row.get("special_case") else ""
    return f"{row['facilitators']}{suffix}"


def _date(iso: str) -> str:
    return display_date(date.fromisoformat(iso))


def _link(text: str, url: str) -> str:
    return f"[{text}]({url})" if url else "—"


def _cell(value: str) -> str:
    return (_plain(value) or "—").replace("|", "\\|")


def _plain(value: str) -> str:
    return " ".join(str(value).split())
