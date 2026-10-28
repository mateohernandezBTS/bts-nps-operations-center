"""Validate the synthetic input contract, not the later golden master snapshots."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import unquote, urlsplit

from engine.report_detection import detect_report, load_detection_config
from engine.source_inventory import build_source_inventory
from engine.stages.business_rules import classify_record, load_business_rules_config
from engine.stages.email_parser import (
    extract_html_from_eml,
    extract_records,
    find_report_table,
    parse_eml_report,
)
from engine.stages.normalize import FALSE_VALUES, TRUE_VALUES, normalize_records
from engine.stages.worklist import generate_worklist
from tests.support.fixture_generator import (
    FAMILIES,
    SUM_FIELDS,
    FixtureInputs,
    fixture_root,
    generate,
    json_bytes,
    load_inputs,
)
from tests.support.fixture_paths import copy_fixture, fixture_path


class FixtureCatalogTest(unittest.TestCase):
    """Twelve collected methods; declared variants are checked with subtests."""

    inputs: ClassVar[FixtureInputs]
    specs: ClassVar[dict[str, dict[str, Any]]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = load_inputs()
        cls.specs = {spec["id"]: spec for spec in cls.inputs.catalog["fixtures"]}

    def family(self, name: str) -> list[dict[str, Any]]:
        """Return the explicit family inventory, never a directory glob."""
        return [spec for spec in self.specs.values() if spec["family"] == name]

    def assert_row_contract(self, spec: dict[str, Any]) -> None:
        """Check independently authored row outcomes against real stage entry points."""
        raw = parse_eml_report(fixture_path(spec["id"]))
        self.assertEqual(len(raw), len(spec["rows"]))
        normalized, _ = normalize_records(raw)
        rules = load_business_rules_config()
        for row_id, actual in zip(spec["rows"], normalized, strict=True):
            expected = self.inputs.rows["rows"][row_id]["expected"]
            with self.subTest(fixture=spec["id"], row=row_id):
                for field in ("status", "ignore_reporting", "validation_status"):
                    self.assertEqual(actual[field], expected[field])
                self.assertEqual(
                    actual["validation_issues"],
                    " | ".join(expected["validation_issues"]),
                )
                classified = classify_record(actual, rules)
                self.assertEqual(classified["decision"], expected["decision"])
                self.assertEqual(
                    classified["decision_codes"].split(" | "),
                    expected["decision_codes"],
                )
                if classified["decision"] == "ELIGIBLE":
                    worklist = generate_worklist(
                        [classified],
                        reference_monday=self.inputs.catalog["reference_monday"],
                    )
                    if expected["window"] == "out":
                        self.assertEqual(worklist["worklist"], [])
                        self.assertEqual(len(worklist["outside_window"]), 1)
                    else:
                        self.assertEqual(
                            worklist["worklist"][0]["Output Status"],
                            expected["worklist_status"],
                        )

    def test_weekly_family_contract(self) -> None:
        self.assertEqual(len(self.family("weekly")), 3)
        for spec in self.family("weekly"):
            with self.subTest(fixture=spec["id"]):
                message = BytesParser(policy=policy.default).parsebytes(
                    fixture_path(spec["id"]).read_bytes()
                )
                self.assertEqual(message.get_content_type(), "multipart/alternative")
                self.assertEqual(
                    message.get_boundary(), "fixture-boundary-" + spec["id"]
                )
                parts = list(message.iter_parts())
                self.assertEqual(
                    [part.get_content_type() for part in parts],
                    ["text/plain", "text/html"],
                )
                for part in parts:
                    self.assertEqual(part.get_content_charset(), "utf-8")
                    self.assertEqual(part["Content-Transfer-Encoding"], "base64")
                    self.assertIsNone(part.get_content_disposition())
                self.assertTrue(parts[0].get_content().strip())
                self.assert_row_contract(spec)
                raw = parse_eml_report(fixture_path(spec["id"]))
                self.assertEqual(len(raw), 2)
                self.assertEqual(len(raw[0]), 15)
                self.assertEqual(
                    [r["billing_office"] for r in raw], [spec["country"]] * 2
                )
                self.assertEqual(
                    [r["start_date"] for r in raw], ["8/4/2026", "8/10/2026"]
                )
                table = find_report_table(
                    extract_html_from_eml(fixture_path(spec["id"]))
                )
                widths = [
                    len(r.find_all(["td", "th"], recursive=False))
                    for r in table.select("tr.dataRow")
                ]
                self.assertEqual(widths, [14, 13] if spec["grouped"] else [14, 14])
                labels = [cell.get_text() for cell in table.find("tr").find_all("th")]
                if spec["country"] == "Brazil":
                    for field in SUM_FIELDS:
                        self.assertIn(
                            self.inputs.catalog["headers"][field] + " Sum", labels
                        )
                    self.assertIn("Billing Office \u2191", labels)
                    self.assertIn("Survey Invitation \u2193", labels)
                    ignored = table.select("tr.groupHeader, tr.subtotal, tr.grandTotal")
                    self.assertEqual(
                        [r.get("class") for r in ignored],
                        [["groupHeader"], ["subtotal"], ["grandTotal"]],
                    )
                    self.assertTrue(all(len(r.find_all("td")) == 14 for r in ignored))
                    self.assertEqual(len(table.select("tr")), 6)
                    self.assertEqual(raw[0]["evaluation_programme"], "-")
                    self.assertEqual(raw[0]["nps"], "feature not included")
                    normalized, _ = normalize_records(raw)
                    for field in ("evaluation_programme", "nps"):
                        self.assertEqual(normalized[0][field], raw[0][field])
                    self.assertRegex(raw[1]["project_url"], r"^/FXT[0-9]{15}$")
                    self.assertEqual(extract_records(table), raw)
                elif spec["country"] == "Mexico":
                    self.assertEqual(
                        labels, list(self.inputs.catalog["headers"].values())
                    )
                    self.assertTrue(
                        all(
                            len(r.find_all("td")) == 14
                            for r in table.select("tr.dataRow")
                        )
                    )

    def test_parser_family_contract(self) -> None:
        self.assertEqual(len(self.family("parser")), 8)
        for spec in self.family("parser"):
            self.assert_row_contract(spec)
        plain = parse_eml_report(fixture_path("parser_Brazil_plain_headers"))
        summed = parse_eml_report(fixture_path("parser_Brazil_sum_headers"))
        self.assertEqual(plain, summed)
        self.assertEqual(
            plain, parse_eml_report(fixture_path("parser_Brazil_forwarded_multipart"))
        )
        forwarded = detect_report(
            fixture_path("parser_Brazil_forwarded_multipart"), load_detection_config()
        )
        self.assertEqual(forwarded.detection_status, "DETECTED")
        self.assertEqual(forwarded.country, "Brazil")
        for placement, target in (
            ("first", "first"),
            ("last", "last"),
            ("both", "last"),
        ):
            row = parse_eml_report(
                fixture_path("parser_Argentina_invitation_" + placement)
            )[0]
            self.assertEqual(
                row["survey_invitation_link"],
                "https://example.invalid/invitation/" + target,
            )
        offices = parse_eml_report(fixture_path("parser_Brazil_multiple_offices"))
        self.assertEqual(
            [r["billing_office"] for r in offices],
            ["Brazil", "Brazil", "Brazil / Nexo", "Brazil / Nexo"],
        )

    def test_detection_family_contract(self) -> None:
        config = load_detection_config()
        self.assertEqual(len(self.family("detection")), 5)
        for spec in self.family("detection"):
            with self.subTest(fixture=spec["id"]):
                context = detect_report(fixture_path(spec["id"]), config)
                if spec["report_type"] == "last_results":
                    self.assertEqual(context.detection_status, "DETECTED")
                    self.assertEqual(context.report_type, "Last Results")
                    self.assertEqual(context.country, spec["country"])
                else:
                    self.assertEqual(context.detection_status, "REVIEW")
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for fixture_id in self.inputs.catalog["bundles"]["complete_six_reports"][
                "fixtures"
            ]:
                copy_fixture(fixture_id, directory / fixture_path(fixture_id).name)
            inventory = build_source_inventory(directory, "weekly_upcoming")
            self.assertEqual(inventory.files_scanned, 6)
            self.assertEqual(inventory.matched_files, 3)
            self.assertEqual(inventory.known_out_of_scope_files, 3)
            self.assertEqual(inventory.missing_required_sources, 0)

    def test_classification_family_contract(self) -> None:
        self.assertEqual(len(self.family("classification")), 3)
        for spec in self.family("classification"):
            self.assert_row_contract(spec)
        declarations = self.inputs.rows["rows"].values()
        covered = {
            (
                r["rule_case"]["rule_id"],
                r["rule_case"]["field"],
                r["rule_case"]["pattern"],
            )
            for r in declarations
            if r["rule_case"]
        }
        required = {
            (rule["id"], field, pattern)
            for rule in load_business_rules_config()["exclusion_rules"]
            for field in rule["fields"]
            for pattern in rule["patterns"]
        }
        self.assertEqual(covered, required)
        boolean_tokens = {r["values"]["ignore_reporting"] for r in declarations}
        self.assertTrue((TRUE_VALUES | FALSE_VALUES) <= boolean_tokens)

    def test_scenarios_family_contract(self) -> None:
        self.assertEqual(len(self.family("scenarios")), 2)
        for spec in self.family("scenarios"):
            self.assert_row_contract(spec)
        original = parse_eml_report(fixture_path("weekly_Argentina_upcoming"))[0]
        duplicate = parse_eml_report(
            fixture_path("scenarios_Brazil_duplicate_project")
        )[0]
        for field in ("project_url", "start_date", "project_name"):
            self.assertEqual(original[field], duplicate[field])
        bundles = self.inputs.catalog["bundles"]
        for country in ("argentina", "brazil", "mexico"):
            ids = bundles["missing_" + country]["fixtures"]
            self.assertEqual(len(ids), 2)
            self.assertNotIn("weekly_" + country.title() + "_upcoming", ids)
        with tempfile.TemporaryDirectory() as temp:
            for fixture_id in bundles["duplicate_source"]["fixtures"]:
                copy_fixture(fixture_id, Path(temp) / fixture_path(fixture_id).name)
            self.assertEqual(
                build_source_inventory(Path(temp), "weekly_upcoming").duplicate_sources,
                1,
            )

    def test_malformed_family_contract(self) -> None:
        self.assertEqual(len(self.family("malformed")), 5)
        for spec in self.family("malformed"):
            with self.subTest(fixture=spec["id"]):
                self.assertEqual(
                    detect_report(
                        fixture_path(spec["id"]), load_detection_config()
                    ).detection_status,
                    "DETECTED",
                )
                with self.assertRaisesRegex(ValueError, spec["expected_parse_error"]):
                    parse_eml_report(fixture_path(spec["id"]))
        table = find_report_table(
            extract_html_from_eml(fixture_path("malformed_Brazil_bad_cells"))
        )
        rows = table.select("tr.dataRow")
        self.assertEqual(
            [len(r.find_all(["td", "th"], recursive=False)) for r in rows], [12, 15]
        )
        rows[0].decompose()
        with self.assertRaisesRegex(ValueError, "15 celdas"):
            extract_records(table)

    def test_generation_is_identical_across_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / "first", Path(temp) / "second"
            self.assertEqual(generate(first), generate(second))
            for relative in ["fixture_manifest.json"] + [
                "eml/" + s["path"] for s in self.specs.values()
            ]:
                self.assertEqual(
                    (first / relative).read_bytes(), (second / relative).read_bytes()
                )

    def test_email_bytes_and_mime_are_stable(self) -> None:
        html_encodings = set()
        for spec in self.specs.values():
            content = fixture_path(spec["id"]).read_bytes()
            with self.subTest(fixture=spec["id"]):
                self.assertNotIn(b"\n", content.replace(b"\r\n", b""))
                message = BytesParser(policy=policy.default).parsebytes(content)
                self.assertEqual(message["Date"], "Mon, 03 Aug 2026 09:00:00 +0000")
                self.assertEqual(
                    message["Message-ID"], "<" + spec["id"] + "@example.invalid>"
                )
                for part in message.walk():
                    if not part.is_multipart():
                        expected_cte = "base64"
                        if part.get_content_type() == "text/html":
                            html_encodings.add(part["Content-Transfer-Encoding"])
                            expected_cte = spec.get("html_cte", "base64")
                        self.assertEqual(
                            part["Content-Transfer-Encoding"], expected_cte
                        )
                        if expected_cte == "quoted-printable":
                            self.assertIn(b"=3D", content)
                            self.assertIn("\u2715", part.get_content())
                if spec["mime"] == "multipart":
                    self.assertEqual(
                        message.get_boundary(), "fixture-boundary-" + spec["id"]
                    )
                    html = [
                        part
                        for part in message.walk()
                        if part.get_content_type() == "text/html"
                    ]
                    self.assertEqual(len(html), 3)
                    self.assertEqual(
                        max(
                            html, key=lambda p: len(p.get_content())
                        ).get_content_disposition(),
                        "attachment",
                    )
        self.assertEqual(html_encodings, {"base64", "quoted-printable"})

    def test_entity_schema_is_explicitly_invented(self) -> None:
        self.assertIn("invented", self.inputs.catalog["provenance"].lower())
        for row_id, row in self.inputs.rows["rows"].items():
            with self.subTest(row=row_id):
                self.assertEqual(
                    set(row["values"]), set(self.inputs.catalog["headers"])
                )
                for field in ("client_name", "project_name", "all_staffings"):
                    value = row["values"][field]
                    if value:
                        self.assertIn("fixture", value.casefold())
                self.assertIn(
                    row["expected"]["decision"], ("ELIGIBLE", "EXCLUDED", "REVIEW")
                )

    def test_links_and_project_ids_are_synthetic(self) -> None:
        lengths = set()
        relative_links = set()
        for row_id, row in self.inputs.rows["rows"].items():
            for field, url in row["links"].items():
                if not url:
                    continue
                with self.subTest(row=row_id, field=field):
                    parsed = urlsplit(url)
                    if url.startswith("/"):
                        self.assertEqual(field, "project_name")
                        self.assertEqual(parsed.scheme, "")
                        self.assertEqual(parsed.netloc, "")
                        self.assertRegex(url, r"^/FXT[0-9]{15}$")
                        relative_links.add(url)
                    else:
                        self.assertEqual(parsed.scheme, "https")
                        self.assertEqual(parsed.netloc, "example.invalid")
                    if field == "project_name" and row_id != "bad_project_url":
                        project_id = unquote(parsed.path).split("/")[-1]
                        self.assertRegex(project_id, r"^FXT[0-9]{12}([0-9]{3})?$")
                        lengths.add(len(project_id))
        self.assertEqual(lengths, {15, 18})
        self.assertTrue(relative_links)

    def test_catalog_and_hash_manifest_are_complete(self) -> None:
        root = fixture_root()
        manifest = json.loads(
            (root / "fixture_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(manifest["fixtures"]), 26)
        self.assertEqual({s["family"] for s in self.specs.values()}, set(FAMILIES))
        self.assertEqual(
            {s["path"] for s in self.specs.values()},
            {
                p.relative_to(root / "eml").as_posix()
                for p in (root / "eml").rglob("*.eml")
            },
        )
        for name, digest in manifest["inputs"].items():
            self.assertEqual(
                hashlib.sha256((root / name).read_bytes()).hexdigest(), digest
            )
        for entry in manifest["fixtures"]:
            self.assertEqual(
                hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest(),
                entry["sha256"],
            )
            self.assertEqual(entry["data_rows"], len(self.specs[entry["id"]]["rows"]))
            self.assertTrue(entry["properties"])
            self.assertTrue(entry["scenarios"])
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp)
            (scratch / "rows.json").write_bytes((root / "rows.json").read_bytes())
            unsafe = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
            unsafe["fixtures"][0]["path"] = "../outside.eml"
            (scratch / "catalog.json").write_bytes(json_bytes(unsafe))
            with self.assertRaises(ValueError):
                load_inputs(scratch)

    def test_processing_copies_leave_sources_immutable(self) -> None:
        fixture_id = "weekly_Brazil_upcoming"
        original = fixture_path(fixture_id).read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            copied = copy_fixture(fixture_id, Path(temp) / "pending" / "Brazil.eml")
            self.assertEqual(copied.read_bytes(), original)
            copied.write_bytes(b"Modified only the disposable copy")
            self.assertEqual(fixture_path(fixture_id).read_bytes(), original)
            with self.assertRaises(FileExistsError):
                copy_fixture(fixture_id, copied)
        with self.assertRaises(ValueError):
            copy_fixture(fixture_id, fixture_root() / "must-not-create.eml")
        with self.assertRaises(ValueError):
            generate(fixture_root())
        with self.assertRaises(KeyError):
            fixture_path("undefined-fixture")


if __name__ == "__main__":
    unittest.main()
