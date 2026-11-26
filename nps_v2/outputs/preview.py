"""Markdown preview of a run report, in Spanish, for the product owner.

Warnings and special-case notices are always written outside the data tables, so a
table can be copied without them (the NPS-003 lesson).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date
from typing import Any

Row = Mapping[str, Any]


def render_preview(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    selection = report["selection"]
    lines = [
        f"# NPS Upcoming — {selection['label']}",
        "",
        f"Corrida `{report['run_id']}` · generada {report['generated_at']} · "
        "solo lectura (no se creó ni publicó nada).",
        "",
    ]
    lines += _filters(selection)
    if not report["watchlist_configured"]:
        lines += [
            "> **Atención:** la lista de casos especiales no está configurada; "
            "no se marcaron facilitadores para mail personalizado.",
            "",
        ]

    lines += [
        "## Resumen",
        "",
        "| Grupo | Proyectos |",
        "|---|---|",
        f"| Encuestas a crear | {summary['pending']} "
        f"({summary['surveys_to_create']} encuestas) |",
        f"| Ya creadas | {summary['complete']} |",
        f"| Revisión manual | {summary['review'] + summary['worklist_review']} |",
        f"| Excluidos por reglas | {summary['excluded']} |",
        f"| Fuera del alcance del reporte | {summary['out_of_scope']} |",
        f"| Filtrados por la búsqueda | {summary['filtered_out']} |",
        f"| Casos especiales | {summary['special_cases']} |",
        f"| Notas de calidad de datos | {summary['quality_notes']} |",
        "",
    ]

    lines += _section(
        "Encuestas a crear",
        report["pending"],
        ["País", "Fecha", "Cliente", "Sesión", "Facilitador", "Crear", "Proyecto"],
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
        "Ya creadas",
        report["complete"],
        [
            "País",
            "Fecha",
            "Cliente",
            "Sesión",
            "Facilitador",
            "NPS",
            "QR",
            "Facilitadores",
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
        "Revisión manual",
        [*report["review"], *report["worklist_review"]],
        ["País", "Fecha", "Cliente", "Sesión", "Motivo", "Proyecto"],
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
        "Excluidos por reglas",
        report["excluded"],
        ["País", "Fecha", "Cliente", "Sesión", "Motivo"],
        lambda r: [
            r["country"],
            _date(r["start_date"]),
            r["client"],
            r["project"],
            "; ".join(r["reasons"]),
        ],
    )
    lines += _section(
        "Fuera del alcance del reporte",
        report["out_of_scope"],
        ["País", "Fecha", "Cliente", "Sesión", "Motivo"],
        lambda r: [
            r["country"],
            _date(r["start_date"]),
            r["client"],
            r["project"],
            r["reason"],
        ],
    )
    lines += _section(
        "Calidad de datos",
        report["quality"],
        ["País", "Fecha", "Cliente", "Sesión", "Nota"],
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
        parts.append("países " + ", ".join(selection["country_codes"]))
    labels = {
        "project": "proyecto",
        "client": "cliente",
        "facilitator": "facilitador",
        "sub_type": "sub-type",
    }
    for key, label in labels.items():
        if selection["filters"].get(key):
            parts.append(f"{label} contiene «{selection['filters'][key]}»")
    return [f"Filtros: {'; '.join(parts)}.", ""] if parts else []


def _section(
    title: str,
    rows: Sequence[Row],
    headers: Sequence[str],
    cells: Callable[[Row], Iterable[str]],
) -> list[str]:
    lines = [f"## {title} ({len(rows)})", ""]
    if not rows:
        return [*lines, "Ninguno.", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "---|" * len(headers))
    for row in rows:
        lines.append("| " + " | ".join(_cell(c) for c in cells(row)) + " |")
    return [*lines, ""]


def _special_cases(cases: Sequence[Row]) -> list[str]:
    lines = [f"## Casos especiales: mail personalizado ({len(cases)})", ""]
    if not cases:
        return [*lines, "Ninguno.", ""]
    lines += [
        "Las encuestas se crean igual; estos datos son para el mail personalizado.",
        "",
    ]
    pending = "pendiente de crear"
    for number, case in enumerate(cases, start=1):
        lines += [
            f"{number}. **{_plain(case['client'])} — {_plain(case['project'])}**",
            f"   - Fecha: {_date(case['start_date'])} · País: {case['country']}",
            f"   - Facilitador: {_plain(', '.join(case['matched_facilitators']))}",
            f"   - Link NPS: {case['nps_link'] or pending}",
            f"   - QR: {case['qr_code'] or pending}",
            f"   - Link facilitadores: {case['facilitators_link'] or pending}",
        ]
    return [*lines, ""]


def _facilitators(row: Row) -> str:
    suffix = " (mail personalizado)" if row.get("special_case") else ""
    return f"{row['facilitators']}{suffix}"


def _date(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def _link(text: str, url: str) -> str:
    return f"[{text}]({url})" if url else "—"


def _cell(value: str) -> str:
    return (_plain(value) or "—").replace("|", "\\|")


def _plain(value: str) -> str:
    return " ".join(str(value).split())
