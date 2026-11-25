"""Connector responses → snapshots, failing closed on anything unexpected."""

from __future__ import annotations

import copy
import json
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from nps_v2.domain import SalesforceId
from nps_v2.salesforce.queries import Query
from nps_v2.salesforce.readers import ReaderError, read_projects, read_survey_sets

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PROJECTS_QUERY = Query(name="projects", soql="SELECT ...", limit=2000)
SETS_QUERY = Query(name="survey_sets_01", soql="SELECT ...", limit=2000)


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ReadProjectsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.projects = read_projects(
            fixture("connector_projects.json"), PROJECTS_QUERY
        )

    def test_reads_every_record_in_order(self) -> None:
        self.assertEqual(
            [str(p.project_id) for p in self.projects],
            ["a0gAA0000000001AAA", "a0gAA0000000002AAA", "a0gAA0000000003AAA"],
        )

    def test_typed_values(self) -> None:
        first = self.projects[0]
        self.assertEqual(first.start_date, date(2026, 11, 24))
        self.assertEqual(first.end_date, date(2026, 11, 24))
        self.assertIs(first.ignore_reporting, False)
        self.assertEqual(first.survey_invitation_id, SalesforceId("0KiAA0000000001AAA"))
        self.assertEqual(first.all_staffings, "Facilitator One, Facilitator Two")

    def test_nulls_become_empty_or_none(self) -> None:
        second = self.projects[1]
        self.assertIsNone(second.end_date)
        self.assertEqual(second.sub_type, "")
        self.assertEqual(second.all_staffings, "")
        self.assertIsNone(second.survey_invitation_id)
        self.assertIs(second.ignore_reporting, True)


class ReadSurveySetsTest(unittest.TestCase):
    def test_reads_related_survey_name_and_timestamps(self) -> None:
        first, second = read_survey_sets(
            [(SETS_QUERY, fixture("connector_survey_sets.json"))]
        )
        self.assertEqual(first.survey_name, "Synthetic NPS")
        self.assertIs(first.survey_nps, True)
        self.assertEqual(first.language, "es")
        self.assertEqual(
            first.created_at, datetime(2026, 11, 17, 12, 37, 27, tzinfo=UTC)
        )
        self.assertIsNone(second.survey_id)
        self.assertEqual((second.survey_name, second.language), ("", ""))
        self.assertEqual((second.invitation_link, second.qr_code_url), ("", ""))

    def test_several_chunks_are_merged(self) -> None:
        other = fixture("connector_survey_sets.json")
        other["records"] = other["records"][:1]
        other["totalSize"] = 1
        other["records"][0]["Id"] = "aHqAA0000000009AAA"
        result = read_survey_sets(
            [(SETS_QUERY, fixture("connector_survey_sets.json")), (SETS_QUERY, other)]
        )
        self.assertEqual(len(result), 3)

    def test_duplicate_survey_set_across_chunks_fails(self) -> None:
        raw = fixture("connector_survey_sets.json")
        with self.assertRaisesRegex(ReaderError, "Duplicate survey set"):
            read_survey_sets([(SETS_QUERY, raw), (SETS_QUERY, raw)])


class EnvelopeTest(unittest.TestCase):
    def assert_rejected(
        self, raw: Any, message: str, query: Query = PROJECTS_QUERY
    ) -> None:
        with self.assertRaisesRegex(ReaderError, message):
            read_projects(raw, query)

    def test_envelope_failures(self) -> None:
        valid = fixture("connector_projects.json")
        cases: dict[str, tuple[Any, str]] = {
            "not an object": ([], "not a JSON object"),
            "paginated": ({**valid, "done": False}, "incomplete"),
            "missing done": (
                {k: v for k, v in valid.items() if k != "done"},
                "incomplete",
            ),
            "no records": ({**valid, "records": None}, "no records list"),
            "count mismatch": ({**valid, "totalSize": 4}, "does not match"),
            "bool count": ({**valid, "totalSize": True}, "does not match"),
            "error payload": ({"error": "INVALID_FIELD"}, "incomplete"),
        }
        for name, (raw, message) in cases.items():
            with self.subTest(case=name):
                self.assert_rejected(raw, message)

    def test_hitting_the_limit_is_treated_as_truncated(self) -> None:
        tight = Query(name="projects", soql="SELECT ...", limit=3)
        self.assert_rejected(
            fixture("connector_projects.json"), "may be truncated", tight
        )

    def test_empty_result_is_valid(self) -> None:
        self.assertEqual(
            read_projects(
                {"totalSize": 0, "done": True, "records": []}, PROJECTS_QUERY
            ),
            [],
        )


class RecordFailuresTest(unittest.TestCase):
    def mutated(self, field: str, value: Any, *, drop: bool = False) -> dict[str, Any]:
        raw = copy.deepcopy(fixture("connector_projects.json"))
        if drop:
            del raw["records"][0][field]
        else:
            raw["records"][0][field] = value
        return raw

    def test_record_failures(self) -> None:
        cases: dict[str, tuple[dict[str, Any], str]] = {
            "missing field": (
                self.mutated("Name", None, drop=True),
                "missing field Name",
            ),
            "bad id": (self.mutated("Id", "nope"), "Id must be a Salesforce Id"),
            "null start": (
                self.mutated("rosscrooke__Start_Date__c", None),
                "YYYY-MM-DD",
            ),
            "local date format": (
                self.mutated("rosscrooke__Start_Date__c", "11/24/2026"),
                "YYYY-MM-DD",
            ),
            "boolean as text": (
                self.mutated("rosscrooke__Ignore_Reporting__c", "false"),
                "true or false",
            ),
            "null boolean": (
                self.mutated("rosscrooke__Ignore_Reporting__c", None),
                "true or false",
            ),
            "number as text": (self.mutated("Name", 7), "text or null"),
            "wrong object": (
                self.mutated("attributes", {"type": "Account"}),
                "expected rosscrooke__Project__c",
            ),
        }
        for name, (raw, message) in cases.items():
            with self.subTest(case=name):
                with self.assertRaisesRegex(ReaderError, message):
                    read_projects(raw, PROJECTS_QUERY)

    def test_duplicate_project_fails(self) -> None:
        raw = fixture("connector_projects.json")
        raw["records"][1]["Id"] = raw["records"][0]["Id"][:15]
        with self.assertRaisesRegex(ReaderError, "Duplicate project"):
            read_projects(raw, PROJECTS_QUERY)

    def test_survey_set_timestamp_and_relation_failures(self) -> None:
        cases: dict[str, tuple[str, Any, str]] = {
            "naive timestamp": ("CreatedDate", "2026-11-17T12:37:27", "time zone"),
            "bad timestamp": ("CreatedDate", "yesterday", "a timestamp"),
            "relation not object": ("Survey__r", "Synthetic NPS", "an object or null"),
            "null nps flag": ("SurveyNPS__c", None, "true or false"),
        }
        for name, (field, value, message) in cases.items():
            with self.subTest(case=name):
                raw = fixture("connector_survey_sets.json")
                raw["records"][0][field] = value
                with self.assertRaisesRegex(ReaderError, message):
                    read_survey_sets([(SETS_QUERY, raw)])


if __name__ == "__main__":
    unittest.main()
