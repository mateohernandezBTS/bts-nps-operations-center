"""Control counts detect records altered, dropped or duplicated in transcription."""

from __future__ import annotations

import copy
import json
import unittest
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from nps_v2.domain import SalesforceId
from nps_v2.registry import load_registry
from nps_v2.salesforce.control import (
    ControlMismatchError,
    build_project_control_query,
    build_survey_set_control_queries,
    verify_projects,
    verify_survey_sets,
)
from nps_v2.salesforce.queries import Query
from nps_v2.salesforce.readers import ReaderError, read_projects, read_survey_sets
from nps_v2.selection import range_selection

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DATA_QUERY = Query(name="projects", soql="SELECT ...", limit=2000)
SETS_QUERY = Query(name="survey_sets_01", soql="SELECT ...", limit=2000)
CONTROL = Query(name="projects_control", soql="SELECT ...", limit=2000)
SETS_CONTROL = Query(name="survey_sets_01_control", soql="SELECT ...", limit=2000)


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    records = [{"attributes": {"type": "AggregateResult"}, **row} for row in rows]
    return {"totalSize": len(records), "done": True, "records": records}


def project_control_for(raw_projects: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(
        (
            r["rosscrooke__Start_Date__c"],
            r["rosscrooke__Status__c"],
            r["rosscrooke__Ignore_Reporting__c"],
            r["Project_Sub_Type__c"],
        )
        for r in raw_projects["records"]
    )
    return aggregate(
        [
            {
                "rosscrooke__Start_Date__c": start,
                "rosscrooke__Status__c": status,
                "rosscrooke__Ignore_Reporting__c": ignore,
                "Project_Sub_Type__c": sub_type,
                "n": n,
            }
            for (start, status, ignore, sub_type), n in counts.items()
        ]
    )


class QueryTextTest(unittest.TestCase):
    def test_project_control_reuses_the_data_filter(self) -> None:
        query = build_project_control_query(
            range_selection(date(2026, 11, 24), date(2026, 11, 30)), load_registry()
        )
        self.assertEqual(query.name, "projects_control")
        self.assertEqual(
            query.soql,
            "SELECT rosscrooke__Start_Date__c, rosscrooke__Status__c, "
            "rosscrooke__Ignore_Reporting__c, Project_Sub_Type__c, COUNT(Id) n "
            "FROM rosscrooke__Project__c "
            "WHERE rosscrooke__Start_Date__c >= 2026-11-24 "
            "AND rosscrooke__Start_Date__c <= 2026-11-30 "
            "AND Billing_Country__c IN ('Argentina', 'Brazil', 'Nexo', 'Mexico') "
            "GROUP BY rosscrooke__Start_Date__c, rosscrooke__Status__c, "
            "rosscrooke__Ignore_Reporting__c, Project_Sub_Type__c "
            "ORDER BY rosscrooke__Start_Date__c ASC, rosscrooke__Status__c ASC, "
            "rosscrooke__Ignore_Reporting__c ASC, Project_Sub_Type__c ASC LIMIT 2000",
        )

    def test_survey_set_controls_follow_the_data_chunks(self) -> None:
        ids = [SalesforceId(f"a0gAA{n:010d}AAA") for n in range(1, 4)]
        queries = build_survey_set_control_queries(ids, chunk_size=2)
        self.assertEqual(
            [q.name for q in queries],
            ["survey_sets_01_control", "survey_sets_02_control"],
        )
        self.assertEqual(
            queries[1].soql,
            "SELECT Survey__c, SurveyNPS__c, COUNT(Id) n FROM Survey_Set__c "
            "WHERE Project__c IN ('a0gAA0000000003AAA') "
            "GROUP BY Survey__c, SurveyNPS__c "
            "ORDER BY Survey__c ASC, SurveyNPS__c ASC LIMIT 2000",
        )


class VerifyProjectsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = fixture("connector_projects.json")
        self.control = project_control_for(self.raw)

    def verify(self, raw: dict[str, Any]) -> None:
        verify_projects(read_projects(raw, DATA_QUERY), self.control, CONTROL)

    def test_faithful_transcription_passes(self) -> None:
        self.verify(self.raw)

    def test_transcription_errors_are_detected(self) -> None:
        def altered(field: str, value: Any) -> dict[str, Any]:
            raw = copy.deepcopy(self.raw)
            raw["records"][0][field] = value
            return raw

        dropped = copy.deepcopy(self.raw)
        dropped["records"].pop()
        dropped["totalSize"] = 2
        duplicated = copy.deepcopy(self.raw)
        twin = copy.deepcopy(duplicated["records"][0])
        twin["Id"] = "a0gAA0000000099AAA"
        duplicated["records"].append(twin)
        duplicated["totalSize"] = 4

        cases = {
            "status": altered("rosscrooke__Status__c", "Prelim"),
            "ignore reporting": altered("rosscrooke__Ignore_Reporting__c", True),
            "start date": altered("rosscrooke__Start_Date__c", "2026-11-25"),
            "sub-type": altered("Project_Sub_Type__c", "Group/POD Coaching"),
            "dropped record": dropped,
            "duplicated record": duplicated,
        }
        for name, raw in cases.items():
            with self.subTest(case=name):
                with self.assertRaisesRegex(ControlMismatchError, "no coinciden"):
                    self.verify(raw)

    def test_malformed_control_rows_fail_closed(self) -> None:
        projects = read_projects(self.raw, DATA_QUERY)
        bad_rows: dict[str, dict[str, Any]] = {
            "missing count": {"rosscrooke__Start_Date__c": "2026-11-24"},
            "zero count": {
                "rosscrooke__Start_Date__c": "2026-11-24",
                "rosscrooke__Status__c": "Conf",
                "rosscrooke__Ignore_Reporting__c": False,
                "Project_Sub_Type__c": None,
                "n": 0,
            },
        }
        for name, row in bad_rows.items():
            with self.subTest(case=name):
                with self.assertRaises(ReaderError):
                    verify_projects(projects, aggregate([row]), CONTROL)


class VerifySurveySetsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sets = read_survey_sets(
            [(SETS_QUERY, fixture("connector_survey_sets.json"))]
        )
        self.control = aggregate(
            [
                {"Survey__c": "0KdAA0000000001AAA", "SurveyNPS__c": True, "n": 1},
                {"Survey__c": None, "SurveyNPS__c": False, "n": 1},
            ]
        )

    def test_matching_counts_pass_even_across_chunks(self) -> None:
        verify_survey_sets(self.sets, [(SETS_CONTROL, self.control)])
        rows = copy.deepcopy(self.control)["records"]
        first, second = aggregate([rows[0]]), aggregate([rows[1]])
        verify_survey_sets(self.sets, [(SETS_CONTROL, first), (SETS_CONTROL, second)])

    def test_missing_set_is_detected(self) -> None:
        with self.assertRaisesRegex(ControlMismatchError, "survey sets"):
            verify_survey_sets(self.sets[:1], [(SETS_CONTROL, self.control)])


if __name__ == "__main__":
    unittest.main()
