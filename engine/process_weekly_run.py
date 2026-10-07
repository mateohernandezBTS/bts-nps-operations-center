from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from engine.selam_aggregator import (
    aggregate_selam_manual_reviews,
    aggregate_selam_worklists,
)
from engine.selam_output import (
    generate_selam_outputs,
)
from engine.source_inventory import (
    build_source_inventory,
)
from engine.weekly_manifest import (
    update_weekly_manifest_from_inventory,
)
from engine.weekly_orchestrator import (
    process_weekly_run,
)
from engine.weekly_run import (
    WeeklyRunError,
    create_weekly_run,
)

import json

from engine.slack_canvas_renderer import (
    generate_slack_canvas_html,
)

from engine.weekly_excel import (
    generate_weekly_excel,
)

from engine.paths import config_path, data_path, test_data_path


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

TEST_SYSTEM_CONFIG = (
    config_path("system_config_test.json")
)


class WeeklyEndToEndError(Exception):
    """Raised when the end-to-end weekly run fails."""


def resolve_environment(
    test_mode: bool,
) -> tuple[Path, Path, str]:
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


def print_inventory_summary(
    inventory,
) -> None:
    print()
    print("INVENTORY")
    print("-" * 80)
    print(
        f"Files scanned: "
        f"{inventory.files_scanned}"
    )
    print(
        f"Matched files: "
        f"{inventory.matched_files}"
    )
    print(
        "Known out of scope: "
        f"{inventory.known_out_of_scope_files}"
    )
    print(
        "Detection review: "
        f"{inventory.review_files}"
    )
    print(
        "Unknown reports: "
        f"{inventory.unconfigured_files}"
    )
    print(
        "Duplicate sources: "
        f"{inventory.duplicate_sources}"
    )
    print(
        "Missing required sources: "
        f"{inventory.missing_required_sources}"
    )


def print_final_summary(
    result: dict[str, Any],
) -> None:
    manifest = result["manifest"]
    weekly_summary = result[
        "weekly_summary"
    ]

    print()
    print("FINAL RESULT")
    print("-" * 80)

    print(
        f"Weekly Run ID: "
        f"{manifest['weekly_run_id']}"
    )

    print(
        f"Status: "
        f"{manifest['status']}"
    )

    print(
        f"Region: "
        f"{weekly_summary['region']}"
    )

    print(
        f"Total records: "
        f"{weekly_summary['total_records']}"
    )

    print(
        f"Clients: "
        f"{weekly_summary['clients']}"
    )

    print(
        f"Ready records: "
        f"{weekly_summary['ready_records']}"
    )

    print(
        f"Review records: "
        f"{weekly_summary['review_records']}"
    )

    print(
        f"Duplicate issues: "
        f"{weekly_summary['duplicate_issues']}"
    )

    print()
    print(
        f"Excel: "
        f"{result['weekly_excel_path']}"
    )

    print(
        f"Slack Canvas: "
        f"{result['slack_canvas_path']}"
    )

    print(
        f"CSV: "
        f"{result['csv_path']}"
    )

    print(
        f"Manual Review: "
        f"{result['manual_review_csv_path']}"
    )

    print(
        f"Summary: "
        f"{result['summary_path']}"
    )

def load_execution_config(
    test_mode: bool,
) -> dict[str, Any] | None:
    """
    Load isolated lifecycle configuration for testing.

    Production keeps using the default system_config.json.
    """
    if not test_mode:
        return None

    if not TEST_SYSTEM_CONFIG.exists():
        raise WeeklyEndToEndError(
            "Testing system configuration does not exist: "
            f"{TEST_SYSTEM_CONFIG}"
        )

    try:
        with TEST_SYSTEM_CONFIG.open(
            "r",
            encoding="utf-8",
        ) as file:
            configuration = json.load(file)
    except json.JSONDecodeError as exc:
        raise WeeklyEndToEndError(
            f"Invalid testing system configuration: {exc}"
        ) from exc

    return configuration

def execute_weekly_end_to_end(
    reference_date: str,
    *,
    test_mode: bool = False,
    stop_on_error: bool = False,
) -> dict[str, Any]:
    input_directory, output_root, environment = (
        resolve_environment(test_mode)
    )

    execution_config = load_execution_config(
        test_mode
    )

    print("=" * 80)
    print("NPS WEEKLY END-TO-END RUN")
    print("=" * 80)
    print(f"Environment: {environment}")
    print(f"Reference date: {reference_date}")
    print(f"Input directory: {input_directory}")
    print(f"Output root: {output_root}")

    if not input_directory.exists():
        raise WeeklyEndToEndError(
            f"Input directory does not exist: "
            f"{input_directory}"
        )

    try:
        run, manifest_path = create_weekly_run(
            reference_date_text=reference_date,
            source_group="weekly_upcoming",
            output_root=output_root,
        )
    except WeeklyRunError as exc:
        raise WeeklyEndToEndError(
            str(exc)
        ) from exc

    print()
    print("WEEKLY RUN")
    print("-" * 80)
    print(f"Weekly Run ID: {run.weekly_run_id}")
    print(f"Window start: {run.window_start}")
    print(f"Window end: {run.window_end}")
    print(f"Manifest: {manifest_path}")

    inventory = build_source_inventory(
        pending_directory=input_directory,
        source_group="weekly_upcoming",
    )

    print_inventory_summary(
        inventory
    )

    ready_manifest = (
        update_weekly_manifest_from_inventory(
            manifest_path=manifest_path,
            inventory=inventory,
        )
    )

    if ready_manifest["status"] != "READY_TO_PROCESS":
        issues = ready_manifest.get(
            "source_inventory",
            {},
        ).get(
            "readiness_issues",
            [],
        )

        raise WeeklyEndToEndError(
            "Weekly run is not ready for processing: "
            + " | ".join(issues)
        )

    completed_manifest = process_weekly_run(
        manifest_path=manifest_path,
        stop_on_error=stop_on_error,
        execution_config=execution_config,
    )

    if completed_manifest["status"] not in {
        "COMPLETED",
        "COMPLETED_WITH_REVIEW",
    }:
        raise WeeklyEndToEndError(
            "Weekly processing did not complete. "
            f"Status: "
            f"{completed_manifest['status']}"
        )

    aggregate_selam_worklists(
    manifest_path=manifest_path,
    )

    aggregate_selam_manual_reviews(
    manifest_path=manifest_path,
    )

    output_result = generate_selam_outputs(
    manifest_path=manifest_path,
    )

    slack_canvas_path = (
    generate_slack_canvas_html(
        manifest_path.parent
    )
    )

    weekly_excel_path = (
    generate_weekly_excel(
        manifest_path
    )
)

    final_result = {
    **output_result,
    "manifest_path": manifest_path,
    "manifest": output_result["manifest"],
    "slack_canvas_path": slack_canvas_path,
    "weekly_excel_path": weekly_excel_path,
    }

    print_final_summary(
    final_result
    )

    print()
    print("=" * 80)
    print("WEEKLY END-TO-END RUN COMPLETED")
    print("=" * 80)

    return final_result


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Execute the complete weekly NPS "
            "processing workflow."
        )
    )

    parser.add_argument(
        "reference_date",
        help=(
            "Configured execution date in "
            "M/D/YYYY format."
        ),
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help=(
            "Use testing input and output "
            "directories."
        ),
    )

    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help=(
            "Stop after the first source failure."
        ),
    )

    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    execute_weekly_end_to_end(
        reference_date=args.reference_date,
        test_mode=args.test,
        stop_on_error=args.stop_on_error,
    )


if __name__ == "__main__":
    main()
