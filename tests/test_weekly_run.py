import json
import shutil
from pathlib import Path

from engine.weekly_run import (
    WeeklyRunError,
    build_weekly_run,
    create_weekly_run,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_OUTPUT_ROOT = (
    PROJECT_ROOT / "tests" / "output" / "weekly_runs"
)


def print_run_summary(run) -> None:
    print(f"Weekly Run ID: {run.weekly_run_id}")
    print(f"Reference date: {run.reference_date}")
    print(f"Execution weekday: {run.execution_weekday}")
    print(f"Window start: {run.window_start}")
    print(f"Window end: {run.window_end}")
    print(f"Window length: {run.window_length_days}")
    print(f"Status: {run.status}")
    print(f"Expected sources: {len(run.expected_sources)}")
    print(f"Required sources: {len(run.required_sources)}")


def main() -> None:
    print("=" * 80)
    print("CONFIGURABLE WEEKLY RUN TEST")
    print("=" * 80)

    if TEST_OUTPUT_ROOT.exists():
        shutil.rmtree(TEST_OUTPUT_ROOT)

    print("\n1. BUILD DEFAULT WEEKLY RUN")
    print("-" * 80)

    run = build_weekly_run(
        reference_date_text="7/27/2026",
        output_root=TEST_OUTPUT_ROOT,
    )

    print_run_summary(run)

    assert run.weekly_run_id == (
        "NPS_WEEK_2026-07-28_2026-08-03"
    )
    assert run.reference_date == "07/27/2026"
    assert run.execution_weekday == "monday"
    assert run.window_start == "07/28/2026"
    assert run.window_end == "08/03/2026"
    assert run.window_length_days == 7
    assert len(run.expected_sources) == 3
    assert len(run.required_sources) == 3

    print("\n2. CREATE MANIFEST")
    print("-" * 80)

    created_run, manifest_path = create_weekly_run(
        reference_date_text="7/27/2026",
        output_root=TEST_OUTPUT_ROOT,
    )

    print(f"Manifest created: {manifest_path}")
    assert manifest_path.exists()

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    assert manifest["weekly_run_id"] == (
        created_run.weekly_run_id
    )
    assert manifest["execution_weekday"] == "monday"
    assert manifest["window_length_days"] == 7
    assert manifest["status"] == "INITIALIZED"

    for source in manifest["expected_sources"]:
        assert source["status"] == "MISSING"
        assert source["matched_file"] is None

    print("Manifest validated.")

    print("\n3. DUPLICATE RUN PROTECTION")
    print("-" * 80)

    try:
        create_weekly_run(
            reference_date_text="7/27/2026",
            output_root=TEST_OUTPUT_ROOT,
        )
    except WeeklyRunError as exc:
        print(f"Duplicate correctly rejected: {exc}")
    else:
        raise AssertionError(
            "Existing weekly run should have been rejected."
        )

    print("\n4. INVALID EXECUTION WEEKDAY")
    print("-" * 80)

    try:
        build_weekly_run(
            reference_date_text="7/29/2026",
            output_root=TEST_OUTPUT_ROOT,
        )
    except WeeklyRunError as exc:
        print(f"Invalid weekday correctly rejected: {exc}")
    else:
        raise AssertionError(
            "Wednesday should be rejected while Monday "
            "is configured."
        )

    print("\n5. EXPECTED SOURCES")
    print("-" * 80)

    for source in run.expected_sources:
        print(
            f"{source['source_id']} | "
            f"{source['country']} | "
            f"{source['report_type']} | "
            f"{source['status']}"
        )

    print("\n" + "=" * 80)
    print("ALL CONFIGURABLE WEEKLY RUN TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()