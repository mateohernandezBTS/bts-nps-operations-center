"""Current classification matrices, including known defects."""

from __future__ import annotations

import unittest
from typing import Any

from engine.stages.business_rules import (
    apply_business_rules,
    load_business_rules_config,
)
from engine.stages.normalize import normalize_records
from tests.support.stage_cases import classification_rows, declarations, parsed_rows


class BusinessRulesTest(unittest.TestCase):
    def classify(self, keys: list[str]) -> dict[str, dict[str, Any]]:
        rows = classification_rows()
        normalized, _ = normalize_records([rows[key] for key in keys])
        result = apply_business_rules(normalized)
        self.assertEqual(
            sum(len(result[k]) for k in ("eligible", "excluded", "review")), len(keys)
        )
        return dict(zip(keys, result["classified"], strict=True))

    def assert_decisions(self, keys: list[str]) -> None:
        self.assertTrue(keys)
        for key, row in self.classify(keys).items():
            with self.subTest(row=key):
                expected = declarations()[key]["expected"]
                self.assertEqual(row["decision"], expected["decision"])
                self.assertEqual(
                    row["decision_codes"].split(" | "), expected["decision_codes"]
                )

    def test_complete_exclusion_matrix(self) -> None:
        selected = [
            k
            for k, d in declarations().items()
            if d["rule_case"] and d["rule_case"]["rule_id"] != "REVENUE_ADMIN"
        ]
        required = {
            (r["id"], f, p)
            for r in load_business_rules_config()["exclusion_rules"]
            if r["action"] == "EXCLUDE"
            for f in r["fields"]
            for p in r["patterns"]
        }
        self.assertEqual(
            {
                tuple(
                    declarations()[k]["rule_case"][f]
                    for f in ("rule_id", "field", "pattern")
                )
                for k in selected
            },
            required,
        )
        self.assert_decisions(selected)
        for key, row in self.classify(selected).items():
            case = declarations()[key]["rule_case"]
            self.assertIn(case["field"], row["matched_fields"].split(" | "))
            self.assertIn(case["rule_id"], row["matched_rules"].split(" | "))

    def test_eligibility_and_invitation(self) -> None:
        # NPS-006: empty Ignore Reporting remains eligible.
        self.assert_decisions(
            [k for k in classification_rows() if k.startswith(("status_", "boolean_"))]
        )
        normalized, _ = normalize_records(
            list(parsed_rows("parser_Argentina_invitation_both").values())
        )
        # NPS-016: invitation presence does not prevent eligibility.
        row = apply_business_rules(normalized)["classified"][0]
        self.assertEqual(row["decision"], "ELIGIBLE")
        self.assertEqual(
            row["survey_invitation_link"], "https://example.invalid/invitation/last"
        )

    def test_review_matrix(self) -> None:
        self.assert_decisions(
            [
                k
                for k in classification_rows()
                if declarations()[k]["expected"]["decision"] == "REVIEW"
            ]
        )

    def test_exclusion_precedes_review(self) -> None:
        row = self.classify(["multi_exclude_review"])["multi_exclude_review"]
        self.assertEqual(row["decision"], "EXCLUDED")
        self.assertEqual(row["decision_code"], "STATUS_NOT_ELIGIBLE")
        self.assertEqual(
            row["decision_codes"],
            "STATUS_NOT_ELIGIBLE | IGNORE_REPORTING | POD | REVENUE_ADMIN",
        )
        self.assertEqual(row["matched_rules"], "POD | REVENUE_ADMIN")
        self.assertEqual(len(row["decision_reasons"].split(" | ")), 4)

    def test_negative_case_and_accent_controls(self) -> None:
        # NPS-004 meli substring; NPS-005 PODs; NPS-015 generic coaching/1:1 meetings.
        self.assert_decisions(
            [k for k in classification_rows() if k.startswith("control_")]
        )
