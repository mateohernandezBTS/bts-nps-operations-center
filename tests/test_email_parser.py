"""Parser format, link, MIME and failure contracts."""

from __future__ import annotations

import unittest

from engine.stages.email_parser import (
    extract_html_from_eml,
    extract_records,
    find_report_table,
    parse_eml_report,
)
from tests.support.fixture_generator import load_inputs
from tests.support.fixture_paths import fixture_path
from tests.support.stage_cases import declarations, parsed_rows


class EmailParserTest(unittest.TestCase):
    def test_plain_and_sum_headers(self) -> None:
        plain = parse_eml_report(fixture_path("parser_Brazil_plain_headers"))
        self.assertEqual(
            plain, parse_eml_report(fixture_path("parser_Brazil_sum_headers"))
        )
        self.assertEqual(len(plain), 2)
        for key, row in parsed_rows("parser_Brazil_plain_headers").items():
            self.assertEqual(
                row["project_name"], declarations()[key]["values"]["project_name"]
            )
            self.assertEqual(len(row), 15)

    def test_grouped_offices(self) -> None:
        rows = parse_eml_report(fixture_path("parser_Brazil_multiple_offices"))
        self.assertEqual(
            [r["billing_office"] for r in rows],
            ["Brazil", "Brazil", "Brazil / Nexo", "Brazil / Nexo"],
        )
        self.assertEqual(
            [r["project_name"] for r in rows],
            [
                declarations()[k]["values"]["project_name"]
                for k in parsed_rows("parser_Brazil_multiple_offices")
            ],
        )

    def test_mexico_plain_td(self) -> None:
        for key, row in parsed_rows("parser_Mexico_14_td").items():
            with self.subTest(row=key):
                expected = declarations()[key]
                self.assertEqual(row["billing_office"], "Mexico")
                self.assertEqual(row["project_url"], expected["links"]["project_name"])
                for field in ("client_name", "status", "ignore_reporting"):
                    self.assertEqual(row[field], expected["values"][field])

    def test_invitation_precedence(self) -> None:
        # NPS-002/016: invitations are parsed without a duplicate prevention rule.
        for placement, target in (
            ("first", "first"),
            ("last", "last"),
            ("both", "last"),
        ):
            with self.subTest(placement=placement):
                row = parse_eml_report(
                    fixture_path("parser_Argentina_invitation_" + placement)
                )[0]
                self.assertEqual(
                    row["survey_invitation_link"],
                    "https://example.invalid/invitation/" + target,
                )
                self.assertTrue(row["survey_invitation"])

    def test_multipart_ignores_attachment(self) -> None:
        path = fixture_path("parser_Brazil_forwarded_multipart")
        self.assertEqual(
            parse_eml_report(path),
            parse_eml_report(fixture_path("parser_Brazil_plain_headers")),
        )
        self.assertEqual(
            extract_records(find_report_table(extract_html_from_eml(path))),
            parse_eml_report(path),
        )

    def test_malformed_inputs(self) -> None:
        for spec in load_inputs().catalog["fixtures"]:
            if spec["family"] == "malformed":
                with self.subTest(fixture=spec["id"]):
                    with self.assertRaisesRegex(
                        ValueError, spec["expected_parse_error"]
                    ):
                        parse_eml_report(fixture_path(spec["id"]))
        table = find_report_table(
            extract_html_from_eml(fixture_path("malformed_Brazil_bad_cells"))
        )
        table.select("tr.dataRow")[0].decompose()
        with self.assertRaisesRegex(ValueError, "15 celdas"):
            extract_records(table)
