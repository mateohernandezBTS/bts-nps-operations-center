from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from engine.selam_aggregator import (
    load_json_file,
    save_json_file,
)


class SelamOutputError(Exception):
    """Raised when SELAM outputs cannot be generated."""


OPERATIONAL_COLUMNS = [
    "Session",
    "Date",
    "Facilitator",
    "QR-Code",
    "Link NPS Survey",
    "Link Insights Facilitators",
    "Results",
    "Link for Results",
]


CSV_COLUMNS = [
    "Client",
    "Country",
    *OPERATIONAL_COLUMNS,
    "Project ID",
    "Project URL",
    "Output Status",
    "Output Issues",
    "Source ID",
    "Source Execution ID",
    "Weekly Run ID",
    "Region",
]

MANUAL_REVIEW_COLUMNS = [
    "Country",
    "client_name",
    "project_name",
    "start_date",
    "status",
    "ignore_reporting",
    "decision",
    "decision_code",
    "decision_reason",
    "matched_field",
    "matched_pattern",
    "Suggested Action",
    "project_url",
    "Source ID",
    "Source Execution ID",
    "Weekly Run ID",
    "Region",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value).split()
    ).strip()

def parse_salesforce_date(
    value: Any,
) -> datetime | None:
    text = clean_text(value)

    if not text:
        return None

    try:
        return datetime.strptime(
            text,
            "%m/%d/%Y",
        )
    except ValueError:
        return None


def filter_manual_reviews_by_window(
    records: list[dict[str, Any]],
    *,
    window_start: str,
    window_end: str,
) -> list[dict[str, Any]]:
    start = parse_salesforce_date(
        window_start
    )

    end = parse_salesforce_date(
        window_end
    )

    if start is None or end is None:
        raise SelamOutputError(
            "Invalid weekly window for manual reviews: "
            f"{window_start} to {window_end}"
        )

    filtered_records = []

    for record in records:
        record_date = parse_salesforce_date(
            record.get(
                "start_date",
                "",
            )
        )

        if record_date is None:
            continue

        if start <= record_date <= end:
            enriched_record = dict(
                record
            )

            enriched_record[
                "Suggested Action"
            ] = (
                "Confirmar si representa una sesión real "
                "antes de crear el NPS."
            )

            filtered_records.append(
                enriched_record
            )

    return filtered_records


