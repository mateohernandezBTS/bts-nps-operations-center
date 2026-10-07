import json
import shutil
from pathlib import Path

from engine.source_inventory import (
    build_source_inventory,
)
from engine.weekly_manifest import (
    update_weekly_manifest_from_inventory,
)
from engine.weekly_orchestrator import (
    process_weekly_run,
)
from engine.weekly_run import create_weekly_run

from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SOURCE_SCENARIO = (
    PROJECT_ROOT
    / "tests"
    / "inventory_scenarios"
    / "complete_upcoming"
)

RUNTIME_DIRECTORY = (
    PROJECT_ROOT
    / "tests"
    / "runtime"
    / f"weekly_orchestrator_{uuid4().hex[:8]}"
)

TEST_OUTPUT_ROOT = (
    PROJECT_ROOT
    / "tests"
    / "output"
    / "weekly_orchestrator"
)


def prepare_runtime_directory() -> None:
    """
    Create an isolated runtime directory for this test run.

    A unique directory is used to avoid OneDrive or Windows
    file-locking issues when deleting previous test folders.
    """
    RUNTIME_DIRECTORY.mkdir(
        parents=True,
        exist_ok=False,
    )

    for source_file in SOURCE_SCENARIO.glob("*.eml"):
        shutil.copy2(
            source_file,
            RUNTIME_DIRECTORY / source_file.name,
        )


def main() -> None:
    print("=" * 80)
    print("WEEKLY ORCHESTRATOR TEST")
    print("=" * 80)

    prepare_runtime_directory()

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

    print("\n2. INVENTORY RUNTIME SOURCES")
    print("-" * 80)

    inventory = build_source_inventory(
        pending_directory=RUNTIME_DIRECTORY,
        source_group="weekly_upcoming",
    )

    print(f"Files scanned: {inventory.files_scanned}")
    print(f"Matched files: {inventory.matched_files}")
    print(
        "Missing required sources: "
        f"{inventory.missing_required_sources}"
    )

    assert inventory.files_scanned == 3
    assert inventory.matched_files == 3
    assert inventory.missing_required_sources == 0

    print("\n3. UPDATE MANIFEST")
    print("-" * 80)

    ready_manifest = (
        update_weekly_manifest_from_inventory(
            manifest_path=manifest_path,
            inventory=inventory,
        )
    )

    print(f"Status: {ready_manifest['status']}")
    assert ready_manifest["status"] == "READY_TO_PROCESS"

    print("\n4. PROCESS WEEKLY RUN")
    print("-" * 80)

    completed_manifest = process_weekly_run(
        manifest_path=manifest_path,
        stop_on_error=False,
    )

    print(
        f"Final status: "
        f"{completed_manifest['status']}"
    )

    summary = completed_manifest[
        "processing_summary"
    ]

    print(
        f"Configured sources: "
        f"{summary['configured_sources']}"
    )
    print(
        f"Processed sources: "
        f"{summary['processed_sources']}"
    )
    print(
        f"Failed sources: "
        f"{summary['failed_sources']}"
    )

    assert completed_manifest["status"] == "COMPLETED"
    assert summary["configured_sources"] == 3
    assert summary["processed_sources"] == 3
    assert summary["failed_sources"] == 0

    print("\n5. SOURCE RESULTS")
    print("-" * 80)

    expected_counts = {
        "upcoming_argentina": 46,
        "upcoming_brazil": 83,
        "upcoming_mexico": 110,
    }

    for source in completed_manifest[
        "expected_sources"
    ]:
        result = source["execution_result"]

        print(
            f"{source['source_id']} | "
            f"{source['status']} | "
            f"{result['execution_id']} | "
            f"{result['country']}"
        )

        assert source["status"] == "PROCESSED"
        assert result is not None
        assert result["status"] == "COMPLETED"
        assert Path(result["run_directory"]).exists()
        assert Path(result["worklist_path"]).exists()
        assert Path(
            result["execution_summary_path"]
        ).exists()

        raw_count = result["summary"][
            "counts"
        ]["raw_records"]

        assert raw_count == expected_counts[
            source["source_id"]
        ]

    print("\n6. VERIFY RUNTIME FILES MOVED")
    print("-" * 80)

    remaining_files = list(
        RUNTIME_DIRECTORY.glob("*.eml")
    )

    print(
        f"Remaining EML files: "
        f"{len(remaining_files)}"
    )

    assert len(remaining_files) == 0

    print("\n7. RELOAD SAVED MANIFEST")
    print("-" * 80)

    with manifest_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        saved_manifest = json.load(file)

    assert saved_manifest["status"] == "COMPLETED"
    assert saved_manifest[
        "processing_summary"
    ]["processed_sources"] == 3

    print("Saved manifest validated.")

    print("\n" + "=" * 80)
    print("WEEKLY ORCHESTRATOR TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()