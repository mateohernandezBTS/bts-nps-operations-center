"""Control counts that guard against transcription errors.

Connector responses reach Claude, not a file, so Claude writes them to the run folder
itself. To make sure nothing was dropped, duplicated or altered on the way, Claude also
runs a small aggregate query per data query (generated here) and the engine compares
its counts with the saved records. Any difference stops the run.

Covered for projects: start date, status, Ignore Reporting and sub-type (the fields
that drive eligibility). Free-text fields (names, client, staffing) are not covered by
counts; the preview shows them for human review.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Hashable, Iterable, Mapping, Sequence
from typing import Any

from nps_v2.domain import DomainError, ProjectSnapshot, SalesforceId, SurveySetSnapshot
from nps_v2.registry import CountryRegistry
from nps_v2.salesforce.queries import (
    PROJECT_OBJECT,
    SURVEY_SET_CHUNK_SIZE,
    SURVEY_SET_OBJECT,
    Query,
    build_projects_query,
    chunk_project_ids,
    id_list,
)
from nps_v2.salesforce.readers import ReaderError, query_records
from nps_v2.selection import Selection

CONTROL_LIMIT = 2000
PROJECT_CONTROL_FIELDS = (
    "rosscrooke__Start_Date__c",
    "rosscrooke__Status__c",
    "rosscrooke__Ignore_Reporting__c",
    "Project_Sub_Type__c",
)
SURVEY_SET_CONTROL_FIELDS = ("Survey__c", "SurveyNPS__c")
COUNT_ALIAS = "n"


class ControlMismatchError(ReaderError):
    """Saved records do not match Salesforce's own counts."""


def build_project_control_query(
    selection: Selection, registry: CountryRegistry
) -> Query:
    where = build_projects_query(selection, registry).soql
    where = where[where.index(" WHERE ") : where.index(" ORDER BY ")]
    return Query(
        name="projects_control",
        soql=_aggregate(PROJECT_OBJECT, PROJECT_CONTROL_FIELDS, where),
        limit=CONTROL_LIMIT,
    )


def build_survey_set_control_queries(
    project_ids: Iterable[SalesforceId], chunk_size: int = SURVEY_SET_CHUNK_SIZE
) -> list[Query]:
    return [
        Query(
            name=f"survey_sets_{number:02d}_control",
            soql=_aggregate(
                SURVEY_SET_OBJECT,
                SURVEY_SET_CONTROL_FIELDS,
                f" WHERE Project__c IN ({id_list(chunk)})",
            ),
            limit=CONTROL_LIMIT,
        )
        for number, chunk in enumerate(
            chunk_project_ids(project_ids, chunk_size), start=1
        )
    ]


def verify_projects(
    projects: Sequence[ProjectSnapshot], raw: Any, query: Query
) -> None:
    expected = _read_counts(raw, query, PROJECT_CONTROL_FIELDS, _project_key)
    actual: Counter[Hashable] = Counter(
        (p.start_date.isoformat(), p.status, p.ignore_reporting, p.sub_type)
        for p in projects
    )
    _compare("projects", expected, actual)


def verify_survey_sets(
    survey_sets: Sequence[SurveySetSnapshot],
    responses: Iterable[tuple[Query, Any]],
) -> None:
    expected: Counter[Hashable] = Counter()
    for query, raw in responses:
        expected.update(_read_counts(raw, query, SURVEY_SET_CONTROL_FIELDS, _set_key))
    actual: Counter[Hashable] = Counter(
        ("" if s.survey_id is None else s.survey_id.key, s.survey_nps)
        for s in survey_sets
    )
    _compare("survey sets", expected, actual)


def _aggregate(sobject: str, fields: Sequence[str], where: str) -> str:
    columns = ", ".join(fields)
    order = ", ".join(f"{f} ASC" for f in fields)
    return (
        f"SELECT {columns}, COUNT(Id) {COUNT_ALIAS} FROM {sobject}{where} "
        f"GROUP BY {columns} ORDER BY {order} LIMIT {CONTROL_LIMIT}"
    )


def _project_key(record: Mapping[str, Any]) -> tuple[str, str, bool, str]:
    start, status, ignore, sub_type = (record.get(f) for f in PROJECT_CONTROL_FIELDS)
    if not isinstance(start, str) or not isinstance(ignore, bool):
        raise ReaderError(f"Unexpected control row: {dict(record)!r}")
    return (start, _text(status), ignore, _text(sub_type))


def _set_key(record: Mapping[str, Any]) -> tuple[str, bool]:
    survey, nps = (record.get(f) for f in SURVEY_SET_CONTROL_FIELDS)
    if not isinstance(nps, bool):
        raise ReaderError(f"Unexpected control row: {dict(record)!r}")
    if survey is None:
        return ("", nps)
    try:
        return (SalesforceId(survey).key, nps)
    except DomainError:
        raise ReaderError(f"Unexpected control row: {dict(record)!r}") from None


def _read_counts(
    raw: Any,
    query: Query,
    fields: Sequence[str],
    key: Any,
) -> Counter[Hashable]:
    counts: Counter[Hashable] = Counter()
    for record in query_records(raw, query):
        missing = [f for f in (*fields, COUNT_ALIAS) if f not in record]
        if missing:
            raise ReaderError(f"Control row of {query.name} lacks {', '.join(missing)}")
        number = record[COUNT_ALIAS]
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise ReaderError(f"Control row of {query.name} has count {number!r}")
        counts[key(record)] += number
    return counts


def _compare(
    label: str, expected: Counter[Hashable], actual: Counter[Hashable]
) -> None:
    if expected == actual:
        return
    differences = [
        f"{group}: Salesforce {expected.get(group, 0)}, guardado {actual.get(group, 0)}"
        for group in sorted(set(expected) | set(actual), key=repr)
        if expected.get(group, 0) != actual.get(group, 0)
    ]
    raise ControlMismatchError(
        f"Los {label} guardados no coinciden con el control de Salesforce "
        f"({sum(expected.values())} vs {sum(actual.values())}): "
        + "; ".join(differences[:10])
    )


def _text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ReaderError(f"Unexpected control value {value!r}")
    return value
