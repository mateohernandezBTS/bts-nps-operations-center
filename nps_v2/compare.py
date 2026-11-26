"""Parallel run: compare a V2 run with the desktop app's ``selam_worklist.csv``.

Both lists are compared by Project ID (15-character key). Every difference is
classified with what V2 knows about that project, so the product owner only has to
look into what is left unexplained.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nps_v2.domain import DomainError, SalesforceId

READY_SECTIONS = ("pending", "complete")
OTHER_SECTIONS = {
    "worklist_review": "V2: revisión manual del worklist",
    "review": "V2: revisión manual por reglas",
    "excluded": "V2: excluido por reglas",
    "out_of_scope": "V2: fuera del alcance del reporte",
}


class CompareError(ValueError):
    """The desktop file cannot be read."""


@dataclass(frozen=True, slots=True)
class Difference:
    project_id: str
    session: str
    client: str
    explanation: str


@dataclass(frozen=True, slots=True)
class Comparison:
    matching: int
    only_desktop: tuple[Difference, ...]
    only_v2: tuple[Difference, ...]

    @property
    def unexplained(self) -> int:
        return sum(
            1 for d in (*self.only_desktop, *self.only_v2) if d.explanation == ""
        )

    def to_dict(self) -> dict[str, Any]:
        def rows(items: Sequence[Difference]) -> list[dict[str, str]]:
            return [
                {
                    "project_id": d.project_id,
                    "session": d.session,
                    "client": d.client,
                    "explanation": d.explanation,
                }
                for d in items
            ]

        return {
            "matching": self.matching,
            "only_desktop": rows(self.only_desktop),
            "only_v2": rows(self.only_v2),
        }


def read_desktop_ready(path: Path) -> dict[str, dict[str, str]]:
    """READY rows of the desktop ``selam_worklist.csv`` keyed by 15-char Project ID."""
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
    except OSError as error:
        raise CompareError(f"Cannot read {path}: {error}") from error
    if rows and "Project ID" not in rows[0]:
        raise CompareError(f"{path.name} has no 'Project ID' column")
    ready: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("Output Status", "READY").strip().upper() != "READY":
            continue
        key = _key(row.get("Project ID", ""))
        if key is None:
            raise CompareError(
                f"Invalid Project ID in desktop file: {row.get('Project ID')!r}"
            )
        ready[key] = row
    return ready


def compare(
    report: Mapping[str, Any], desktop_ready: Mapping[str, Mapping[str, str]]
) -> Comparison:
    v2_ready = {
        _report_key(row): row for section in READY_SECTIONS for row in report[section]
    }
    elsewhere = {
        _report_key(row): (label, row)
        for section, label in OTHER_SECTIONS.items()
        for row in report[section]
    }

    only_desktop = []
    for key, row in sorted(desktop_ready.items()):
        if key in v2_ready:
            continue
        if key in elsewhere:
            label, v2_row = elsewhere[key]
            reasons = v2_row.get("reasons") or [
                v2_row.get("reason") or v2_row.get("issues", "")
            ]
            explanation = f"{label}: {'; '.join(r for r in reasons if r)}"
        else:
            explanation = (
                "No está en Salesforce para esta selección: puede haberse borrado o "
                "cambiado de fecha o país después del reporte"
            )
        only_desktop.append(
            Difference(key, row.get("Session", ""), row.get("Client", ""), explanation)
        )

    only_v2 = [
        Difference(
            key,
            row["project"],
            row["client"],
            "",  # V2 cannot know why the report did not have it: check in Salesforce
        )
        for key, row in sorted(v2_ready.items())
        if key not in desktop_ready
    ]
    matching = len(set(v2_ready) & set(desktop_ready))
    return Comparison(matching, tuple(only_desktop), tuple(only_v2))


def render_comparison(comparison: Comparison, *, run_id: str, desktop_name: str) -> str:
    lines = [
        f"# Corrida en paralelo — {run_id}",
        "",
        f"Comparación de sesiones listas (READY) de V2 contra `{desktop_name}`.",
        "",
        "| Resultado | Sesiones |",
        "|---|---|",
        f"| Coinciden | {comparison.matching} |",
        f"| Solo en escritorio | {len(comparison.only_desktop)} |",
        f"| Solo en V2 | {len(comparison.only_v2)} |",
        "",
    ]
    lines += _table("Solo en escritorio", comparison.only_desktop)
    lines += _table("Solo en V2", comparison.only_v2)
    if comparison.only_v2:
        lines += [
            "Para cada sesión solo en V2, revisá en Salesforce `CreatedDate` y "
            "`LastModifiedDate`: si son posteriores al envío del reporte, la "
            "diferencia es temporal. Anotá la explicación en el registro de la "
            "corrida.",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def _table(title: str, rows: Sequence[Difference]) -> list[str]:
    lines = [f"## {title} ({len(rows)})", ""]
    if not rows:
        return [*lines, "Ninguna.", ""]
    lines += ["| Project ID | Cliente | Sesión | Explicación |", "|---|---|---|---|"]
    for row in rows:
        cells = (
            row.project_id,
            row.client,
            row.session,
            row.explanation or "A revisar",
        )
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    return [*lines, ""]


def _report_key(row: Mapping[str, Any]) -> str:
    key = _key(str(row.get("project_id", "")))
    if key is None:
        raise CompareError(f"Invalid project id in report: {row.get('project_id')!r}")
    return key


def _key(value: str) -> str | None:
    try:
        return SalesforceId(value.strip()).key
    except DomainError:
        return None
