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
    "worklist_review": "V2: worklist manual review",
    "review": "V2: manual review by rules",
    "excluded": "V2: excluded by rules",
    "out_of_scope": "V2: outside the report scope",
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
                "Not in Salesforce for this selection: it may have been deleted, or "
                "its date or country changed, after the report was sent"
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
        f"# Parallel run — {run_id}",
        "",
        f"Ready (READY) sessions of V2 compared with `{desktop_name}`.",
        "",
        "| Result | Sessions |",
        "|---|---|",
        f"| Matching | {comparison.matching} |",
        f"| Only on desktop | {len(comparison.only_desktop)} |",
        f"| Only in V2 | {len(comparison.only_v2)} |",
        "",
    ]
    lines += _table("Only on desktop", comparison.only_desktop)
    lines += _table("Only in V2", comparison.only_v2)
    if comparison.only_v2:
        lines += [
            "For each session only in V2, check `CreatedDate` and "
            "`LastModifiedDate` in Salesforce: if they are later than the report "
            "e-mail, the difference is timing only. Record the explanation in the "
            "run log.",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def _table(title: str, rows: Sequence[Difference]) -> list[str]:
    lines = [f"## {title} ({len(rows)})", ""]
    if not rows:
        return [*lines, "None.", ""]
    lines += ["| Project ID | Client | Session | Explanation |", "|---|---|---|---|"]
    for row in rows:
        cells = (
            row.project_id,
            row.client,
            row.session,
            row.explanation or "To check",
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
