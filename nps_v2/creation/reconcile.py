"""Reconcile: what really exists in Salesforce after an execution, per planned survey.

Never trusts the execution state alone: every "created" survey is confirmed by a fresh
read (its survey set with the recorded link and, for NPS, the project pointing to the
invitation). Nothing is ever deleted; partial items are reported for a manual fix.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from nps_v2.creation.execution import (
    CommandProgress,
    CommandStatus,
    ExecutionState,
    RunStatus,
)
from nps_v2.creation.plan import CreationPlan, SurveyCommand
from nps_v2.creation.recipe import PROJECT_OBJECT
from nps_v2.domain import ProjectSnapshot, SalesforceId, SurveySetSnapshot
from nps_v2.salesforce.control import build_survey_set_control_queries
from nps_v2.salesforce.queries import (
    Query,
    build_survey_set_queries,
    id_list,
)

AFTER_GROUP = "creation_after"
AFTER_PREFIX = "after_"
POINTER_QUERY = "after_projects"
POINTER_LIMIT = 2000


class Outcome(StrEnum):
    CREATED = "created"
    ALREADY_EXISTED = "already existed"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_RUN = "not run"


@dataclass(frozen=True, slots=True)
class SurveyOutcome:
    command: SurveyCommand
    outcome: Outcome
    invitation_id: str
    survey_set_id: str
    link: str
    note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.command.key,
            "project_id": self.command.project_id,
            "project": self.command.project_name,
            "client": self.command.client,
            "country": self.command.country,
            "start_date": self.command.start_date,
            "kind": self.command.kind,
            "survey": self.command.survey_name,
            "language": self.command.language,
            "special_case": self.command.special_case,
            "outcome": self.outcome.value,
            "invitation_id": self.invitation_id,
            "survey_set_id": self.survey_set_id,
            "link": self.link,
            "note": self.note,
        }


def after_queries(
    projects: Sequence[ProjectSnapshot], plan: CreationPlan
) -> list[Query]:
    """Fresh survey sets of every project of the run (data + control, like V2-1) and
    the project links of planned NPS surveys."""
    ids = [p.project_id for p in projects]
    pairs = zip(
        build_survey_set_queries(ids),
        build_survey_set_control_queries(ids),
        strict=True,
    )
    queries = [
        Query(name=f"{AFTER_PREFIX}{q.name}", soql=q.soql, limit=q.limit)
        for pair in pairs
        for q in pair
    ]
    nps = sorted(
        {SalesforceId(c.project_id) for c in plan.commands if c.kind == "NPS"}, key=str
    )
    if nps:
        queries.append(
            Query(
                name=POINTER_QUERY,
                soql=(
                    f"SELECT Id, Survey_Invitation__c FROM {PROJECT_OBJECT} "
                    f"WHERE Id IN ({id_list(nps)}) ORDER BY Id ASC "
                    f"LIMIT {POINTER_LIMIT}"
                ),
                limit=POINTER_LIMIT,
            )
        )
    return queries


def project_pointers(raw: Any) -> dict[str, str]:
    """15-char project key → 15-char invitation key (from the pointer query)."""
    records = raw.get("records") if isinstance(raw, Mapping) else None
    if not isinstance(records, list) or raw.get("done") is not True:
        raise ValueError("The project read-back is incomplete")
    pointers = {}
    for record in records:
        invitation = record.get("Survey_Invitation__c")
        pointers[SalesforceId(str(record["Id"])).key] = (
            SalesforceId(str(invitation)).key if invitation else ""
        )
    return pointers


def reconcile(
    plan: CreationPlan,
    state: ExecutionState,
    survey_sets: Sequence[SurveySetSnapshot],
    pointers: Mapping[str, str],
) -> list[SurveyOutcome]:
    by_id = {s.survey_set_id: s for s in survey_sets}
    outcomes = []
    for command in plan.commands:
        progress = state.commands.get(command.key) or CommandProgress(command.key)
        outcomes.append(_outcome(command, progress, state, by_id, pointers))
    return outcomes


def _outcome(
    command: SurveyCommand,
    progress: CommandProgress,
    state: ExecutionState,
    by_id: Mapping[SalesforceId, SurveySetSnapshot],
    pointers: Mapping[str, str],
) -> SurveyOutcome:
    def result(outcome: Outcome, note: str = "") -> SurveyOutcome:
        return SurveyOutcome(
            command,
            outcome,
            progress.invitation_id,
            progress.survey_set_id,
            progress.invitation_link,
            note or progress.note,
        )

    if progress.status == CommandStatus.SKIPPED.value:
        return result(Outcome.ALREADY_EXISTED)
    if progress.survey_set_id:
        found = by_id.get(SalesforceId(progress.survey_set_id))
        if found is None or found.invitation_link != progress.invitation_link:
            return result(
                Outcome.PARTIAL, "The survey set was not found as written on read-back"
            )
        if command.kind == "NPS":
            pointer = pointers.get(SalesforceId(command.project_id).key, "")
            if pointer != SalesforceId(progress.invitation_id).key:
                return result(
                    Outcome.PARTIAL,
                    "The survey exists, but the project does not point to its NPS "
                    "invitation; fix the project's Survey Invitation by hand",
                )
        return result(Outcome.CREATED, "")
    if progress.invitation_id:
        return result(
            Outcome.PARTIAL,
            f"Invitation {progress.invitation_id} was created without its survey set; "
            "finish or remove it by hand",
        )
    if progress.status == CommandStatus.FAILED.value:
        return result(Outcome.FAILED)
    if state.status == RunStatus.FAILED.value:
        return result(Outcome.NOT_RUN, "Not attempted: the run stopped before it")
    return result(Outcome.NOT_RUN, "Not attempted")


def counts(outcomes: Sequence[SurveyOutcome]) -> dict[str, int]:
    return {o.value: sum(1 for x in outcomes if x.outcome is o) for o in Outcome}
