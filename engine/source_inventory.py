from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from engine.report_detection import (
    ReportContext,
    detect_pending_reports,
    load_detection_config,
)
from engine.source_config import (
    get_enabled_sources,
    load_source_configuration,
)


class SourceInventoryError(Exception):
    """Raised when the source inventory cannot be generated."""


@dataclass
class InventoryItem:
    source_file: str
    source_path: str
    subject: str
    sender_email: str
    received_at: str
    detected_country: str
    detected_report_type: str
    detection_status: str
    detection_issues: list[str]
    matched_source_id: str | None
    inventory_status: str


@dataclass
class SourceStatus:
    source_id: str
    country: str
    report_type: str
    required: bool
    status: str
    matched_files: list[str]


@dataclass
class SourceInventory:
    source_group: str
    scanned_directory: str
    files_scanned: int
    configured_sources: int
    matched_files: int
    known_out_of_scope_files: int
    review_files: int
    unconfigured_files: int
    duplicate_sources: int
    missing_required_sources: int
    items: list[InventoryItem]
    sources: list[SourceStatus]


def normalize_value(value: Any) -> str:
    """
    Normalize configuration and detector values for matching.

    Treat spaces, underscores, and hyphens as equivalent.

    Examples:
        Upcoming -> upcoming
        Last Results -> last results
        last_results -> last results
        last-results -> last results
    """
    if value is None:
        return ""

    normalized = (
        str(value)
        .strip()
        .casefold()
        .replace("_", " ")
        .replace("-", " ")
    )

    return " ".join(
        normalized.split()
    )


def build_source_lookup(
    source_group: str,
) -> dict[tuple[str, str], dict[str, Any]]:
    """
    Build a lookup using normalized country and report type.

    The number of configured sources is dynamic.
    """
    configured_sources = get_enabled_sources(source_group)

    lookup: dict[
        tuple[str, str],
        dict[str, Any],
    ] = {}

    for source in configured_sources:
        key = (
            normalize_value(source["country"]),
            normalize_value(source["report_type"]),
        )

        if key in lookup:
            first_source = lookup[key]["source_id"]

            raise SourceInventoryError(
                "Two enabled sources use the same country and "
                f"report type: {first_source} and "
                f"{source['source_id']}."
            )

        lookup[key] = source

    return lookup

def build_global_source_lookup(
) -> dict[tuple[str, str], dict[str, Any]]:
    """
    Build a lookup containing every enabled source
    from every enabled source group.
    """
    configuration = load_source_configuration()

    source_groups = configuration[
        "source_groups"
    ]

    lookup: dict[
        tuple[str, str],
        dict[str, Any],
    ] = {}

    for group_id, group in source_groups.items():
        if not group.get("enabled", False):
            continue

        for source in group.get("sources", []):
            if not source.get("enabled", False):
                continue

            key = (
                normalize_value(source["country"]),
                normalize_value(source["report_type"]),
            )

            if key in lookup:
                previous = lookup[key]

                raise SourceInventoryError(
                    "Two enabled sources use the same country "
                    "and report type across source groups: "
                    f"{previous['source_id']} and "
                    f"{source['source_id']}."
                )

            lookup[key] = {
                **source,
                "source_group": group_id,
            }

    return lookup


def match_context_to_source(
    context: ReportContext,
    source_lookup: dict[
        tuple[str, str],
        dict[str, Any],
    ],
    global_source_lookup: dict[
        tuple[str, str],
        dict[str, Any],
    ],
) -> tuple[str | None, str]:
    """
    Match a detected report against the selected source group.

    Returns:
        matched_source_id
        inventory_status
    """
    if context.detection_status != "DETECTED":
        return None, "DETECTION_REVIEW"

    key = (
        normalize_value(context.country),
        normalize_value(context.report_type),
    )

    matched_source = source_lookup.get(key)

    if matched_source is not None:
        return matched_source["source_id"], "MATCHED"

    known_source = global_source_lookup.get(key)

    if known_source is not None:
        return None, "KNOWN_OUT_OF_SCOPE"

    return None, "UNKNOWN_REPORT"


