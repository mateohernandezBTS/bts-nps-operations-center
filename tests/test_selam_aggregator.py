import json
from pathlib import Path

from engine.selam_aggregator import (
    aggregate_selam_worklists,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MANIFEST_PATH = (
    PROJECT_ROOT
    / "tests"
    / "output"
    / "weekly_orchestrator"
    / "NPS_WEEK_2026-07-28_2026-08-03"
    / "weekly_manifest.json"
)


def main() -> None:
    print("=" * 80)
    print("SELAM AGGREGATOR TEST")
    print("=" * 80)

    result = aggregate_selam_worklists(
        manifest_path=MANIFEST_PATH,
    )

    records = result["records"]
    issues = result[
        "duplicate_issues"
    ]
    summary = result["summary"]

    print("\nSUMMARY")
    print("-" * 80)
    print(
        f"Region: "
        f"{summary['region']}"
    )
    print(
        f"Processed sources: "
        f"{summary['processed_sources']}"
    )
    print(
        "Records before deduplication: "
        f"{summary['records_before_deduplication']}"
    )
    print(
        "Records after deduplication: "
        f"{summary['records_after_deduplication']}"
    )
    print(
        f"Duplicate issues: "
        f"{summary['duplicate_issues']}"
    )
    print(
        f"Clients: "
        f"{summary['clients']}"
    )
    print(
        f"Countries: "
        f"{summary['countries']}"
    )

    assert summary["region"] == "SELAM"
    assert summary[
        "processed_sources"
    ] == 3

    assert summary[
        "records_before_deduplication"
    ] == 12

    assert summary[
        "records_after_deduplication"
    ] == 12

    assert summary[
        "duplicate_issues"
    ] == 0

    assert len(records) == 12
    assert len(issues) == 0

    countries = {
        record["Country"]
        for record in records
    }

    assert countries == {
        "Brazil",
        "Mexico",
    }

    print("\nFIRST RECORDS")
    print("-" * 80)

    for record in records[:5]:
        print(
            f"{record['Client']} | "
            f"{record['Country']} | "
            f"{record['Date']} | "
            f"{record['Session']}"
        )

        assert record["Region"] == "SELAM"
        assert record["Weekly Run ID"] == (
            "NPS_WEEK_2026-07-28_2026-08-03"
        )
        assert record["Source ID"]
        assert record["Source Execution ID"]

    consolidated_path = Path(
        summary[
            "selam_consolidated_worklist_path"
        ]
    )

    assert consolidated_path.exists()

    with consolidated_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        saved_records = json.load(file)

    assert len(saved_records) == 12
    assert saved_records == records

    print("\nSaved SELAM worklist validated.")

    print("\n" + "=" * 80)
    print("SELAM AGGREGATOR TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()