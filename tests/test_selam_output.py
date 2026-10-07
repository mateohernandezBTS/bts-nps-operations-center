import csv
import json
from pathlib import Path

from engine.selam_output import (
    CSV_COLUMNS,
    generate_selam_outputs,
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
    print("SELAM OUTPUT TEST")
    print("=" * 80)

    result = generate_selam_outputs(
        manifest_path=MANIFEST_PATH,
    )

    summary = result[
        "weekly_summary"
    ]

    print("\nSUMMARY")
    print("-" * 80)
    print(
        f"Region: {summary['region']}"
    )
    print(
        f"Weekly Run: "
        f"{summary['weekly_run_id']}"
    )
    print(
        f"Total records: "
        f"{summary['total_records']}"
    )
    print(
        f"Clients: "
        f"{summary['clients']}"
    )
    print(
        f"Countries with records: "
        f"{summary['countries_with_records']}"
    )
    print(
        f"Ready records: "
        f"{summary['ready_records']}"
    )
    print(
        f"Review records: "
        f"{summary['review_records']}"
    )
    print(
        f"Duplicate issues: "
        f"{summary['duplicate_issues']}"
    )

    assert summary["region"] == "SELAM"
    assert summary["total_records"] == 12
    assert summary["clients"] == 8
    assert summary[
        "countries_with_records"
    ] == 2
    assert summary["ready_records"] == 12
    assert summary["review_records"] == 0
    assert summary["duplicate_issues"] == 0

    print("\nFILES")
    print("-" * 80)

    for file_path in [
        result["csv_path"],
        result["markdown_path"],
        result["summary_path"],
    ]:
        print(file_path)
        assert Path(file_path).exists()

    print("\nCSV VALIDATION")
    print("-" * 80)

    with Path(result["csv_path"]).open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)
        csv_records = list(reader)

    print(f"CSV records: {len(csv_records)}")

    assert reader.fieldnames == CSV_COLUMNS
    assert len(csv_records) == 12

    print("\nMARKDOWN VALIDATION")
    print("-" * 80)

    markdown = Path(
        result["markdown_path"]
    ).read_text(
        encoding="utf-8"
    )

    required_clients = {
        "B3",
        "Engie Brazil",
        "FedEx",
        "Itau",
        "Mattel Mexico",
        "RD Saúde",
        "Vila Nova",
        "Vivo Brazil",
    }

    for client in required_clients:
        assert f"## {client}" in markdown

    assert (
        "# NPS Weekly Worklist — SELAM"
        in markdown
    )

    assert (
        "[Home](https://mybts.my.site.com/"
        in markdown
    )

    print("Client groups and links validated.")

    print("\nSUMMARY FILE VALIDATION")
    print("-" * 80)

    with Path(result["summary_path"]).open(
        "r",
        encoding="utf-8",
    ) as file:
        saved_summary = json.load(file)

    assert saved_summary == summary

    print(
        "SELAM weekly summary validated."
    )

    print("\n" + "=" * 80)
    print("SELAM OUTPUT TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()