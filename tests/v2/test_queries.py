"""Generated SOQL text: exact output, escaping and chunking."""

from __future__ import annotations

import unittest
from datetime import date

from nps_v2.domain import SalesforceId
from nps_v2.registry import load_registry
from nps_v2.salesforce.queries import (
    PROJECT_QUERY_LIMIT,
    build_projects_query,
    build_survey_set_queries,
    soql_string,
)
from nps_v2.selection import day_selection, standard_week_selection


def project_id(number: int) -> SalesforceId:
    return SalesforceId(f"a0gAA{number:010d}AAA")


class ProjectsQueryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_registry()

    def test_standard_week_all_countries(self) -> None:
        query = build_projects_query(
            standard_week_selection(date(2026, 11, 25)), self.registry
        )
        self.assertEqual(query.name, "projects")
        self.assertEqual(query.limit, PROJECT_QUERY_LIMIT)
        self.assertEqual(
            query.soql,
            "SELECT Id, Name, Billing_Country__c, rosscrooke__Start_Date__c, "
            "rosscrooke__End_Date__c, rosscrooke__Client_Name__c, Project_Sub_Type__c, "
            "rosscrooke__Status__c, All_Staffings__c, rosscrooke__Ignore_Reporting__c, "
            "Survey_Invitation__c FROM rosscrooke__Project__c "
            "WHERE rosscrooke__Start_Date__c >= 2026-11-24 "
            "AND rosscrooke__Start_Date__c <= 2026-11-30 "
            "AND Billing_Country__c IN ('Argentina', 'Brazil', 'Nexo', 'Mexico') "
            "ORDER BY rosscrooke__Start_Date__c ASC, Id ASC LIMIT 2000",
        )

    def test_country_codes_narrow_the_query(self) -> None:
        selection = day_selection(date(2026, 11, 26)).with_filters(
            country_codes=("BR",)
        )
        soql = build_projects_query(selection, self.registry).soql
        self.assertIn("Billing_Country__c IN ('Brazil', 'Nexo')", soql)
        self.assertIn(">= 2026-11-26 AND rosscrooke__Start_Date__c <= 2026-11-26", soql)

    def test_text_filters_never_reach_the_query(self) -> None:
        from nps_v2.selection import SearchFilters

        selection = day_selection(date(2026, 11, 26)).with_filters(
            filters=SearchFilters(client="O'Brien", facilitator="x")
        )
        soql = build_projects_query(selection, self.registry).soql
        self.assertNotIn("Brien", soql)


class SoqlStringTest(unittest.TestCase):
    def test_quotes_and_backslashes_are_escaped(self) -> None:
        self.assertEqual(soql_string("O'Brien"), "'O\\'Brien'")
        self.assertEqual(soql_string("a\\b"), "'a\\\\b'")
        self.assertEqual(soql_string("x' OR Name != '"), "'x\\' OR Name != \\''")


class SurveySetQueriesTest(unittest.TestCase):
    def test_no_projects_no_queries(self) -> None:
        self.assertEqual(build_survey_set_queries([]), [])

    def test_single_chunk_exact_text(self) -> None:
        (query,) = build_survey_set_queries([project_id(1), project_id(2)])
        self.assertEqual(query.name, "survey_sets_01")
        self.assertEqual(
            query.soql,
            "SELECT Id, Project__c, Survey__c, Survey__r.Name, Survey_Language__c, "
            "SurveyNPS__c, Survey_Invitation_Link__c, QR_Code_URL__c, CreatedDate "
            "FROM Survey_Set__c "
            "WHERE Project__c IN ('a0gAA0000000001AAA', 'a0gAA0000000002AAA') "
            "ORDER BY Project__c ASC, CreatedDate ASC, Id ASC LIMIT 2000",
        )

    def test_chunking_and_deduplication(self) -> None:
        ids = [project_id(n) for n in range(1, 6)] + [SalesforceId("a0gAA0000000001")]
        queries = build_survey_set_queries(ids, chunk_size=2)
        self.assertEqual(
            [q.name for q in queries], [f"survey_sets_0{n}" for n in (1, 2, 3)]
        )
        self.assertEqual([q.soql.count("'a0g") for q in queries], [2, 2, 1])

    def test_invalid_input(self) -> None:
        with self.assertRaises(ValueError):
            build_survey_set_queries([project_id(1)], chunk_size=0)
        with self.assertRaises(TypeError):
            build_survey_set_queries(["a0gAA0000000001AAA"])  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main()
