from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from engine.weekly_manifest import (
    load_weekly_manifest,
    save_weekly_manifest,
)


class SelamAggregatorError(Exception):
    """Raised when weekly SELAM worklists cannot be aggregated."""


def load_json_file(
    file_path: Path | str,
) -> Any:
    path = Path(file_path)

    if not path.exists():
        raise SelamAggregatorError(
            f"JSON file does not exist: {path}"
        )

    if not path.is_file():
        raise SelamAggregatorError(
            f"JSON path is not a file: {path}"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise SelamAggregatorError(
            f"Invalid JSON file '{path}': {exc}"
        ) from exc
    except OSError as exc:
        raise SelamAggregatorError(
            f"Could not read JSON file '{path}': {exc}"
        ) from exc

def load_csv_file(
    file_path: Path | str,
) -> list[dict[str, Any]]:
    path = Path(file_path)

    if not path.exists():
        raise SelamAggregatorError(
            f"CSV file does not exist: {path}"
        )

    if not path.is_file():
        raise SelamAggregatorError(
            f"CSV path is not a file: {path}"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            return list(
                csv.DictReader(file)
            )
    except OSError as exc:
        raise SelamAggregatorError(
            f"Could not read CSV file '{path}': {exc}"
        ) from exc


def save_json_file(
    data: Any,
    file_path: Path | str,
) -> Path:
    path = Path(file_path)

    try:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )
    except OSError as exc:
        raise SelamAggregatorError(
            f"Could not save JSON file '{path}': {exc}"
        ) from exc

    return path


def parse_salesforce_date(
    value: str,
) -> datetime:
    if not value:
        return datetime.max

    try:
        return datetime.strptime(
            value.strip(),
            "%m/%d/%Y",
        )
    except ValueError:
        return datetime.max


def build_record_key(
    record: dict[str, Any],
) -> tuple[str, str, str]:
    return (
        str(record.get("Project ID", "")).strip(),
        str(record.get("Date", "")).strip(),
        str(record.get("Session", "")).strip().casefold(),
    )


def enrich_worklist_record(
    record: dict[str, Any],
    *,
    country: str,
    source_id: str,
    execution_id: str,
    weekly_run_id: str,
) -> dict[str, Any]:
    return {
        **record,
        "Country": country,
        "Source ID": source_id,
        "Source Execution ID": execution_id,
        "Weekly Run ID": weekly_run_id,
        "Region": "SELAM",
    }

def enrich_selam_record(
    record: dict[str, Any],
    *,
    country: str,
    source_id: str,
    execution_id: str,
    weekly_run_id: str,
    record_type: str,
) -> dict[str, Any]:
    return {
        **record,
        "Country": country,
        "Source ID": source_id,
        "Source Execution ID": execution_id,
        "Weekly Run ID": weekly_run_id,
        "Region": "SELAM",
        "Record Type": record_type,
    }


def sort_worklist_records(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: (
            str(
                record.get(
                    "Client",
                    "",
                )
            ).strip().casefold(),
            str(
                record.get(
                    "Country",
                    "",
                )
            ).strip().casefold(),
            parse_salesforce_date(
                str(
                    record.get(
                        "Date",
                        "",
                    )
                )
            ),
            str(
                record.get(
                    "Session",
                    "",
                )
            ).strip().casefold(),
        ),
    )


def detect_cross_source_duplicates(
    records: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    unique_records: list[dict[str, Any]] = []
    duplicate_issues: list[dict[str, Any]] = []

    seen: dict[
        tuple[str, str, str],
        dict[str, Any],
    ] = {}

    for record in records:
        key = build_record_key(record)

        project_id, record_date, session = key

        if not project_id:
            unique_records.append(record)
            continue

        if key not in seen:
            seen[key] = record
            unique_records.append(record)
            continue

        original = seen[key]

        duplicate_issues.append(
            {
                "duplicate_key": {
                    "project_id": project_id,
                    "date": record_date,
                    "session": session,
                },
                "original_source_id": original.get(
                    "Source ID"
                ),
                "duplicate_source_id": record.get(
                    "Source ID"
                ),
                "original_execution_id": original.get(
                    "Source Execution ID"
                ),
                "duplicate_execution_id": record.get(
                    "Source Execution ID"
                ),
                "original_record": original,
                "duplicate_record": record,
            }
        )

    return unique_records, duplicate_issues


def aggregate_selam_worklists(
    manifest_path: Path | str,
) -> dict[str, Any]:
    path = Path(manifest_path)
    manifest = load_weekly_manifest(path)

    weekly_status = manifest.get(
        "status"
    )

    if weekly_status not in {
        "COMPLETED",
        "COMPLETED_WITH_REVIEW",
    }:
        raise SelamAggregatorError(
            "Weekly run must be completed before aggregation. "
            f"Current status: {weekly_status}"
        )

    weekly_run_id = manifest.get(
        "weekly_run_id",
        "",
    )

    if not weekly_run_id:
        raise SelamAggregatorError(
            "Weekly manifest is missing 'weekly_run_id'."
        )

    all_records: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []

    expected_sources = manifest.get(
        "expected_sources",
        [],
    )

    for source in expected_sources:
        if source.get("status") != "PROCESSED":
            continue

        result = source.get(
            "execution_result"
        )

        if not isinstance(result, dict):
            raise SelamAggregatorError(
                f"Source '{source.get('source_id')}' "
                "does not contain execution_result."
            )

        worklist_path = result.get(
            "worklist_path"
        )

        summary_path = result.get(
            "execution_summary_path"
        )

        execution_id = result.get(
            "execution_id",
            "",
        )

        country = result.get(
            "country",
            source.get("country", ""),
        )

        source_id = source.get(
            "source_id",
            "",
        )

        if not worklist_path:
            raise SelamAggregatorError(
                f"Source '{source_id}' "
                "does not contain worklist_path."
            )

        worklist_data = load_json_file(
            worklist_path
        )

        if not isinstance(
            worklist_data,
            list,
        ):
            raise SelamAggregatorError(
                f"Worklist for '{source_id}' "
                "must contain a JSON list."
            )

        for record in worklist_data:
            all_records.append(
                enrich_worklist_record(
                    record=record,
                    country=country,
                    source_id=source_id,
                    execution_id=execution_id,
                    weekly_run_id=weekly_run_id,
                )
            )

        execution_summary = {}

        if summary_path:
            execution_summary = load_json_file(
                summary_path
            )

        source_summaries.append(
            {
                "source_id": source_id,
                "country": country,
                "execution_id": execution_id,
                "worklist_records": len(
                    worklist_data
                ),
                "execution_counts": (
                    execution_summary.get(
                        "counts",
                        {},
                    )
                    if isinstance(
                        execution_summary,
                        dict,
                    )
                    else {}
                ),
            }
        )

    deduplicated_records, duplicate_issues = (
        detect_cross_source_duplicates(
            all_records
        )
    )

    sorted_records = sort_worklist_records(
        deduplicated_records
    )

    weekly_output_directory = path.parent

    consolidated_path = (
        weekly_output_directory
        / "selam_consolidated_worklist.json"
    )

    issues_path = (
        weekly_output_directory
        / "selam_consolidation_issues.json"
    )

    summary_path = (
        weekly_output_directory
        / "selam_aggregation_summary.json"
    )

    save_json_file(
        sorted_records,
        consolidated_path,
    )

    save_json_file(
        duplicate_issues,
        issues_path,
    )

    aggregation_summary = {
        "region": "SELAM",
        "weekly_run_id": weekly_run_id,
        "aggregated_at": (
            datetime.now()
            .astimezone()
            .isoformat(timespec="seconds")
        ),
        "processed_sources": len(
            source_summaries
        ),
        "records_before_deduplication": len(
            all_records
        ),
        "records_after_deduplication": len(
            sorted_records
        ),
        "duplicate_issues": len(
            duplicate_issues
        ),
        "clients": len(
            {
                str(
                    record.get(
                        "Client",
                        "",
                    )
                ).strip()
                for record in sorted_records
                if str(
                    record.get(
                        "Client",
                        "",
                    )
                ).strip()
            }
        ),
        "countries": sorted(
            {
                str(
                    record.get(
                        "Country",
                        "",
                    )
                ).strip()
                for record in sorted_records
                if str(
                    record.get(
                        "Country",
                        "",
                    )
                ).strip()
            }
        ),
        "source_summaries": source_summaries,
        "selam_consolidated_worklist_path": str(
            consolidated_path
        ),
        "selam_consolidation_issues_path": str(
            issues_path
        ),
    }

    save_json_file(
        aggregation_summary,
        summary_path,
    )

    manifest["selam_aggregation"] = {
        **aggregation_summary,
        "summary_path": str(
            summary_path
        ),
    }

    manifest["updated_at"] = (
        datetime.now()
        .astimezone()
        .isoformat(timespec="seconds")
    )

    save_weekly_manifest(
        manifest_path=path,
        manifest=manifest,
    )

    return {
        "records": sorted_records,
        "duplicate_issues": duplicate_issues,
        "summary": aggregation_summary,
        "manifest": manifest,
    }

def build_manual_review_key(
    record: dict[str, Any],
) -> tuple[str, str, str]:
    return (
        str(
            record.get(
                "project_url",
                "",
            )
        ).strip().casefold(),
        str(
            record.get(
                "start_date",
                "",
            )
        ).strip(),
        str(
            record.get(
                "project_name",
                "",
            )
        ).strip().casefold(),
    )

def detect_manual_review_duplicates(
    records: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    unique_records: list[dict[str, Any]] = []
    duplicate_issues: list[dict[str, Any]] = []

    seen: dict[
        tuple[str, str, str],
        dict[str, Any],
    ] = {}

    for record in records:
        key = build_manual_review_key(
            record
        )

        project_url, record_date, project_name = key

        if not project_url and not project_name:
            unique_records.append(
                record
            )
            continue

        if key not in seen:
            seen[key] = record
            unique_records.append(
                record
            )
            continue

        original = seen[key]

        duplicate_issues.append(
            {
                "duplicate_key": {
                    "project_url": project_url,
                    "date": record_date,
                    "project_name": project_name,
                },
                "original_source_id": original.get(
                    "Source ID"
                ),
                "duplicate_source_id": record.get(
                    "Source ID"
                ),
                "original_record": original,
                "duplicate_record": record,
            }
        )

    return (
        unique_records,
        duplicate_issues,
    )

def sort_manual_review_records(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: (
            str(
                record.get(
                    "client_name",
                    "",
                )
            ).strip().casefold(),
            str(
                record.get(
                    "Country",
                    "",
                )
            ).strip().casefold(),
            parse_salesforce_date(
                str(
                    record.get(
                        "start_date",
                        "",
                    )
                )
            ),
            str(
                record.get(
                    "project_name",
                    "",
                )
            ).strip().casefold(),
        ),
    )

def aggregate_selam_manual_reviews(
    manifest_path: Path | str,
) -> dict[str, Any]:
    path = Path(manifest_path)
    manifest = load_weekly_manifest(
        path
    )

    weekly_status = manifest.get(
        "status"
    )

    if weekly_status not in {
        "COMPLETED",
        "COMPLETED_WITH_REVIEW",
    }:
        raise SelamAggregatorError(
            "Weekly run must be completed before "
            "manual review aggregation. "
            f"Current status: {weekly_status}"
        )

    weekly_run_id = manifest.get(
        "weekly_run_id",
        "",
    )

    if not weekly_run_id:
        raise SelamAggregatorError(
            "Weekly manifest is missing "
            "'weekly_run_id'."
        )

    all_records: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []

    expected_sources = manifest.get(
        "expected_sources",
        [],
    )

    for source in expected_sources:
        if source.get("status") != "PROCESSED":
            continue

        result = source.get(
            "execution_result"
        )

        if not isinstance(
            result,
            dict,
        ):
            raise SelamAggregatorError(
                f"Source '{source.get('source_id')}' "
                "does not contain execution_result."
            )

        review_path = result.get(
            "business_review_path"
        )

        execution_id = result.get(
            "execution_id",
            "",
        )

        country = result.get(
            "country",
            source.get(
                "country",
                "",
            ),
        )

        source_id = source.get(
            "source_id",
            "",
        )

        if not review_path:
            source_summaries.append(
                {
                    "source_id": source_id,
                    "country": country,
                    "execution_id": execution_id,
                    "manual_review_records": 0,
                    "review_file_available": False,
                }
            )
            continue

        review_file = Path(
            review_path
        )

        if not review_file.exists():
            source_summaries.append(
                {
                    "source_id": source_id,
                    "country": country,
                    "execution_id": execution_id,
                    "manual_review_records": 0,
                    "review_file_available": False,
                }
            )
            continue

        review_data = load_csv_file(
            review_file
        )

        for record in review_data:
            all_records.append(
                enrich_selam_record(
                    record=record,
                    country=country,
                    source_id=source_id,
                    execution_id=execution_id,
                    weekly_run_id=weekly_run_id,
                    record_type="MANUAL_REVIEW",
                )
            )

        source_summaries.append(
            {
                "source_id": source_id,
                "country": country,
                "execution_id": execution_id,
                "manual_review_records": len(
                    review_data
                ),
                "review_file_available": True,
            }
        )

    (
        deduplicated_records,
        duplicate_issues,
    ) = detect_manual_review_duplicates(
        all_records
    )

    sorted_records = (
        sort_manual_review_records(
            deduplicated_records
        )
    )

    weekly_output_directory = path.parent

    consolidated_path = (
        weekly_output_directory
        / "selam_manual_review.json"
    )

    issues_path = (
        weekly_output_directory
        / "selam_manual_review_issues.json"
    )

    summary_path = (
        weekly_output_directory
        / "selam_manual_review_summary.json"
    )

    save_json_file(
        sorted_records,
        consolidated_path,
    )

    save_json_file(
        duplicate_issues,
        issues_path,
    )

    review_summary = {
        "region": "SELAM",
        "weekly_run_id": weekly_run_id,
        "aggregated_at": (
            datetime.now()
            .astimezone()
            .isoformat(
                timespec="seconds"
            )
        ),
        "processed_sources": len(
            source_summaries
        ),
        "records_before_deduplication": len(
            all_records
        ),
        "records_after_deduplication": len(
            sorted_records
        ),
        "duplicate_issues": len(
            duplicate_issues
        ),
        "countries": sorted(
            {
                str(
                    record.get(
                        "Country",
                        "",
                    )
                ).strip()
                for record in sorted_records
                if str(
                    record.get(
                        "Country",
                        "",
                    )
                ).strip()
            }
        ),
        "source_summaries": source_summaries,
        "selam_manual_review_path": str(
            consolidated_path
        ),
        "selam_manual_review_issues_path": str(
            issues_path
        ),
    }

    save_json_file(
        review_summary,
        summary_path,
    )

    manifest["selam_manual_review"] = {
        **review_summary,
        "summary_path": str(
            summary_path
        ),
    }

    manifest["updated_at"] = (
        datetime.now()
        .astimezone()
        .isoformat(
            timespec="seconds"
        )
    )

    save_weekly_manifest(
        manifest_path=path,
        manifest=manifest,
    )

    return {
        "records": sorted_records,
        "duplicate_issues": duplicate_issues,
        "summary": review_summary,
        "manifest": manifest,
    }