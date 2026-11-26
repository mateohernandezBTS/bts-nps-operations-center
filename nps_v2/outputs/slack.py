"""Slack table through the certified renderer, with QR and links filled in.

The renderer (``engine/slack_canvas_renderer.py``) reads ``selam_worklist.csv`` and an
optional ``selam_weekly_summary.json`` from a directory and writes
``selam_slack_canvas.html``, the page the product owner copies into the canvas today.
V2 writes the same CSV contract (pinned by a test against
``engine.selam_output.CSV_COLUMNS``) so the output looks exactly like the desktop one.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

from engine.slack_canvas_renderer import generate_slack_canvas_html
from nps_v2.adapters import legacy_date
from nps_v2.domain import SalesforceId
from nps_v2.pipeline import WorklistEntry
from nps_v2.registry import CountryRegistry
from nps_v2.surveys.state import ProjectSurveys

SLACK_CSV_COLUMNS: tuple[str, ...] = (
    "Client",
    "Country",
    "Session",
    "Date",
    "Facilitator",
    "QR-Code",
    "Link NPS Survey",
    "Link Insights Facilitators",
    "Results",
    "Link for Results",
    "Project ID",
    "Project URL",
    "Output Status",
    "Output Issues",
    "Source ID",
    "Source Execution ID",
    "Weekly Run ID",
    "Region",
)
SOURCE_ID = "salesforce_v2"
WORKLIST_FILE = "selam_worklist.csv"
SUMMARY_FILE = "selam_weekly_summary.json"


def slack_rows(
    entries: Sequence[WorklistEntry],
    surveys: Mapping[SalesforceId, ProjectSurveys],
    registry: CountryRegistry,
    run_id: str,
) -> list[dict[str, str]]:
    rows = []
    for entry in entries:
        row = {column: entry.row.get(column, "") for column in SLACK_CSV_COLUMNS}
        row.update(surveys[entry.project.project_id].slack_columns())
        row.update(
            {
                "Country": registry.by_code(entry.country_code).name,
                "Source ID": SOURCE_ID,
                "Source Execution ID": run_id,
                "Weekly Run ID": run_id,
                "Region": "SELAM",
            }
        )
        rows.append(row)
    return rows


def write_slack_table(
    directory: Path,
    rows: Sequence[Mapping[str, str]],
    *,
    run_id: str,
    date_from: date,
    date_to: date,
    review_count: int,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / WORKLIST_FILE).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(SLACK_CSV_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "weekly_run_id": run_id,
        "window_start": legacy_date(date_from),
        "window_end": legacy_date(date_to),
        "review_records": review_count,
    }
    (directory / SUMMARY_FILE).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return Path(generate_slack_canvas_html(directory))
