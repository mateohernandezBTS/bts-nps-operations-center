import shutil
from pathlib import Path

from engine.source_inventory import (
    build_source_inventory,
)
from engine.weekly_manifest import (
    update_weekly_manifest_from_inventory,
)
from engine.weekly_run import create_weekly_run


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCENARIO_DIRECTORY = (
    PROJECT_ROOT
    / "tests"
    / "inventory_scenarios"
    / "six_real_reports"
)

TEST_OUTPUT_ROOT = (
    PROJECT_ROOT
    / "tests"
    / "output"
    / "six_reports_manifest"
)


def main() -> None:
    print("=" * 80)
    print("SIX REPORTS MANIFEST TEST")
    print("=" * 80)

    if TEST_OUTPUT_ROOT.exists():
        shutil.rmtree(TEST_OUTPUT_ROOT)

    run, manifest_path = create_weekly_run(
        reference_date_text="7/27/2026",
        source_group="weekly_upcoming",
        output_root=TEST_OUTPUT_ROOT,
    )

    inventory = build_source_inventory(
        pending_directory=SCENARIO_DIRECTORY,
        source_group="weekly_upcoming",
    )

    updated_manifest = (
        update_weekly_manifest_from_inventory(
            manifest_path=manifest_path,
            inventory=inventory,
        )
    )

    print(f"Files scanned: {inventory.files_scanned}")
    print(f"Matched files: {inventory.matched_files}")
    print(
        "Known out of scope: "
        f"{inventory.known_out_of_scope_files}"
    )
    print(
        "Unconfigured reports: "
        f"{inventory.unconfigured_files}"
    )
    print(
        "Missing required sources: "
        f"{inventory.missing_required_sources}"
    )
    print(
        f"Final manifest status: "
        f"{updated_manifest['status']}"
    )

    assert inventory.files_scanned == 6
    assert inventory.matched_files == 3
    assert inventory.known_out_of_scope_files == 3
    assert inventory.unconfigured_files == 0
    assert inventory.missing_required_sources == 0
    assert updated_manifest["status"] == "READY_TO_PROCESS"

    source_inventory = updated_manifest[
        "source_inventory"
    ]

    assert source_inventory[
        "known_out_of_scope_files"
    ] == 3

    assert source_inventory[
        "readiness_issues"
    ] == []

    print("\nEXPECTED SOURCES")
    print("-" * 80)

    for source in updated_manifest[
        "expected_sources"
    ]:
        print(
            f"{source['source_id']} | "
            f"{source['status']} | "
            f"{source['matched_file']}"
        )

        assert source["status"] == "RECEIVED"

    print("\n" + "=" * 80)
    print("SIX REPORTS MANIFEST TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()