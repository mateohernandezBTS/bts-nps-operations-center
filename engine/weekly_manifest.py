from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from engine.source_inventory import (
    SourceInventory,
    SourceInventoryError,
)


def determine_inventory_readiness(
    inventory: SourceInventory,
) -> tuple[str, list[str]]:
    """
    Determine whether a weekly source inventory is ready.

    Returns:
        A weekly run status and a list of readiness issues.
    """
    issues: list[str] = []

    for source in inventory.sources:
        if source.required and source.status == "MISSING":
            issues.append(
                f"Missing required source: {source.source_id}"
            )

        if source.status == "DUPLICATE":
            issues.append(
                f"Duplicate source: {source.source_id}"
            )

    if inventory.review_files:
        issues.append(
            "Reports requiring detection review: "
            f"{inventory.review_files}"
        )

    if inventory.unconfigured_files:
        issues.append(
            "Unconfigured reports detected: "
            f"{inventory.unconfigured_files}"
        )

    if issues:
        return "WAITING_FOR_REPORTS", issues

    return "READY_TO_PROCESS", []


def load_weekly_manifest(
    manifest_path: Path | str,
) -> dict[str, Any]:
    """
    Load and validate a weekly manifest JSON file.
    """
    path = Path(manifest_path)

    if not path.exists():
        raise SourceInventoryError(
            f"Weekly manifest does not exist: {path}"
        )

    if not path.is_file():
        raise SourceInventoryError(
            f"Weekly manifest path is not a file: {path}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            manifest = json.load(file)
    except json.JSONDecodeError as exc:
        raise SourceInventoryError(
            f"Invalid weekly manifest JSON: {exc}"
        ) from exc
    except OSError as exc:
        raise SourceInventoryError(
            f"Could not read weekly manifest: {exc}"
        ) from exc

    if not isinstance(manifest, dict):
        raise SourceInventoryError(
            "Weekly manifest must contain a JSON object."
        )

    if not manifest.get("weekly_run_id"):
        raise SourceInventoryError(
            "Weekly manifest is missing 'weekly_run_id'."
        )

    if not manifest.get("source_group"):
        raise SourceInventoryError(
            "Weekly manifest is missing 'source_group'."
        )

    return manifest


def save_weekly_manifest(
    manifest_path: Path | str,
    manifest: dict[str, Any],
) -> None:
    """
    Save a weekly manifest to disk.
    """
    path = Path(manifest_path)

    try:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open("w", encoding="utf-8") as file:
            json.dump(
                manifest,
                file,
                ensure_ascii=False,
                indent=2,
            )
    except OSError as exc:
        raise SourceInventoryError(
            f"Could not save weekly manifest: {exc}"
        ) from exc


def update_weekly_manifest_from_inventory(
    manifest_path: Path | str,
    inventory: SourceInventory,
) -> dict[str, Any]:
    """
    Update a weekly manifest using source inventory results.

    This function does not move or modify EML source files.
    """
    path = Path(manifest_path)
    manifest = load_weekly_manifest(path)

    manifest_group = manifest.get("source_group")

    if manifest_group != inventory.source_group:
        raise SourceInventoryError(
            "Inventory source group does not match manifest. "
            f"Inventory: {inventory.source_group}. "
            f"Manifest: {manifest_group}."
        )

    statuses_by_source = {
        source.source_id: source
        for source in inventory.sources
    }

    expected_sources = manifest.get(
        "expected_sources",
        [],
    )

    if not isinstance(expected_sources, list):
        raise SourceInventoryError(
            "'expected_sources' must be a list."
        )

    for expected_source in expected_sources:
        source_id = expected_source["source_id"]
        inventory_status = statuses_by_source.get(
            source_id
        )

        if inventory_status is None:
            expected_source["status"] = "MISSING"
            expected_source["matched_file"] = None
            expected_source["matched_files"] = []
            continue

        matched_files = list(
            inventory_status.matched_files
        )

        expected_source["status"] = (
            inventory_status.status
        )
        expected_source["matched_files"] = matched_files

        if len(matched_files) == 1:
            expected_source["matched_file"] = (
                matched_files[0]
            )
        else:
            expected_source["matched_file"] = None

    run_status, readiness_issues = (
        determine_inventory_readiness(inventory)
    )

    current_time = (
        datetime.now()
        .astimezone()
        .isoformat(timespec="seconds")
    )

    manifest["status"] = run_status

    manifest["source_inventory"] = {
        "scanned_directory": (
            inventory.scanned_directory
        ),
        "files_scanned": inventory.files_scanned,
        "configured_sources": (
            inventory.configured_sources
        ),
        "matched_files": inventory.matched_files,
        "review_files": inventory.review_files,
        "unconfigured_files": (
            inventory.unconfigured_files
        ),
        "duplicate_sources": (
            inventory.duplicate_sources
        ),
        "missing_required_sources": (
            inventory.missing_required_sources
        ),
        "readiness_issues": readiness_issues,
        "inventoried_at": current_time,
        "known_out_of_scope_files": (
            inventory.known_out_of_scope_files
        ),
    }

    manifest["inventory_items"] = [
        asdict(item)
        for item in inventory.items
    ]

    manifest["updated_at"] = current_time

    save_weekly_manifest(
        manifest_path=path,
        manifest=manifest,
    )

    return manifest