def escape_markdown_cell(value: Any) -> str:
    """
    Prepare a value for a Markdown table cell.
    """
    text = clean_text(value)

    return (
        text
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def markdown_link(
    label: str,
    url: Any,
) -> str:
    """
    Return a Markdown link when a URL is available.
    """
    clean_url = clean_text(url)

    if not clean_url:
        return ""

    return f"[{label}]({clean_url})"


def operational_value(
    record: dict[str, Any],
    column: str,
) -> str:
    """
    Prepare one operational value for Markdown.
    """
    if column == "Link for Results":
        return markdown_link(
            "Home",
            record.get(column),
        )

    if column == "Link NPS Survey":
        return markdown_link(
            "NPS",
            record.get(column),
        )

    if column == "Link Insights Facilitators":
        return markdown_link(
            "Facilitators",
            record.get(column),
        )

    return escape_markdown_cell(
        record.get(column, "")
    )


def group_records_by_client(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Group records while preserving their existing order.
    """
    grouped: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for record in records:
        client = clean_text(
            record.get("Client")
        ) or "[CLIENT NOT PROVIDED]"

        grouped[client].append(record)

    return dict(grouped)


def build_markdown_table(
    records: list[dict[str, Any]],
) -> str:
    """
    Build one Markdown table using operational columns.
    """
    header = (
        "| "
        + " | ".join(OPERATIONAL_COLUMNS)
        + " |"
    )

    separator = (
        "| "
        + " | ".join(
            "---"
            for _ in OPERATIONAL_COLUMNS
        )
        + " |"
    )

    rows = [
        header,
        separator,
    ]

    for record in records:
        values = [
            operational_value(
                record,
                column,
            )
            for column in OPERATIONAL_COLUMNS
        ]

        rows.append(
            "| "
            + " | ".join(values)
            + " |"
        )

    return "\n".join(rows)


def build_selam_markdown(
    records: list[dict[str, Any]],
    *,
    weekly_run_id: str,
    window_start: str,
    window_end: str,
) -> str:
    """
    Build a client-grouped SELAM Markdown document.
    """
    grouped_records = group_records_by_client(
        records
    )

    lines = [
        "# NPS Weekly Worklist — SELAM",
        "",
        f"**Weekly Run:** {weekly_run_id}",
        f"**Window:** {window_start} to {window_end}",
        f"**Total records:** {len(records)}",
        f"**Clients:** {len(grouped_records)}",
        "",
    ]

    for client, client_records in grouped_records.items():
        countries = sorted(
            {
                clean_text(
                    record.get("Country")
                )
                for record in client_records
                if clean_text(
                    record.get("Country")
                )
            }
        )

        lines.extend(
            [
                f"## {client}",
                "",
                (
                    "**Country:** "
                    + ", ".join(countries)
                    if countries
                    else "**Country:** Not available"
                ),
                "",
                build_markdown_table(
                    client_records
                ),
                "",
            ]
        )

    if not records:
        lines.extend(
            [
                "No NPS records were found inside "
                "the configured weekly window.",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def save_csv_file(
    records: list[dict[str, Any]],
    file_path: Path | str,
) -> Path:
    """
    Save the consolidated SELAM Worklist as UTF-8 CSV.
    """
    path = Path(file_path)

    try:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=CSV_COLUMNS,
                extrasaction="ignore",
            )

            writer.writeheader()
            writer.writerows(records)

    except OSError as exc:
        raise SelamOutputError(
            f"Could not save CSV file '{path}': {exc}"
        ) from exc

    return path

def save_manual_review_csv(
    records: list[dict[str, Any]],
    file_path: Path | str,
) -> Path:
    path = Path(
        file_path
    )

    try:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=MANUAL_REVIEW_COLUMNS,
                extrasaction="ignore",
            )

            writer.writeheader()
            writer.writerows(
                records
            )

    except OSError as exc:
        raise SelamOutputError(
            "Could not save manual review CSV "
            f"'{path}': {exc}"
        ) from exc

    return path


def build_weekly_summary(
    records: list[dict[str, Any]],
    *,
    aggregation_summary: dict[str, Any],
    weekly_run_id: str,
    window_start: str,
    window_end: str,
) -> dict[str, Any]:
    """
    Build an operational summary from the consolidated records.
    """
    records_by_country = Counter(
        clean_text(record.get("Country"))
        or "[UNKNOWN]"
        for record in records
    )

    records_by_client = Counter(
        clean_text(record.get("Client"))
        or "[UNKNOWN]"
        for record in records
    )

    records_by_status = Counter(
        clean_text(
            record.get("Output Status")
        )
        or "[UNKNOWN]"
        for record in records
    )

    review_records = [
        record
        for record in records
        if clean_text(
            record.get("Output Status")
        ).upper()
        != "READY"
        or clean_text(
            record.get("Output Issues")
        )
    ]

    return {
        "region": "SELAM",
        "weekly_run_id": weekly_run_id,
        "window_start": window_start,
        "window_end": window_end,
        "generated_at": (
            datetime.now()
            .astimezone()
            .isoformat(timespec="seconds")
        ),
        "processed_sources": aggregation_summary.get(
            "processed_sources",
            0,
        ),
        "total_records": len(records),
        "clients": len(records_by_client),
        "countries_with_records": len(
            records_by_country
        ),
        "records_by_country": dict(
            sorted(records_by_country.items())
        ),
        "records_by_client": dict(
            sorted(records_by_client.items())
        ),
        "records_by_output_status": dict(
            sorted(records_by_status.items())
        ),
        "ready_records": sum(
            1
            for record in records
            if clean_text(
                record.get("Output Status")
            ).upper()
            == "READY"
        ),
        "review_records": len(
            review_records
        ),
        "duplicate_issues": aggregation_summary.get(
            "duplicate_issues",
            0,
        ),
        "review_items": [
            {
                "client": record.get("Client", ""),
                "country": record.get("Country", ""),
                "session": record.get("Session", ""),
                "date": record.get("Date", ""),
                "project_id": record.get(
                    "Project ID",
                    "",
                ),
                "output_status": record.get(
                    "Output Status",
                    "",
                ),
                "output_issues": record.get(
                    "Output Issues",
                    "",
                ),
            }
            for record in review_records
        ],
    }


def generate_selam_outputs(
    manifest_path: Path | str,
) -> dict[str, Any]:
    """
    Generate CSV, Markdown, summary, and manual review outputs
    using the consolidated SELAM data.
    """
    manifest_file = Path(
        manifest_path
    )

    if not manifest_file.exists():
        raise SelamOutputError(
            "Weekly manifest does not exist: "
            f"{manifest_file}"
        )

    try:
        with manifest_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            manifest = json.load(
                file
            )

    except json.JSONDecodeError as exc:
        raise SelamOutputError(
            "Invalid weekly manifest JSON: "
            f"{exc}"
        ) from exc

    aggregation = manifest.get(
        "selam_aggregation"
    )

    if not isinstance(
        aggregation,
        dict,
    ):
        raise SelamOutputError(
            "Weekly manifest does not contain "
            "'selam_aggregation'."
        )

    consolidated_path = aggregation.get(
        "selam_consolidated_worklist_path"
    )

    if not consolidated_path:
        raise SelamOutputError(
            "SELAM aggregation does not contain "
            "'selam_consolidated_worklist_path'."
        )

    records = load_json_file(
        consolidated_path
    )

    if not isinstance(
        records,
        list,
    ):
        raise SelamOutputError(
            "SELAM consolidated Worklist "
            "must be a JSON list."
        )

    manual_review_aggregation = (
        manifest.get(
            "selam_manual_review",
            {},
        )
    )

    manual_review_path = (
        manual_review_aggregation.get(
            "selam_manual_review_path"
        )
        if isinstance(
            manual_review_aggregation,
            dict,
        )
        else None
    )

    manual_review_records = []

    if manual_review_path:
        loaded_manual_reviews = (
            load_json_file(
                manual_review_path
            )
        )

        if not isinstance(
            loaded_manual_reviews,
            list,
        ):
            raise SelamOutputError(
                "SELAM manual review "
                "must be a JSON list."
            )

        manual_review_records = (
            loaded_manual_reviews
        )

    weekly_run_id = clean_text(
        manifest.get(
            "weekly_run_id"
        )
    )

    window_start = clean_text(
        manifest.get(
            "window_start"
        )
    )

    window_end = clean_text(
        manifest.get(
            "window_end"
        )
    )

    weekly_manual_reviews = (
        filter_manual_reviews_by_window(
            manual_review_records,
            window_start=window_start,
            window_end=window_end,
        )
    )

    output_directory = (
        manifest_file.parent
    )

    csv_path = (
        output_directory
        / "selam_worklist.csv"
    )

    markdown_path = (
        output_directory
        / "selam_slack_ready.md"
    )

    summary_path = (
        output_directory
        / "selam_weekly_summary.json"
    )

    manual_review_csv_path = (
        output_directory
        / "selam_manual_review.csv"
    )

    save_csv_file(
        records=records,
        file_path=csv_path,
    )

    save_manual_review_csv(
        records=weekly_manual_reviews,
        file_path=manual_review_csv_path,
    )

    markdown = build_selam_markdown(
        records=records,
        weekly_run_id=weekly_run_id,
        window_start=window_start,
        window_end=window_end,
    )

    try:
        markdown_path.write_text(
            markdown,
            encoding="utf-8",
        )

    except OSError as exc:
        raise SelamOutputError(
            "Could not save Markdown file: "
            f"{exc}"
        ) from exc

    weekly_summary = (
        build_weekly_summary(
            records=records,
            aggregation_summary=aggregation,
            weekly_run_id=weekly_run_id,
            window_start=window_start,
            window_end=window_end,
        )
    )

    weekly_summary[
        "worklist_review_records"
    ] = weekly_summary[
        "review_records"
    ]

    weekly_summary[
        "manual_review_records"
    ] = len(
        weekly_manual_reviews
    )

    weekly_summary[
        "review_records"
    ] = (
        weekly_summary[
            "worklist_review_records"
        ]
        + weekly_summary[
            "manual_review_records"
        ]
    )

    weekly_summary[
        "manual_review_items"
    ] = [
        {
            "country": record.get(
                "Country",
                "",
            ),
            "client": record.get(
                "client_name",
                "",
            ),
            "project": record.get(
                "project_name",
                "",
            ),
            "date": record.get(
                "start_date",
                "",
            ),
            "reason": record.get(
                "decision_reason",
                "",
            ),
            "suggested_action": (
                record.get(
                    "Suggested Action",
                    "",
                )
            ),
            "project_url": record.get(
                "project_url",
                "",
            ),
        }
        for record in weekly_manual_reviews
    ]

    save_json_file(
        weekly_summary,
        summary_path,
    )

    manifest[
        "selam_outputs"
    ] = {
        "generated_at": (
            weekly_summary[
                "generated_at"
            ]
        ),
        "csv_path": str(
            csv_path
        ),
        "markdown_path": str(
            markdown_path
        ),
        "summary_path": str(
            summary_path
        ),
        "manual_review_csv_path": str(
            manual_review_csv_path
        ),
        "total_records": len(
            records
        ),
        "clients": weekly_summary[
            "clients"
        ],
        "ready_records": (
            weekly_summary[
                "ready_records"
            ]
        ),
        "worklist_review_records": (
            weekly_summary[
                "worklist_review_records"
            ]
        ),
        "manual_review_records": (
            weekly_summary[
                "manual_review_records"
            ]
        ),
        "review_records": (
            weekly_summary[
                "review_records"
            ]
        ),
    }

    manifest[
        "updated_at"
    ] = (
        datetime.now()
        .astimezone()
        .isoformat(
            timespec="seconds"
        )
    )

    try:
        with manifest_file.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                manifest,
                file,
                ensure_ascii=False,
                indent=2,
            )

    except OSError as exc:
        raise SelamOutputError(
            "Could not update weekly manifest: "
            f"{exc}"
        ) from exc

    return {
        "records": records,
        "markdown": markdown,
        "weekly_summary": (
            weekly_summary
        ),
        "manual_review_records": (
            weekly_manual_reviews
        ),
        "csv_path": csv_path,
        "markdown_path": (
            markdown_path
        ),
        "summary_path": (
            summary_path
        ),
        "manual_review_csv_path": (
            manual_review_csv_path
        ),
        "manifest": manifest,
    }