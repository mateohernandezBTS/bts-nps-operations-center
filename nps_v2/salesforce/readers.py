"""Connector JSON → domain snapshots.

The connector returns ``{"totalSize": n, "done": true, "records": [...]}`` with one
``attributes`` object per record. Readers are strict: a response that is incomplete,
truncated or not shaped as expected raises :class:`ReaderError`, so a broken read can
never look like "nothing pending". Empty text fields become ``""``; the certified
stages decide later whether that is a problem for the record.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Any

from nps_v2.domain import (
    DomainError,
    ProjectSnapshot,
    SalesforceId,
    SurveySetSnapshot,
)
from nps_v2.salesforce.queries import PROJECT_OBJECT, SURVEY_SET_OBJECT, Query


class ReaderError(ValueError):
    """A connector response cannot be trusted."""


def query_records(raw: Any, query: Query) -> list[Mapping[str, Any]]:
    """Validate the response envelope of ``query`` and return its records."""
    where = f"Response of {query.name}"
    if not isinstance(raw, Mapping):
        raise ReaderError(f"{where} is not a JSON object")
    if raw.get("done") is not True:
        raise ReaderError(f"{where} is incomplete (done is not true); do not paginate")
    records = raw.get("records")
    if not isinstance(records, list) or not all(
        isinstance(r, Mapping) for r in records
    ):
        raise ReaderError(f"{where} has no records list")
    total = raw.get("totalSize")
    if not isinstance(total, int) or isinstance(total, bool) or total != len(records):
        raise ReaderError(
            f"{where}: totalSize {total!r} does not match {len(records)} records"
        )
    if len(records) >= query.limit:
        raise ReaderError(
            f"{where} reached its limit of {query.limit} rows and may be truncated; "
            "narrow the selection"
        )
    return records


def read_projects(raw: Any, query: Query) -> list[ProjectSnapshot]:
    projects = [
        _project(record, index)
        for index, record in enumerate(query_records(raw, query), start=1)
    ]
    _ensure_unique((p.project_id for p in projects), "project")
    return projects


def read_survey_sets(
    responses: Iterable[tuple[Query, Any]],
) -> list[SurveySetSnapshot]:
    """Read every survey-set chunk response into one list."""
    survey_sets = [
        _survey_set(record, index)
        for query, raw in responses
        for index, record in enumerate(query_records(raw, query), start=1)
    ]
    _ensure_unique((s.survey_set_id for s in survey_sets), "survey set")
    return survey_sets


def _project(record: Mapping[str, Any], index: int) -> ProjectSnapshot:
    row = _Row(record, PROJECT_OBJECT, index)
    return ProjectSnapshot(
        project_id=row.salesforce_id("Id"),
        name=row.text("Name"),
        billing_country=row.text("Billing_Country__c"),
        start_date=row.required_date("rosscrooke__Start_Date__c"),
        end_date=row.optional_date("rosscrooke__End_Date__c"),
        client_name=row.text("rosscrooke__Client_Name__c"),
        sub_type=row.text("Project_Sub_Type__c"),
        status=row.text("rosscrooke__Status__c"),
        all_staffings=row.text("All_Staffings__c"),
        ignore_reporting=row.boolean("rosscrooke__Ignore_Reporting__c"),
        survey_invitation_id=row.optional_salesforce_id("Survey_Invitation__c"),
    )


def _survey_set(record: Mapping[str, Any], index: int) -> SurveySetSnapshot:
    row = _Row(record, SURVEY_SET_OBJECT, index)
    return SurveySetSnapshot(
        survey_set_id=row.salesforce_id("Id"),
        project_id=row.salesforce_id("Project__c"),
        survey_id=row.optional_salesforce_id("Survey__c"),
        survey_name=row.related_text("Survey__r", "Name"),
        language=row.text("Survey_Language__c"),
        survey_nps=row.boolean("SurveyNPS__c"),
        invitation_link=row.text("Survey_Invitation_Link__c"),
        qr_code_url=row.text("QR_Code_URL__c"),
        created_at=row.required_datetime("CreatedDate"),
    )


class _Row:
    """Typed access to one connector record; every failure names the field."""

    def __init__(self, record: Mapping[str, Any], sobject: str, index: int) -> None:
        self._record = record
        self._where = f"{sobject} record #{index}"
        attributes = record.get("attributes")
        if isinstance(attributes, Mapping) and attributes.get("type") not in (
            None,
            sobject,
        ):
            raise ReaderError(
                f"{self._where} has type {attributes.get('type')!r}, expected {sobject}"
            )

    def _value(self, field: str) -> Any:
        if field not in self._record:
            raise ReaderError(f"{self._where} is missing field {field}")
        return self._record[field]

    def _fail(self, field: str, expected: str, value: Any) -> ReaderError:
        return ReaderError(f"{self._where}: {field} must be {expected}, got {value!r}")

    def text(self, field: str) -> str:
        value = self._value(field)
        if value is None:
            return ""
        if not isinstance(value, str):
            raise self._fail(field, "text or null", value)
        return value

    def related_text(self, relation: str, field: str) -> str:
        related = self._record.get(relation)
        if related is None:
            return ""
        if not isinstance(related, Mapping):
            raise self._fail(relation, "an object or null", related)
        value = related.get(field)
        if value is None:
            return ""
        if not isinstance(value, str):
            raise self._fail(f"{relation}.{field}", "text or null", value)
        return value

    def boolean(self, field: str) -> bool:
        value = self._value(field)
        if not isinstance(value, bool):
            raise self._fail(field, "true or false", value)
        return value

    def salesforce_id(self, field: str) -> SalesforceId:
        value = self._value(field)
        try:
            return SalesforceId(value)
        except DomainError:
            raise self._fail(field, "a Salesforce Id", value) from None

    def optional_salesforce_id(self, field: str) -> SalesforceId | None:
        return None if self._value(field) is None else self.salesforce_id(field)

    def required_date(self, field: str) -> date:
        value = self._value(field)
        if not isinstance(value, str):
            raise self._fail(field, "a YYYY-MM-DD date", value)
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise self._fail(field, "a YYYY-MM-DD date", value) from None

    def optional_date(self, field: str) -> date | None:
        return None if self._value(field) is None else self.required_date(field)

    def required_datetime(self, field: str) -> datetime:
        value = self._value(field)
        if not isinstance(value, str):
            raise self._fail(field, "a timestamp", value)
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            raise self._fail(field, "a timestamp", value) from None
        if parsed.tzinfo is None:
            raise self._fail(field, "a timestamp with time zone", value)
        return parsed


def _ensure_unique(ids: Iterable[SalesforceId], label: str) -> None:
    seen: set[SalesforceId] = set()
    for record_id in ids:
        if record_id in seen:
            raise ReaderError(f"Duplicate {label} Id {record_id} in connector response")
        seen.add(record_id)
