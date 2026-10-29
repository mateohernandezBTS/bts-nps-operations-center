"""Ten semantic golden master contracts; committed candidates remain PR-gated."""

from __future__ import annotations

import copy
import json
import os
import unittest

from bs4 import BeautifulSoup

from engine.paths import repository_path
from tests.support.pipeline_harness import (
    MALFORMED_SCENARIOS,
    SCENARIOS,
    run_scenario,
)
from tests.support.snapshot_candidates import (
    SNAPSHOT_ROOT,
    compare,
    provenance,
    read_snapshot,
    write_candidates,
)
from tests.support.snapshot_projection import Projection, json_text


class PipelineGoldenMasterTest(unittest.TestCase):
    actual: dict[str, dict[str, str]]
    export_candidates: bool

    @classmethod
    def setUpClass(cls) -> None:
        cls.actual = {scenario: run_scenario(scenario) for scenario in SCENARIOS}
        cls.export_candidates = os.environ.get("BTS_EXPORT_GOLDEN_CANDIDATES") == "1"
        if cls.export_candidates:
            write_candidates(cls.actual)

    def assert_snapshot(self, scenario: str) -> dict[str, str]:
        actual = self.actual[scenario]
        if not self.export_candidates:
            compare(read_snapshot(scenario), actual)
        return actual

    def test_complete_pipeline(self) -> None:
        files = self.assert_snapshot("complete_weekly")
        summary = json.loads(files["summary.json"])
        self.assertEqual((summary["ready_records"], summary["review_records"]), (6, 0))
        self.assertEqual(
            [s["name"] for s in json.loads(files["excel_cells.json"])],
            ["Home", "Worklist", "Revision Manual", "Manifest", "Issues"],
        )
        records = json.loads(files["selam_consolidated.json"])
        csvs = json.loads(files["weekly_csv.json"])
        worklist = next(v for k, v in csvs.items() if "manual" not in k)
        self.assertEqual(worklist["records"], records)
        workbook = json.loads(files["excel_cells.json"])[1]
        cells = {c["coordinate"]: c for c in workbook["cells"]}
        for index, row in enumerate(records, 4):
            self.assertEqual(cells[f"C{index}"]["value"], row["Session"])
            self.assertEqual(cells[f"J{index}"]["hyperlink"], row["Link for Results"])
            self.assertEqual(cells[f"L{index}"]["hyperlink"], row["Project URL"])

    def test_parser_equivalence(self) -> None:
        files = self.assert_snapshot("parser_equivalence")
        raw = json.loads(files["raw.json"])
        for name in ("parser_Brazil_sum_headers", "parser_Brazil_forwarded_multipart"):
            self.assertEqual(raw[name], raw["parser_Brazil_plain_headers"])
        self.assertEqual(
            raw["parser_Argentina_invitation_both"][0]["survey_invitation_link"],
            "https://example.invalid/invitation/last",
        )

    def test_rule_review_matrix(self) -> None:
        files = self.assert_snapshot("review_and_boundaries")
        classified = json.loads(files["classified.json"])
        self.assertEqual(sum(map(len, classified.values())), 85)
        review = json.loads(files["selam_manual_review.json"])
        self.assertTrue(review)
        self.assertTrue(all(r["decision"] == "REVIEW" for r in review))

    def test_window_edges(self) -> None:
        files = self.assert_snapshot("review_and_boundaries")
        rows = json.loads(files["worklist.json"])["upcoming_mexico_1"]
        dates = {r["Date"] for r in rows}
        self.assertTrue({"8/4/2026", "8/10/2026"} <= dates)
        outside = json.loads(files["outside_window.json"])["upcoming_mexico_1"]
        self.assertEqual([r["start_date"] for r in outside], ["8/3/2026", "8/11/2026"])
        html = BeautifulSoup(files["slack.html"], "html.parser")
        # NPS-003: the separate-email warning is still inside a copied client table.
        warning = html.select_one("tr.separate-email-warning")
        self.assertIsNotNone(warning)
        assert warning is not None
        self.assertIsNotNone(warning.find_parent("table"))

    def test_source_blocking(self) -> None:
        for scenario in (
            "missing_argentina",
            "missing_brazil",
            "missing_mexico",
            "duplicate_source",
        ):
            with self.subTest(scenario=scenario):
                files = self.assert_snapshot(scenario)
                operation = json.loads(files["operation.json"])
                self.assertEqual(operation["status"], "BLOCKED")
                self.assertFalse(operation["success"])
                self.assertNotIn("excel_cells.json", files)
        for scenario in MALFORMED_SCENARIOS:
            with self.subTest(scenario=scenario):
                files = self.assert_snapshot(scenario)
                contexts = json.loads(files["execution_manifest.json"])
                self.assertEqual(
                    next(iter(contexts.values()))["execution_status"], "FAILED"
                )
                self.assertNotIn("excel_cells.json", files)

    def test_cross_source_duplicates(self) -> None:
        files = self.assert_snapshot("cross_source_duplicates")
        summary = json.loads(files["summary.json"])
        self.assertEqual(
            (summary["ready_records"], summary["duplicate_issues"]), (10, 1)
        )
        self.assertEqual(len(json.loads(files["manual_review_issues.json"])), 1)

    def test_partial_failure(self) -> None:
        files = self.assert_snapshot("partial_failure")
        # NPS-001: partial failure reports success and omits Brazil from outputs.
        self.assertEqual(
            json.loads(files["operation.json"]),
            {
                "success": True,
                "status": "COMPLETED_WITH_REVIEW",
                "issues": [],
            },
        )
        manifest = json.loads(files["weekly_manifest.json"])
        self.assertEqual(
            [s["status"] for s in manifest["expected_sources"]],
            ["PROCESSED", "FAILED", "PROCESSED"],
        )
        self.assertEqual(
            json.loads(files["summary.json"])["records_by_country"],
            {"Argentina": 2, "Mexico": 2},
        )

    def test_canonicalization_repeatability(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                compare(self.actual[scenario], run_scenario(scenario))

    def test_mutation_detection(self) -> None:
        root_a = repository_path(".tmp", "projection-a")
        root_b = repository_path(".tmp", "projection-b")
        first_id, second_id = "20260803_090000_abcdef", "20260804_100000_123456"
        first = Projection(root_a, {first_id: "<EXECUTION:upcoming_argentina_1>"})
        second = Projection(root_b, {second_id: "<EXECUTION:upcoming_argentina_1>"})
        record = {
            "Date": "8/4/2026",
            "decision": "ELIGIBLE",
            "Project URL": "https://example.invalid/project/FXT000000000001",
            "execution_id": first_id,
            "run_directory": str(root_a / "runs" / first_id),
            "started_at": "2026-08-03T09:00:00",
            "finished_at": "2026-08-03T09:00:01",
        }
        expected = {"record.json": json_text(first.value(record))}
        for field, value in (
            ("Date", "8/11/2026"),
            ("decision", "EXCLUDED"),
            ("Project URL", "https://example.invalid/changed"),
        ):
            changed = copy.deepcopy(record)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                compare(expected, {"record.json": json_text(first.value(changed))})
        runtime = {
            **record,
            "execution_id": second_id,
            "run_directory": str(root_b / "runs" / second_id),
            "started_at": "2026-08-04T10:00:00",
            "finished_at": "2026-08-04T10:00:01",
        }
        compare(expected, {"record.json": json_text(second.value(runtime))})
        with self.assertRaises(AssertionError):
            first.value({"run_directory": str(repository_path())})
        with self.assertRaises(AssertionError):
            first.value({"started_at": "invalid"})
        with self.assertRaises(AssertionError):
            first.value(
                {
                    "started_at": record["finished_at"],
                    "finished_at": record["started_at"],
                }
            )

    def test_provenance(self) -> None:
        current = provenance(self.actual)
        if self.export_candidates:
            return
        stored = json.loads(
            (SNAPSHOT_ROOT / "provenance.json").read_text(encoding="utf-8")
        )
        self.assertEqual(stored["input_sha256"], current["input_sha256"])
        self.assertEqual(stored["candidate_sha256"], current["candidate_sha256"])
        approval = (SNAPSHOT_ROOT / "APPROVAL.md").read_text(encoding="utf-8")
        self.assertTrue("Status: PENDING" in approval or "Status: APPROVED" in approval)
