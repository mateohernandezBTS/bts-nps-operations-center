"""SOQL text generated from a selection and the country registry.

Claude runs these queries verbatim through the Salesforce connector; it never writes
its own. Text filters of the selection are applied by the engine after reading, so the
query only bounds dates and countries and every returned row can be explained.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from nps_v2.domain import SalesforceId
from nps_v2.registry import CountryRegistry
from nps_v2.selection import Selection

PROJECT_OBJECT = "rosscrooke__Project__c"
SURVEY_SET_OBJECT = "Survey_Set__c"

PROJECT_FIELDS: tuple[str, ...] = (
    "Id",
    "Name",
    "Billing_Country__c",
    "rosscrooke__Start_Date__c",
    "rosscrooke__End_Date__c",
    "rosscrooke__Client_Name__c",
    "Project_Sub_Type__c",
    "rosscrooke__Status__c",
    "All_Staffings__c",
    "rosscrooke__Ignore_Reporting__c",
    "Survey_Invitation__c",
)

SURVEY_SET_FIELDS: tuple[str, ...] = (
    "Id",
    "Project__c",
    "Survey__c",
    "Survey__r.Name",
    "Survey_Language__c",
    "SurveyNPS__c",
    "Survey_Invitation_Link__c",
    "QR_Code_URL__c",
    "CreatedDate",
)

# A query returning this many rows may have been cut: readers reject it.
PROJECT_QUERY_LIMIT = 2000
SURVEY_SET_QUERY_LIMIT = 2000
SURVEY_SET_CHUNK_SIZE = 200


@dataclass(frozen=True, slots=True)
class Query:
    """A query to run through the connector, with the row cap it was built with."""

    name: str
    soql: str
    limit: int


def soql_string(value: str) -> str:
    """Quote a value as a SOQL string literal."""
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def build_projects_query(selection: Selection, registry: CountryRegistry) -> Query:
    billing_values = registry.billing_values(selection.country_codes)
    countries = ", ".join(soql_string(v) for v in billing_values)
    soql = (
        f"SELECT {', '.join(PROJECT_FIELDS)} "
        f"FROM {PROJECT_OBJECT} "
        f"WHERE rosscrooke__Start_Date__c >= {selection.date_from.isoformat()} "
        f"AND rosscrooke__Start_Date__c <= {selection.date_to.isoformat()} "
        f"AND Billing_Country__c IN ({countries}) "
        "ORDER BY rosscrooke__Start_Date__c ASC, Id ASC "
        f"LIMIT {PROJECT_QUERY_LIMIT}"
    )
    return Query(name="projects", soql=soql, limit=PROJECT_QUERY_LIMIT)


def build_survey_set_queries(
    project_ids: Iterable[SalesforceId],
    chunk_size: int = SURVEY_SET_CHUNK_SIZE,
) -> list[Query]:
    """One query per chunk of project Ids (none when there are no projects)."""
    queries = []
    for number, chunk in enumerate(chunk_project_ids(project_ids, chunk_size), start=1):
        soql = (
            f"SELECT {', '.join(SURVEY_SET_FIELDS)} "
            f"FROM {SURVEY_SET_OBJECT} "
            f"WHERE Project__c IN ({id_list(chunk)}) "
            "ORDER BY Project__c ASC, CreatedDate ASC, Id ASC "
            f"LIMIT {SURVEY_SET_QUERY_LIMIT}"
        )
        queries.append(
            Query(
                name=f"survey_sets_{number:02d}",
                soql=soql,
                limit=SURVEY_SET_QUERY_LIMIT,
            )
        )
    return queries


def chunk_project_ids(
    project_ids: Iterable[SalesforceId], chunk_size: int = SURVEY_SET_CHUNK_SIZE
) -> list[Sequence[SalesforceId]]:
    """Unique Ids in input order, split into chunks of at most ``chunk_size``."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    unique = _unique(project_ids)
    return [unique[i : i + chunk_size] for i in range(0, len(unique), chunk_size)]


def id_list(project_ids: Iterable[SalesforceId]) -> str:
    return ", ".join(soql_string(str(project_id)) for project_id in project_ids)


def _unique(project_ids: Iterable[SalesforceId]) -> Sequence[SalesforceId]:
    seen: set[SalesforceId] = set()
    ordered = []
    for project_id in project_ids:
        if not isinstance(project_id, SalesforceId):
            raise TypeError("project_ids must contain SalesforceId values")
        if project_id not in seen:
            seen.add(project_id)
            ordered.append(project_id)
    return ordered
