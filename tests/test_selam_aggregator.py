"""Attribution, ordering, deduplication and persisted aggregation."""

from __future__ import annotations

from engine.selam_aggregator import (
    aggregate_selam_manual_reviews,
    aggregate_selam_worklists,
)
from tests.support.stage_cases import declarations
from tests.support.weekly_cases import IsolatedWeeklyCase, read_json


class SelamAggregatorTest(IsolatedWeeklyCase):
    def test_attribution_and_order(self) -> None:
        path = self.prepare()
        completed = self.process(path)
        result = aggregate_selam_worklists(path)
        records = result["records"]
        self.assertEqual(len(records), 6)
        self.assertEqual(result["duplicate_issues"], [])
        self.assertEqual(result["summary"]["processed_sources"], 3)
        self.assertEqual(
            [r["Session"] for r in records],
            [
                "Fixture Session 001",
                "Fixture Session 002",
                "Fixture Session 003",
                "Fixture Session 004",
                "Fixture Session 005",
                "Fixture Session 006",
            ],
        )
        executions = {
            s["source_id"]: s["execution_result"]["execution_id"]
            for s in completed["expected_sources"]
        }
        for row in records:
            self.assertEqual(row["Region"], "SELAM")
            self.assertEqual(row["Weekly Run ID"], completed["weekly_run_id"])
            self.assertEqual(row["Source ID"], "upcoming_" + row["Country"].lower())
            self.assertEqual(row["Source Execution ID"], executions[row["Source ID"]])

    def test_duplicate_ready_records(self) -> None:
        path = self.prepare("cross_source_duplicates")
        self.process(path)
        result = aggregate_selam_worklists(path)
        self.assertEqual(result["summary"]["records_before_deduplication"], 11)
        self.assertEqual(result["summary"]["records_after_deduplication"], 10)
        self.assertEqual(len(result["duplicate_issues"]), 1)
        issue = result["duplicate_issues"][0]
        self.assertEqual(
            (issue["original_source_id"], issue["duplicate_source_id"]),
            ("upcoming_argentina", "upcoming_brazil"),
        )
        self.assertEqual(
            issue["duplicate_key"],
            dict(
                project_id="FXT000000000001",
                date="8/4/2026",
                session="fixture session 001",
            ),
        )
        self.assertEqual(
            [
                r["Country"]
                for r in result["records"]
                if r["Session"] == "Fixture Session 001"
            ],
            ["Argentina"],
        )

    def test_review_aggregation_and_duplicate(self) -> None:
        path = self.prepare("cross_source_duplicates")
        self.process(path)
        result = aggregate_selam_manual_reviews(path)
        self.assertEqual(len(result["records"]), 10)
        self.assertEqual(len(result["duplicate_issues"]), 1)
        issue = result["duplicate_issues"][0]
        self.assertEqual(
            (issue["original_source_id"], issue["duplicate_source_id"]),
            ("upcoming_argentina", "upcoming_brazil"),
        )
        expected = {
            d["values"]["project_name"]
            for k, d in declarations().items()
            if (
                k.startswith("rule_revenue_admin_")
                or k in ("review_inside", "review_outside")
            )
        }
        self.assertEqual({r["project_name"] for r in result["records"]}, expected)
        for row in result["records"]:
            self.assertEqual(row["Record Type"], "MANUAL_REVIEW")
            self.assertEqual(row["decision"], "REVIEW")
            self.assertEqual(row["decision_code"], "REVENUE_ADMIN")

    def test_persistence(self) -> None:
        path = self.prepare()
        self.process(path)
        result = aggregate_selam_worklists(path)
        review = aggregate_selam_manual_reviews(path)
        summary = result["summary"]
        self.assertEqual(
            read_json(self.assert_local(summary["selam_consolidated_worklist_path"])),
            result["records"],
        )
        self.assertEqual(
            read_json(self.assert_local(summary["selam_consolidation_issues_path"])), []
        )
        saved = read_json(path)
        self.assertEqual(
            read_json(self.assert_local(saved["selam_aggregation"]["summary_path"])),
            summary,
        )
        self.assertEqual(
            read_json(self.assert_local(review["summary"]["selam_manual_review_path"])),
            [],
        )
        self.assertEqual(saved["status"], "COMPLETED")
