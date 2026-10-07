from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from engine.source_config import (
    load_source_configuration,
)
from engine.source_inventory import (
    SourceInventoryError,
    build_source_inventory,
    inventory_to_dict,
)

from engine.paths import data_path, test_data_path


PRODUCTION_INPUT = (
    data_path("input", "upcoming")
)

TEST_INPUT = (
    test_data_path(
        "input",
        "power_automate",
        "upcoming",
    )
)

PRODUCTION_OUTPUT = (
    data_path("output", "weekly_runs")
)

TEST_OUTPUT = (
    test_data_path("output", "weekly_runs")
)


class WeeklyPreflightError(Exception):
    """Raised when the weekly preflight cannot be completed."""


def parse_reference_date(
    reference_date_text: str,
) -> datetime:
    """
    Parse a reference date in Salesforce format M/D/YYYY.

    The weekly process is expected to run using a Monday
    as the reference date.
    """
    try:
        reference_date = datetime.strptime(
            reference_date_text,
            "%m/%d/%Y",
        )
    except ValueError as exc:
        raise WeeklyPreflightError(
            "Invalid reference date. "
            "Use M/D/YYYY format, for example 8/3/2026."
        ) from exc

    if reference_date.weekday() != 0:
        raise WeeklyPreflightError(
            "The reference date must be a Monday. "
            f"Received: {reference_date_text}"
        )

    return reference_date


def calculate_weekly_window(
    reference_date: datetime,
) -> tuple[datetime, datetime]:
    """
    Calculate the operational weekly window.

    Tuesday after the reference Monday
    through the following Monday, inclusive.
    """
    window_start = reference_date + timedelta(days=1)
    window_end = reference_date + timedelta(days=7)

    return window_start, window_end


def resolve_environment(
    test_mode: bool,
) -> tuple[Path, Path, str]:
    """
    Return input directory, output root, and environment.
    """
    if test_mode:
        return (
            TEST_INPUT,
            TEST_OUTPUT,
            "TEST",
        )

    return (
        PRODUCTION_INPUT,
        PRODUCTION_OUTPUT,
        "PRODUCTION",
    )


def load_source_group(
    source_group: str,
) -> dict[str, Any]:
    """
    Load and validate the selected source group.
    """
    configuration = load_source_configuration()

    source_groups = configuration.get(
        "source_groups",
        {},
    )

    group = source_groups.get(source_group)

    if group is None:
        raise WeeklyPreflightError(
            f"Source group does not exist: {source_group}"
        )

    if not group.get("enabled", False):
        raise WeeklyPreflightError(
            f"Source group is disabled: {source_group}"
        )

    return group


def build_weekly_run_id(
    window_start: datetime,
    window_end: datetime,
) -> str:
    """
    Generate the expected weekly run identifier without
    creating folders or modifying the filesystem.
    """
    return (
        "NPS_WEEK_"
        f"{window_start.strftime('%Y-%m-%d')}_"
        f"{window_end.strftime('%Y-%m-%d')}"
    )


def build_readiness_issues(
    inventory,
    *,
    allow_partial_run: bool,
    existing_run_directory: Path,
) -> list[str]:
    """
    Build human-readable blocking issues.
    """
    issues: list[str] = []

    for source in inventory.sources:
        if source.status == "MISSING" and source.required:
            issues.append(
                "Missing required source: "
                f"{source.country} "
                f"{source.report_type}"
            )

        if source.status == "DUPLICATE":
            issues.append(
                "Duplicate source: "
                f"{source.country} "
                f"{source.report_type} "
                f"({len(source.matched_files)} files)"
            )

    if inventory.review_files > 0:
        issues.append(
            "Files require report-detection review: "
            f"{inventory.review_files}"
        )

    if inventory.unconfigured_files > 0:
        issues.append(
            "Unknown or unconfigured reports detected: "
            f"{inventory.unconfigured_files}"
        )

    if (
        inventory.missing_required_sources > 0
        and not allow_partial_run
    ):
        issues.append(
            "Partial weekly runs are disabled."
        )

    if existing_run_directory.exists():
        issues.append(
            "A weekly run already exists: "
            f"{existing_run_directory.name}"
        )

    return issues