def context_to_inventory_item(
    context: ReportContext,
    matched_source_id: str | None,
    inventory_status: str,
) -> InventoryItem:
    return InventoryItem(
        source_file=context.source_file,
        source_path=context.source_path,
        subject=context.subject,
        sender_email=context.sender_email,
        received_at=context.received_at,
        detected_country=context.country,
        detected_report_type=context.report_type,
        detection_status=context.detection_status,
        detection_issues=list(
            context.detection_issues
        ),
        matched_source_id=matched_source_id,
        inventory_status=inventory_status,
    )


def build_source_statuses(
    source_group: str,
    items: list[InventoryItem],
) -> list[SourceStatus]:
    """
    Build one status record for each configured source.
    """
    configured_sources = get_enabled_sources(source_group)

    files_by_source: dict[str, list[str]] = defaultdict(list)

    for item in items:
        if item.matched_source_id:
            files_by_source[
                item.matched_source_id
            ].append(item.source_file)

    statuses: list[SourceStatus] = []

    for source in configured_sources:
        source_id = source["source_id"]
        matched_files = files_by_source.get(
            source_id,
            [],
        )

        if len(matched_files) == 0:
            status = "MISSING"
        elif len(matched_files) == 1:
            status = "RECEIVED"
        else:
            status = "DUPLICATE"

        statuses.append(
            SourceStatus(
                source_id=source_id,
                country=source["country"],
                report_type=source["report_type"],
                required=bool(source["required"]),
                status=status,
                matched_files=matched_files,
            )
        )

    return statuses


def build_source_inventory(
    pending_directory: Path | str,
    source_group: str = "weekly_upcoming",
) -> SourceInventory:
    """
    Scan EML files and associate them with configured sources.

    This function does not move or modify source files.
    """
    directory = Path(pending_directory)

    if not directory.exists():
        raise SourceInventoryError(
            f"Inventory directory does not exist: {directory}"
        )

    if not directory.is_dir():
        raise SourceInventoryError(
            f"Inventory path is not a directory: {directory}"
        )

    source_lookup = build_source_lookup(
        source_group
    )

    global_source_lookup = (
        build_global_source_lookup()
    )

    detection_config = load_detection_config()

    contexts = detect_pending_reports(
        pending_directory=directory,
        config=detection_config,
    )

    items: list[InventoryItem] = []

    for context in contexts:
        matched_source_id, inventory_status = (
            match_context_to_source(
                context=context,
                source_lookup=source_lookup,
                global_source_lookup=(
                    global_source_lookup
                ),
            )
        )

        items.append(
            context_to_inventory_item(
                context=context,
                matched_source_id=matched_source_id,
                inventory_status=inventory_status,
            )
        )

    source_statuses = build_source_statuses(
        source_group=source_group,
        items=items,
    )

    matched_files = sum(
        1
        for item in items
        if item.inventory_status == "MATCHED"
    )

    known_out_of_scope_files = sum(
        1
        for item in items
        if item.inventory_status
        == "KNOWN_OUT_OF_SCOPE"
    )

    review_files = sum(
        1
        for item in items
        if item.inventory_status
        == "DETECTION_REVIEW"
    )

    unconfigured_files = sum(
        1
        for item in items
        if item.inventory_status
        == "UNKNOWN_REPORT"
    )

    duplicate_sources = sum(
        1
        for source in source_statuses
        if source.status == "DUPLICATE"
    )

    missing_required_sources = sum(
        1
        for source in source_statuses
        if source.required
        and source.status == "MISSING"
    )

    return SourceInventory(
        source_group=source_group,
        scanned_directory=str(directory),
        files_scanned=len(contexts),
        configured_sources=len(source_statuses),
        matched_files=matched_files,
        review_files=review_files,
        unconfigured_files=unconfigured_files,
        duplicate_sources=duplicate_sources,
        missing_required_sources=(
            missing_required_sources
        ),
        items=items,
        sources=source_statuses,
        known_out_of_scope_files=(
            known_out_of_scope_files
        ),
    )


def inventory_to_dict(
    inventory: SourceInventory,
) -> dict[str, Any]:
    """
    Convert the inventory to a JSON-compatible dictionary.
    """
    return asdict(inventory)