"""Slack outputs of a run: the desktop-compatible CSV and the V2 Slack page.

``selam_worklist.csv`` keeps the desktop contract (pinned by a test against
``engine.selam_output.CSV_COLUMNS``) so runs can be compared with the desktop app.
``selam_slack_canvas.html`` is the V2 page (``nps_v2.outputs.slack_page``): BTS-styled
preview, Slack-safe copy payload identical to the desktop table, QR as an image.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

from nps_v2.adapters import legacy_date
from nps_v2.domain import SalesforceId
from nps_v2.outputs.slack_page import PageContext, render_page
from nps_v2.outputs.special_email import EmailLanguage
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
PAGE_FILE = "selam_slack_canvas.html"


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
    page_context: PageContext,
    country_order: Sequence[str],
    special_cases: Mapping[str, Sequence[str]],
    email_languages: Mapping[str, EmailLanguage] | None = None,
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
    page = directory / PAGE_FILE
    page.write_text(
        render_page(
            rows,
            context=page_context,
            country_order=country_order,
            special_cases=special_cases,
            email_languages=email_languages,
        ),
        encoding="utf-8",
    )
    return page
