from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from engine.schedule_config import load_weekly_schedule
from engine.source_config import (
    get_enabled_sources,
    get_required_sources,
)

from engine.paths import data_path

DEFAULT_WEEKLY_OUTPUT_ROOT = data_path("output", "weekly_runs")

DATE_FORMAT_INPUT = "%m/%d/%Y"
DATE_FORMAT_RUN_ID = "%Y-%m-%d"

VALID_WEEKLY_RUN_STATUSES = {
    "INITIALIZED",
    "WAITING_FOR_REPORTS",
    "READY_TO_PROCESS",
    "PROCESSING",
    "COMPLETED",
    "COMPLETED_WITH_REVIEW",
    "FAILED",
}


class WeeklyRunError(Exception):
    """Raised when a weekly run cannot be created or validated."""


@dataclass(frozen=True)
class WeeklyWindow:
    reference_date: date
    window_start: date
    window_end: date


@dataclass
class WeeklyRun:
    weekly_run_id: str
    source_group: str
    reference_date: str
    execution_weekday: str
    window_start: str
    window_end: str
    window_length_days: int
    status: str
    expected_sources: list[dict[str, Any]]
    required_sources: list[dict[str, Any]]
    created_at: str
    output_directory: str
    is_partial: bool = False


def parse_reference_date(value: str) -> date:
    try:
        return datetime.strptime(
            value.strip(),
            DATE_FORMAT_INPUT,
        ).date()
    except ValueError as exc:
        raise WeeklyRunError(
            f"Invalid reference date '{value}'. "
            "Expected format M/D/YYYY, for example 7/27/2026."
        ) from exc


def validate_reference_weekday(
    reference_date: date,
    expected_weekday_number: int,
    expected_weekday_name: str,
) -> None:
    if reference_date.weekday() != expected_weekday_number:
        actual_weekday = reference_date.strftime("%A")

        raise WeeklyRunError(
            f"Reference date "
            f"{reference_date.strftime(DATE_FORMAT_INPUT)} "
            f"is {actual_weekday}, but the configured execution day "
            f"is {expected_weekday_name.capitalize()}."
        )


def calculate_weekly_window(
    reference_date: date,
    start_offset_days: int,
    window_length_days: int,
) -> WeeklyWindow:
    window_start = reference_date + timedelta(
        days=start_offset_days
    )

    window_end = window_start + timedelta(
        days=window_length_days - 1
    )

    return WeeklyWindow(
        reference_date=reference_date,
        window_start=window_start,
        window_end=window_end,
    )


def build_weekly_run_id(window: WeeklyWindow) -> str:
    start = window.window_start.strftime(DATE_FORMAT_RUN_ID)
    end = window.window_end.strftime(DATE_FORMAT_RUN_ID)

    return f"NPS_WEEK_{start}_{end}"


def serialize_source(
    source: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_id": source["source_id"],
        "country": source["country"],
        "report_type": source["report_type"],
        "required": bool(source["required"]),
        "enabled": bool(source["enabled"]),
        "status": "MISSING",
        "matched_file": None,
    }


def build_weekly_run(
    reference_date_text: str,
    source_group: str = "weekly_upcoming",
    output_root: Path | str = DEFAULT_WEEKLY_OUTPUT_ROOT,
) -> WeeklyRun:
    schedule = load_weekly_schedule()
    reference_date = parse_reference_date(reference_date_text)

    validate_reference_weekday(
        reference_date=reference_date,
        expected_weekday_number=schedule[
            "execution_weekday_number"
        ],
        expected_weekday_name=schedule["execution_weekday"],
    )

    window = calculate_weekly_window(
        reference_date=reference_date,
        start_offset_days=schedule[
            "window_start_offset_days"
        ],
        window_length_days=schedule[
            "window_length_days"
        ],
    )

    weekly_run_id = build_weekly_run_id(window)

    enabled_sources = get_enabled_sources(source_group)
    required_sources = get_required_sources(source_group)

    if not enabled_sources:
        raise WeeklyRunError(
            f"No enabled sources found for source group "
            f"'{source_group}'."
        )

    serialized_expected = [
        serialize_source(source)
        for source in enabled_sources
    ]

    required_ids = {
        source["source_id"]
        for source in required_sources
    }

    serialized_required = [
        source.copy()
        for source in serialized_expected
        if source["source_id"] in required_ids
    ]

    output_directory = Path(output_root) / weekly_run_id

    return WeeklyRun(
        weekly_run_id=weekly_run_id,
        source_group=source_group,
        reference_date=reference_date.strftime(DATE_FORMAT_INPUT),
        execution_weekday=schedule["execution_weekday"],
        window_start=window.window_start.strftime(DATE_FORMAT_INPUT),
        window_end=window.window_end.strftime(DATE_FORMAT_INPUT),
        window_length_days=schedule["window_length_days"],
        status="INITIALIZED",
        expected_sources=serialized_expected,
        required_sources=serialized_required,
        created_at=datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        output_directory=str(output_directory),
        is_partial=False,
    )


def validate_weekly_run(run: WeeklyRun) -> None:
    if run.status not in VALID_WEEKLY_RUN_STATUSES:
        raise WeeklyRunError(
            f"Invalid weekly run status: {run.status}"
        )

    if not run.weekly_run_id:
        raise WeeklyRunError(
            "weekly_run_id cannot be empty."
        )

    if not run.expected_sources:
        raise WeeklyRunError(
            "A weekly run must contain at least one expected source."
        )

    source_ids = [
        source["source_id"]
        for source in run.expected_sources
    ]

    if len(source_ids) != len(set(source_ids)):
        raise WeeklyRunError(
            "Duplicate source IDs detected in weekly run."
        )

    expected_ids = set(source_ids)

    for source in run.required_sources:
        if source["source_id"] not in expected_ids:
            raise WeeklyRunError(
                f"Required source '{source['source_id']}' "
                "is not present in expected_sources."
            )


def create_weekly_run(
    reference_date_text: str,
    source_group: str = "weekly_upcoming",
    output_root: Path | str = DEFAULT_WEEKLY_OUTPUT_ROOT,
    overwrite: bool = False,
) -> tuple[WeeklyRun, Path]:
    run = build_weekly_run(
        reference_date_text=reference_date_text,
        source_group=source_group,
        output_root=output_root,
    )

    validate_weekly_run(run)

    output_directory = Path(run.output_directory)
    manifest_path = output_directory / "weekly_manifest.json"

    if manifest_path.exists() and not overwrite:
        raise WeeklyRunError(
            f"Weekly run already exists: {run.weekly_run_id}. "
            "Use overwrite=True only during controlled testing."
        )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with manifest_path.open("w", encoding="utf-8") as file:
            json.dump(
                asdict(run),
                file,
                ensure_ascii=False,
                indent=2,
            )
    except OSError as exc:
        raise WeeklyRunError(
            f"Could not write weekly manifest: {exc}"
        ) from exc

    return run, manifest_path
