"""Normalization token matrices and validation row attribution."""

from __future__ import annotations

import unittest

from engine.stages.normalize import normalize_records, normalize_salesforce_date
from tests.support.stage_cases import classification_rows, declarations


class NormalizeTest(unittest.TestCase):
    def test_dates_and_whitespace(self) -> None:
        for value, expected in (
            ("08/04/26", "8/4/2026"),
            (" 8/4/2026 ", "8/4/2026"),
            ("", ""),
        ):
            with self.subTest(value=value):
                self.assertEqual(normalize_salesforce_date(value), (expected, None))
        rows = classification_rows()
        normalized, issues = normalize_records(
            [rows["short_date"], rows["whitespace_entities"]]
        )
        self.assertEqual(issues, [])
        self.assertEqual(normalized[0]["start_date"], "8/4/2026")
        self.assertEqual(normalized[1]["project_name"], "Fixture Session <Glow>")

    def assert_variants(self, keys: list[str], fields: tuple[str, ...]) -> None:
        rows = classification_rows()
        self.assertTrue(keys)
        for key in keys:
            with self.subTest(row=key):
                normalized, issues = normalize_records([rows[key]])
                expected = declarations()[key]["expected"]
                for field in fields:
                    self.assertEqual(normalized[0][field], expected[field])
                self.assertEqual(
                    normalized[0]["validation_issues"],
                    " | ".join(expected["validation_issues"]),
                )
                self.assertEqual(
                    issues[0]["issues"] if issues else [], expected["validation_issues"]
                )

    def test_boolean_tokens(self) -> None:
        # NPS-006: empty is False and x is True.
        self.assert_variants(
            [
                k
                for k in classification_rows()
                if k.startswith("boolean_") or k == "unknown_boolean"
            ],
            ("ignore_reporting", "validation_status"),
        )

    def test_status_variants(self) -> None:
        self.assert_variants(
            [
                k
                for k in classification_rows()
                if k.startswith("status_") or k in ("unknown_status", "missing_status")
            ],
            ("status", "validation_status"),
        )

    def test_required_fields_and_row_numbers(self) -> None:
        selected = {
            k: r
            for k, r in classification_rows().items()
            if k.startswith(("missing_", "invalid_")) and k != "missing_project_url"
        }
        self.assertEqual(len(selected), 6)
        normalized, issues = normalize_records(list(selected.values()))
        self.assertEqual([r["row_number"] for r in issues], list(range(1, 7)))
        for key, row, issue in zip(selected, normalized, issues, strict=True):
            with self.subTest(row=key):
                expected = declarations()[key]["expected"]["validation_issues"]
                self.assertEqual(row["validation_status"], "REVIEW")
                self.assertEqual(issue["issues"], expected)
                self.assertEqual(row["validation_issues"], " | ".join(expected))
