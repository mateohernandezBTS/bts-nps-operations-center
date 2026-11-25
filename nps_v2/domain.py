"""Pure domain types for the V2 engine.

Values here are already validated and typed. Translation from connector JSON lives in
``nps_v2.salesforce.readers`` and translation to the certified engine dialect lives in
``nps_v2.adapters``; neither concern leaks into these types.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

_SALESFORCE_ID = re.compile(r"[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?")


class DomainError(ValueError):
    """A value violates a domain invariant."""


@dataclass(frozen=True, slots=True)
class SalesforceId:
    """A 15- or 18-character Salesforce record Id.

    Two Ids are equal when their case-sensitive 15-character prefixes are equal, which
    is how Salesforce itself relates both forms.
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _SALESFORCE_ID.fullmatch(self.value):
            raise DomainError(f"Invalid Salesforce Id: {self.value!r}")

    @property
    def key(self) -> str:
        return self.value[:15]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SalesforceId):
            return NotImplemented
        return self.key == other.key

    def __hash__(self) -> int:
        return hash(self.key)

    def __str__(self) -> str:
        return self.value


class SurveyKind(StrEnum):
    """The two survey kinds every eligible project needs."""

    NPS = "NPS"
    FACILITATORS = "FACILITATORS"


class SurveyState(StrEnum):
    """Survey situation of an eligible project, evaluated per kind."""

    PENDING_BOTH = "PENDING_BOTH"
    PENDING_NPS = "PENDING_NPS"
    PENDING_FACILITATORS = "PENDING_FACILITATORS"
    COMPLETE = "COMPLETE"

    @classmethod
    def from_presence(cls, *, has_nps: bool, has_facilitators: bool) -> SurveyState:
        if has_nps and has_facilitators:
            return cls.COMPLETE
        if has_nps:
            return cls.PENDING_FACILITATORS
        if has_facilitators:
            return cls.PENDING_NPS
        return cls.PENDING_BOTH

    @property
    def missing_kinds(self) -> tuple[SurveyKind, ...]:
        return {
            SurveyState.PENDING_BOTH: (SurveyKind.NPS, SurveyKind.FACILITATORS),
            SurveyState.PENDING_NPS: (SurveyKind.NPS,),
            SurveyState.PENDING_FACILITATORS: (SurveyKind.FACILITATORS,),
            SurveyState.COMPLETE: (),
        }[self]


@dataclass(frozen=True, slots=True)
class ProjectSnapshot:
    """One ``rosscrooke__Project__c`` record as read from Salesforce.

    Values are kept exactly as read. Doubtful data (for example an end date before the
    start date) is not rejected here: one bad record must go to manual review, never
    abort the whole run.
    """

    project_id: SalesforceId
    name: str
    billing_country: str
    start_date: date
    end_date: date | None
    client_name: str
    sub_type: str
    status: str
    all_staffings: str
    ignore_reporting: bool
    survey_invitation_id: SalesforceId | None = None


@dataclass(frozen=True, slots=True)
class SurveySetSnapshot:
    """One ``Survey_Set__c`` record as read from Salesforce."""

    survey_set_id: SalesforceId
    project_id: SalesforceId
    survey_id: SalesforceId | None
    language: str
    survey_nps: bool
    invitation_link: str
    qr_code_url: str
    created_at: datetime
