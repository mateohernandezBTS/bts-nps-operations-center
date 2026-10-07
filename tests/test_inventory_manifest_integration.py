import json
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
    / "complete_upcoming"
)

TEST_OUTPUT_ROOT = (
    PROJECT_ROOT
    / "tests"
    / "output"
    / "inventory_manifest_integration"
)


def main() -> None:
    print("=" * 80)
    print("INVENTORY + WEEKLY MANIFEST INTEGRATION TEST")
    print("=" * 80)

    if TEST_OUTPUT_ROOT.exists():
        shutil.rmtree(TEST_OUTPUT_ROOT)

    print("\n1. CREATE WEEKLY RUN")
    print("-" * 80)

    run, manifest_path = create_weekly_run(
        reference_date_text="7/27/2026",
        source_group="weekly_upcoming",
        output_root=TEST_OUTPUT_ROOT,
    )

    print(f"Weekly Run ID: {run.weekly_run_id}")
    print(f"Initial status: {run.status}")
    print(f"Manifest: {manifest_path}")

    assert run.status == "INITIALIZED"

    print("\n2. BUILD SOURCE INVENTORY")
    print("-" * 80)

    inventory = build_source_inventory(
        pending_directory=SCENARIO_DIRECTORY,
        source_group="weekly_upcoming",
    )

    print(f"Files scanned: {inventory.files_scanned}")
    print(f"Matched files: {inventory.matched_files}")
    print(
        f"Missing required sources: "
        f"{inventory.missing_required_sources}"
    )
    print(
        f"Duplicate sources: "
        f"{inventory.duplicate_sources}"
    )

    assert inventory.files_scanned == 3
    assert inventory.matched_files == 3
    assert inventory.missing_required_sources == 0
    assert inventory.duplicate_sources == 0

    print("\n3. UPDATE WEEKLY MANIFEST")
    print("-" * 80)

    updated_manifest = (
        update_weekly_manifest_from_inventory(
            manifest_path=manifest_path,
            inventory=inventory,
        )
    )

    print(
        f"Updated status: "
        f"{updated_manifest['status']}"
    )

    assert updated_manifest["status"] == "READY_TO_PROCESS"

    for source in updated_manifest["expected_sources"]:
        print(
            f"{source['source_id']} | "
            f"{source['status']} | "
            f"{source['matched_file']}"
        )

        assert source["status"] == "RECEIVED"
        assert source["matched_file"] is not None
        assert len(source["matched_files"]) == 1

    inventory_summary = updated_manifest[
        "source_inventory"
    ]

    assert inventory_summary["files_scanned"] == 3
    assert inventory_summary["matched_files"] == 3
    assert inventory_summary[
        "missing_required_sources"
    ] == 0
    assert inventory_summary["readiness_issues"] == []

    print("\n4. RELOAD MANIFEST FROM DISK")
    print("-" * 80)

    with manifest_path.open("r", encoding="utf-8") as file:
        saved_manifest = json.load(file)

    assert saved_manifest["status"] == "READY_TO_PROCESS"
    assert len(saved_manifest["inventory_items"]) == 3

    print("Saved manifest validated.")

    print("\n" + "=" * 80)
    print("INTEGRATION TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()