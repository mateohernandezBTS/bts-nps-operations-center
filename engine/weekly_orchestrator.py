from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from engine.process_report import process_report_file
from engine.weekly_manifest import (
    load_weekly_manifest,
    save_weekly_manifest,
)


class WeeklyOrchestratorError(Exception):
    """Raised when a weekly run cannot be orchestrated."""


def current_timestamp() -> str:
    return (
        datetime.now()
        .astimezone()
        .isoformat(timespec="seconds")
    )


def find_expected_source(
    manifest: dict[str, Any],
    source_id: str,
) -> dict[str, Any]:
    """
    Find one configured source inside the weekly manifest.
    """
    for source in manifest.get("expected_sources", []):
        if source.get("source_id") == source_id:
            return source

    raise WeeklyOrchestratorError(
        f"Source not found in manifest: {source_id}"
    )


def resolve_source_path(
    manifest: dict[str, Any],
    source: dict[str, Any],
) -> Path:
    """
    Resolve the original EML path using the inventory directory
    and the matched file stored in the manifest.
    """
    source_inventory = manifest.get("source_inventory", {})
    scanned_directory = source_inventory.get(
        "scanned_directory",
        "",
    )

    matched_file = source.get("matched_file")

    if not scanned_directory:
        raise WeeklyOrchestratorError(
            "The manifest does not contain "
            "'source_inventory.scanned_directory'."
        )

    if not matched_file:
        raise WeeklyOrchestratorError(
            f"Source '{source['source_id']}' "
            "does not contain a matched_file."
        )

    source_path = (
        Path(scanned_directory)
        / matched_file
    )

    if not source_path.exists():
        raise WeeklyOrchestratorError(
            f"Source file does not exist: {source_path}"
        )

    return source_path


def initialize_source_processing_fields(
    source: dict[str, Any],
) -> None:
    """
    Ensure processing fields exist before execution.
    """
    source.setdefault("processing_started_at", None)
    source.setdefault("processing_finished_at", None)
    source.setdefault("execution_result", None)
    source.setdefault("processing_error", None)


def summarize_weekly_results(
    manifest: dict[str, Any],
) -> dict[str, int]:
    """
    Count processing results across all expected sources.
    """
    sources = manifest.get("expected_sources", [])

    return {
        "configured_sources": len(sources),
        "processed_sources": sum(
            1
            for source in sources
            if source.get("status") == "PROCESSED"
        ),
        "failed_sources": sum(
            1
            for source in sources
            if source.get("status") == "FAILED"
        ),
        "received_sources": sum(
            1
            for source in sources
            if source.get("status") == "RECEIVED"
        ),
        "missing_sources": sum(
            1
            for source in sources
            if source.get("status") == "MISSING"
        ),
        "duplicate_sources": sum(
            1
            for source in sources
            if source.get("status") == "DUPLICATE"
        ),
    }


def determine_final_weekly_status(
    manifest: dict[str, Any],
) -> str:
    """
    Determine the final status after all available sources run.
    """
    summary = summarize_weekly_results(manifest)

    if summary["failed_sources"] > 0:
        if summary["processed_sources"] > 0:
            return "COMPLETED_WITH_REVIEW"

        return "FAILED"

    if (
        summary["processed_sources"]
        == summary["configured_sources"]
    ):
        return "COMPLETED"

    return "COMPLETED_WITH_REVIEW"


def process_weekly_run(
    manifest_path: Path | str,
    stop_on_error: bool = False,
    execution_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Process every RECEIVED source in a weekly manifest.

    The individual EML files are processed by process_report_file().
    Each execution retains its own output/runs/<execution_id> folder.

    Args:
        manifest_path:
            Path to weekly_manifest.json.
        stop_on_error:
            When True, stop immediately after the first source failure.
            When False, continue processing the remaining sources.

    Returns:
        Updated weekly manifest.
    """
    path = Path(manifest_path)
    manifest = load_weekly_manifest(path)

    if manifest.get("status") != "READY_TO_PROCESS":
        raise WeeklyOrchestratorError(
            "Weekly run is not ready for processing. "
            f"Current status: {manifest.get('status')}"
        )

    expected_sources = manifest.get(
        "expected_sources",
        [],
    )

    if not expected_sources:
        raise WeeklyOrchestratorError(
            "The weekly manifest contains no expected sources."
        )

    sources_to_process = [
        source
        for source in expected_sources
        if source.get("status") == "RECEIVED"
    ]

    if not sources_to_process:
        raise WeeklyOrchestratorError(
            "No RECEIVED sources are available for processing."
        )

    manifest["status"] = "PROCESSING"
    manifest["processing_started_at"] = current_timestamp()
    manifest["processing_finished_at"] = None
    manifest["processing_summary"] = None
    manifest["updated_at"] = current_timestamp()

    for source in expected_sources:
        initialize_source_processing_fields(source)

    save_weekly_manifest(
        manifest_path=path,
        manifest=manifest,
    )

    reference_date = manifest.get(
        "reference_date",
        "",
    )

    if not reference_date:
        raise WeeklyOrchestratorError(
            "The weekly manifest is missing 'reference_date'."
        )

    for source_snapshot in sources_to_process:
        source_id = source_snapshot["source_id"]

        # Reload the current source object from the manifest
        # so later saves always use the latest version.
        source = find_expected_source(
            manifest=manifest,
            source_id=source_id,
        )

        source["status"] = "PROCESSING"
        source["processing_started_at"] = (
            current_timestamp()
        )
        source["processing_finished_at"] = None
        source["processing_error"] = None

        manifest["updated_at"] = current_timestamp()

        save_weekly_manifest(
            manifest_path=path,
            manifest=manifest,
        )

        try:
            source_path = resolve_source_path(
                manifest=manifest,
                source=source,
            )

            result = process_report_file(
                source_path=source_path,
                reference_monday=reference_date,
                system_config_override=execution_config,
            )

            source["status"] = "PROCESSED"
            source["processing_finished_at"] = (
                current_timestamp()
            )
            source["execution_result"] = result
            source["processing_error"] = None

        except Exception as error:
            source["status"] = "FAILED"
            source["processing_finished_at"] = (
                current_timestamp()
            )
            source["execution_result"] = None
            source["processing_error"] = {
                "error_type": type(error).__name__,
                "message": str(error),
                "failed_at": current_timestamp(),
            }

            manifest["updated_at"] = current_timestamp()

            save_weekly_manifest(
                manifest_path=path,
                manifest=manifest,
            )

            if stop_on_error:
                manifest["status"] = "FAILED"
                manifest["processing_finished_at"] = (
                    current_timestamp()
                )
                manifest["processing_summary"] = (
                    summarize_weekly_results(manifest)
                )
                manifest["updated_at"] = current_timestamp()

                save_weekly_manifest(
                    manifest_path=path,
                    manifest=manifest,
                )

                raise

        manifest["updated_at"] = current_timestamp()

        save_weekly_manifest(
            manifest_path=path,
            manifest=manifest,
        )

    manifest["status"] = determine_final_weekly_status(
        manifest
    )

    manifest["processing_finished_at"] = (
        current_timestamp()
    )

    manifest["processing_summary"] = (
        summarize_weekly_results(manifest)
    )

    manifest["updated_at"] = current_timestamp()

    save_weekly_manifest(
        manifest_path=path,
        manifest=manifest,
    )

    return manifest