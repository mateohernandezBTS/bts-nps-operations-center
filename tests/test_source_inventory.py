from pathlib import Path

from engine.source_inventory import (
    build_source_inventory,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_INPUT_DIRECTORY = (
    PROJECT_ROOT
    / "tests"
    / "inventory_scenarios"
    / "six_real_reports"
)


def main() -> None:
    print("=" * 80)
    print("SOURCE INVENTORY TEST")
    print("=" * 80)

    inventory = build_source_inventory(
        pending_directory=TEST_INPUT_DIRECTORY,
        source_group="weekly_upcoming",
    )

    print("\nSUMMARY")
    print("-" * 80)
    print(
        f"Directory: {inventory.scanned_directory}"
    )
    print(
        f"Files scanned: {inventory.files_scanned}"
    )
    print(
        f"Configured sources: "
        f"{inventory.configured_sources}"
    )
    print(
        "Known out of scope: "
        f"{inventory.known_out_of_scope_files}"
    )
    print(
        f"Matched files: {inventory.matched_files}"
    )
    print(
        f"Detection review: "
        f"{inventory.review_files}"
    )
    print(
        f"Unconfigured reports: "
        f"{inventory.unconfigured_files}"
    )
    print(
        f"Duplicate sources: "
        f"{inventory.duplicate_sources}"
    )
    print(
        f"Missing required sources: "
        f"{inventory.missing_required_sources}"
    )

    print("\nFILES")
    print("-" * 80)

    for item in inventory.items:
        print(f"File: {item.source_file}")
        print(
            f"Detected: "
            f"{item.detected_country or '[NO COUNTRY]'} / "
            f"{item.detected_report_type or '[NO TYPE]'}"
        )
        print(
            f"Detection status: "
            f"{item.detection_status}"
        )
        print(
            f"Matched source: "
            f"{item.matched_source_id or '[NONE]'}"
        )
        print(
            f"Inventory status: "
            f"{item.inventory_status}"
        )

        if item.detection_issues:
            print(
                "Issues: "
                + " | ".join(
                    item.detection_issues
                )
            )

        print()

    print("CONFIGURED SOURCES")
    print("-" * 80)

    for source in inventory.sources:
        files = (
            ", ".join(source.matched_files)
            if source.matched_files
            else "[NONE]"
        )

        print(
            f"{source.source_id} | "
            f"{source.country} | "
            f"{source.report_type} | "
            f"{source.status} | "
            f"{files}"
        )

    assert inventory.files_scanned == len(
        list(TEST_INPUT_DIRECTORY.glob("*.eml"))
    )

    assert inventory.configured_sources == 3

    assert (
        inventory.matched_files
        + inventory.known_out_of_scope_files
        + inventory.review_files
        + inventory.unconfigured_files
        == inventory.files_scanned
    )

    print("\n" + "=" * 80)
    print("SOURCE INVENTORY TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()