def run_weekly_preflight(
    reference_date_text: str,
    *,
    test_mode: bool = False,
    source_group: str = "weekly_upcoming",
) -> dict[str, Any]:
    """
    Inspect weekly sources without moving, processing,
    archiving, or modifying any report file.

    The returned dictionary is suitable for both:
    - command-line output;
    - the future graphical interface.
    """
    reference_date = parse_reference_date(
        reference_date_text
    )

    window_start, window_end = (
        calculate_weekly_window(reference_date)
    )

    input_directory, output_root, environment = (
        resolve_environment(test_mode)
    )

    source_group_config = load_source_group(
        source_group
    )

    allow_partial_run = bool(
        source_group_config.get(
            "allow_partial_run",
            False,
        )
    )

    weekly_run_id = build_weekly_run_id(
        window_start,
        window_end,
    )

    expected_run_directory = (
        output_root
        / weekly_run_id
    )

    if not input_directory.exists():
        raise WeeklyPreflightError(
            "Input directory does not exist: "
            f"{input_directory}"
        )

    if not input_directory.is_dir():
        raise WeeklyPreflightError(
            "Input path is not a directory: "
            f"{input_directory}"
        )

    try:
        inventory = build_source_inventory(
            pending_directory=input_directory,
            source_group=source_group,
        )
    except SourceInventoryError as exc:
        raise WeeklyPreflightError(
            str(exc)
        ) from exc

    issues = build_readiness_issues(
        inventory,
        allow_partial_run=allow_partial_run,
        existing_run_directory=(
            expected_run_directory
        ),
    )

    status = (
        "READY_TO_PROCESS"
        if not issues
        else "BLOCKED"
    )

    return {
        "environment": environment,
"reference_date": format_date_portable(
    reference_date
),
"window_start": format_date_portable(
    window_start
),
"window_end": format_date_portable(
    window_end
),
        "weekly_run_id": weekly_run_id,
        "source_group": source_group,
        "input_directory": str(input_directory),
        "output_root": str(output_root),
        "expected_run_directory": str(
            expected_run_directory
        ),
        "allow_partial_run": allow_partial_run,
        "status": status,
        "issues": issues,
        "inventory": inventory_to_dict(
            inventory
        ),
    }


def format_date_portable(
    value: datetime,
) -> str:
    """
    Format a date as M/D/YYYY without platform-specific
    strftime flags.
    """
    return (
        f"{value.month}/"
        f"{value.day}/"
        f"{value.year}"
    )


def print_preflight_result(
    result: dict[str, Any],
) -> None:
    """
    Print a user-friendly preflight summary.
    """
    inventory = result["inventory"]

    print("=" * 80)
    print("NPS WEEKLY PREFLIGHT")
    print("=" * 80)

    print(
        f"Environment: "
        f"{result['environment']}"
    )
    print(
        f"Reference date: "
        f"{result['reference_date']}"
    )
    print(
        f"Weekly window: "
        f"{result['window_start']} "
        f"- {result['window_end']}"
    )
    print(
        f"Weekly Run ID: "
        f"{result['weekly_run_id']}"
    )
    print(
        f"Input directory: "
        f"{result['input_directory']}"
    )

    print()
    print("EXPECTED SOURCES")
    print("-" * 80)

    for source in inventory["sources"]:
        label = (
            f"{source['country']} "
            f"{source['report_type']}"
        )

        print(
            f"{label}: "
            f"{source['status']}"
        )

        if source["matched_files"]:
            for filename in source["matched_files"]:
                print(
                    f"  - {filename}"
                )

    print()
    print("FILES")
    print("-" * 80)

    print(
        f"Files scanned: "
        f"{inventory['files_scanned']}"
    )
    print(
        f"Matched files: "
        f"{inventory['matched_files']}"
    )
    print(
        "Known out of scope: "
        f"{inventory['known_out_of_scope_files']}"
    )
    print(
        "Detection review: "
        f"{inventory['review_files']}"
    )
    print(
        "Unknown reports: "
        f"{inventory['unconfigured_files']}"
    )
    print(
        "Duplicate sources: "
        f"{inventory['duplicate_sources']}"
    )
    print(
        "Missing required sources: "
        f"{inventory['missing_required_sources']}"
    )

    print()
    print("STATUS")
    print("-" * 80)
    print(result["status"])

    if result["issues"]:
        print()
        print("ISSUES")
        print("-" * 80)

        for issue in result["issues"]:
            print(f"- {issue}")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate whether the weekly NPS run is ready "
            "without processing or modifying source files."
        )
    )

    parser.add_argument(
        "reference_date",
        help=(
            "Reference Monday in M/D/YYYY format."
        ),
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help=(
            "Use isolated testing input and output paths."
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Print the structured result as JSON."
        ),
    )

    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    try:
        result = run_weekly_preflight(
            reference_date_text=(
                args.reference_date
            ),
            test_mode=args.test,
        )
    except WeeklyPreflightError as exc:
        print("=" * 80)
        print("NPS WEEKLY PREFLIGHT FAILED")
        print("=" * 80)
        print(str(exc))
        raise SystemExit(1) from exc

    if args.json:
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print_preflight_result(
            result
        )

    if result["status"] != "READY_TO_PROCESS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
