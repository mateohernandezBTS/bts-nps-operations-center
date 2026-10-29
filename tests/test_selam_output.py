"""CSV schema, summary/window partition and retained Markdown."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from engine.selam_aggregator import (
    aggregate_selam_manual_reviews,
    aggregate_selam_worklists,
)
from engine.selam_output import (
    CSV_COLUMNS,
    MANUAL_REVIEW_COLUMNS,
    generate_selam_outputs,
)
from tests.support.weekly_cases import IsolatedWeeklyCase, read_json


class SelamOutputTest(IsolatedWeeklyCase):
    def outputs(self, bundle: str = "complete_weekly") -> dict[str, Any]:
        path = self.prepare(bundle)
        self.process(path)
        aggregate_selam_worklists(path)
        aggregate_selam_manual_reviews(path)
        return generate_selam_outputs(path)

    def test_csv_schema_and_records(self) -> None:
        result = self.outputs()
        with self.assert_local(result["csv_path"]).open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            reader = csv.DictReader(stream)
            records = list(reader)
        self.assertEqual(reader.fieldnames, CSV_COLUMNS)
        self.assertEqual(len(records), 6)
        self.assertEqual(records, result["records"])
        self.assertEqual(
            [r["Session"] for r in records],
            [f"Fixture Session {i:03}" for i in range(1, 7)],
        )
        # NPS-002: current CSV omits invitation values/links.
        self.assertNotIn("survey_invitation_link", reader.fieldnames or [])

    def test_summary_and_manual_review_window(self) -> None:
        result = self.outputs("cross_source_duplicates")
        summary = result["weekly_summary"]
        self.assertEqual(read_json(self.assert_local(result["summary_path"])), summary)
        self.assertEqual(
            (
                summary["total_records"],
                summary["ready_records"],
                summary["duplicate_issues"],
            ),
            (10, 10, 1),
        )
        self.assertEqual(
            (summary["window_start"], summary["window_end"]),
            ("08/04/2026", "08/10/2026"),
        )
        self.assertEqual(
            (
                summary["manual_review_records"],
                summary["worklist_review_records"],
                summary["review_records"],
            ),
            (9, 0, 9),
        )
        with Path(result["manual_review_csv_path"]).open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            reader = csv.DictReader(stream)
            reviews = list(reader)
        self.assertEqual(reader.fieldnames, MANUAL_REVIEW_COLUMNS)
        self.assertEqual(len(reviews), 9)
        self.assertNotIn(
            "Fixture Session revenue outside", [r["project_name"] for r in reviews]
        )
        self.assertIn(
            "Fixture Session revenue inside", [r["project_name"] for r in reviews]
        )
        self.assertEqual(
            reviews,
            [
                {key: row.get(key, "") for key in MANUAL_REVIEW_COLUMNS}
                for row in result["manual_review_records"]
            ],
        )

    def test_retained_markdown(self) -> None:
        result = self.outputs()
        path = self.assert_local(result["markdown_path"])
        self.assertEqual(path.name, "selam_slack_ready.md")
        markdown = path.read_text(encoding="utf-8")
        self.assertEqual(markdown, result["markdown"])
        self.assertIn("# NPS Weekly Worklist \u2014 SELAM", markdown)
        for row in result["records"]:
            self.assertIn(row["Session"], markdown)
            self.assertIn("## " + row["Client"], markdown)
            self.assertIn("[Home](" + row["Link for Results"] + ")", markdown)
