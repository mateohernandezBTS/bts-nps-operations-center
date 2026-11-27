"""Execution of an approved creation plan: one connector call at a time.

The engine never calls Salesforce. It prints the next call (tool and exact input),
Claude runs it, and ``record`` hands the result back. Each step validates its result
before the next one is printed, so a wrong answer stops the run before anything else
is written. Order:

1. preflight: ``salesforce_describe`` (compact) of the two objects V2 creates, to check
   the connector's user may create them (D-V2-4). The project update is not
   pre-checked (its describe is too large); if it fails, the survey already exists and
   ``reconcile`` reports the missing project link;
2. site check: the survey site (``Network``, the invitation's ``CommunityId``) must be
   visible to that user, or Salesforce rejects the invitation with "insufficient access
   rights on cross-reference id" (seen in the first pilot, 2026-11-27);
3. per planned survey: check it does not exist yet → create the invitation → read its
   generated link → create the survey set → (NPS) point the project to the invitation.

The state is plain data saved after every step, so a run can be inspected or resumed
and ``reconcile`` can report exactly what was written.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from nps_v2.creation.plan import CreationPlan, SurveyCommand
from nps_v2.creation.recipe import (
    INVITATION_OBJECT,
    PROJECT_OBJECT,
    SURVEY_SET_OBJECT,
    CreationConfig,
    RecipeError,
    invitation_fields,
    project_fields,
    survey_link,
    survey_set_fields,
)
from nps_v2.creation.responses import (
    ResponseError,
    created_id,
    describe_problems,
    query_records,
    update_ok,
)
from nps_v2.domain import SurveyKind
from nps_v2.registry import CountryRegistry
from nps_v2.salesforce.queries import soql_string

TOOL_DESCRIBE = "salesforce_describe"
TOOL_QUERY = "salesforce_query"
TOOL_CREATE = "salesforce_create"
TOOL_UPDATE = "salesforce_update"
WRITE_TOOLS = (TOOL_CREATE, TOOL_UPDATE)
STATE_VERSION = "1.0"


class ExecutionError(ValueError):
    """The execution cannot continue (wrong state or approval)."""


class StepKind(StrEnum):
    PREFLIGHT = "preflight"
    SITE_CHECK = "site_check"
    CHECK = "check"
    CREATE_INVITATION = "create_invitation"
    READ_INVITATION = "read_invitation"
    CREATE_SURVEY_SET = "create_survey_set"
    UPDATE_PROJECT = "update_project"


class RunStatus(StrEnum):
    RUNNING = "running"
    FAILED = "failed"
    DONE = "done"


class CommandStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    SKIPPED = "skipped"  # already existed in Salesforce at the check
    FAILED = "failed"  # nothing was written for it
    PARTIAL = "partial"  # something was written, not everything


@dataclass(slots=True)
class Step:
    kind: str
    key: str  # command key, or the object name for a preflight


@dataclass(slots=True)
class CommandProgress:
    key: str
    status: str = CommandStatus.PENDING.value
    invitation_id: str = ""
    invitation_link: str = ""
    survey_set_id: str = ""
    project_updated: bool = False
    note: str = ""


@dataclass(slots=True)
class ExecutionState:
    plan_hash: str
    steps: list[Step]
    commands: dict[str, CommandProgress]
    cursor: int = 0
    status: str = RunStatus.RUNNING.value
    operator_id: str = ""
    operator_name: str = ""
    error: str = ""
    log: list[dict[str, Any]] = field(default_factory=list)

    # --- persistence -----------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {"version": STATE_VERSION, **asdict(self)}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> ExecutionState:
        try:
            return cls(
                plan_hash=str(raw["plan_hash"]),
                steps=[Step(**s) for s in raw["steps"]],
                commands={
                    k: CommandProgress(**v) for k, v in dict(raw["commands"]).items()
                },
                cursor=int(raw["cursor"]),
                status=str(raw["status"]),
                operator_id=str(raw.get("operator_id", "")),
                operator_name=str(raw.get("operator_name", "")),
                error=str(raw.get("error", "")),
                log=list(raw.get("log", [])),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ExecutionError(f"Invalid execution state: {error}") from error

    @property
    def finished(self) -> bool:
        return self.status != RunStatus.RUNNING.value


@dataclass(frozen=True, slots=True)
class Call:
    """The next connector call: run ``tool`` with exactly ``input``."""

    step: int
    kind: str
    key: str
    tool: str
    input: dict[str, Any]
    description: str

    @property
    def writes(self) -> bool:
        return self.tool in WRITE_TOOLS

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "kind": self.kind,
            "key": self.key,
            "tool": self.tool,
            "input": self.input,
            "description": self.description,
            "writes_to_salesforce": self.writes,
        }


# --- planning the steps ----------------------------------------------------------


def start(plan: CreationPlan) -> ExecutionState:
    if not plan.commands:
        raise ExecutionError("The plan has no surveys to create")
    steps = [
        Step(StepKind.PREFLIGHT.value, INVITATION_OBJECT),
        Step(StepKind.PREFLIGHT.value, SURVEY_SET_OBJECT),
        Step(StepKind.SITE_CHECK.value, SITE_OBJECT),
    ]
    for command in plan.commands:
        kinds = [
            StepKind.CHECK,
            StepKind.CREATE_INVITATION,
            StepKind.READ_INVITATION,
            StepKind.CREATE_SURVEY_SET,
        ]
        if command.kind == SurveyKind.NPS.value:
            kinds.append(StepKind.UPDATE_PROJECT)
        steps.extend(Step(kind.value, command.key) for kind in kinds)
    return ExecutionState(
        plan_hash=plan.hash,
        steps=steps,
        commands={c.key: CommandProgress(c.key) for c in plan.commands},
    )


_PREFLIGHT_NEEDS = {
    INVITATION_OBJECT: (
        "create",
        (
            "Name",
            "SurveyId",
            "CommunityId",
            "OptionsAllowGuestUserResponse",
            "OptionsAllowParticipantAccessTheirResponse",
            "OptionsCollectAnonymousResponse",
        ),
    ),
    SURVEY_SET_OBJECT: (
        "create",
        (
            "Project__c",
            "Survey__c",
            "Survey_Language__c",
            "SurveyNPS__c",
            "IpAddress_Restricted__c",
            "Survey_Invitation__c",
            "Survey_Invitation_Link__c",
            "QR_Code_URL__c",
        ),
    ),
}


# --- the next call ---------------------------------------------------------------


def next_call(
    state: ExecutionState,
    plan: CreationPlan,
    config: CreationConfig,
    registry: CountryRegistry,
) -> Call | None:
    """The call to run now, or ``None`` when the run has finished."""
    _check_plan(state, plan)
    if state.finished:
        return None
    step = state.steps[state.cursor]
    kind = StepKind(step.kind)
    if kind is StepKind.PREFLIGHT:
        needs, _ = _PREFLIGHT_NEEDS[step.key]
        return Call(
            state.cursor,
            kind.value,
            step.key,
            TOOL_DESCRIBE,
            {"sobjectType": step.key, "compact": True},
            f"Check that you can {needs} {step.key} records (nothing is written).",
        )
    if kind is StepKind.SITE_CHECK:
        return Call(
            state.cursor,
            kind.value,
            step.key,
            TOOL_QUERY,
            {"query": _site_query(config)},
            "Check that you can use the survey site (nothing is written).",
        )
    command = _command(plan, step.key)
    progress = state.commands[step.key]
    label = f"{command.survey_name} for {command.project_name}"
    if kind is StepKind.CHECK:
        return Call(
            state.cursor,
            kind.value,
            step.key,
            TOOL_QUERY,
            {"query": _check_query(command, registry)},
            f"Check that {label} does not exist yet (nothing is written).",
        )
    if kind is StepKind.CREATE_INVITATION:
        data = invitation_fields(
            survey_id=command.survey_id,
            survey_name=command.survey_name,
            project_name=command.project_name,
            config=config,
        )
        return Call(
            state.cursor,
            kind.value,
            step.key,
            TOOL_CREATE,
            {"sobjectType": INVITATION_OBJECT, "data": data},
            f"WRITE: create the survey invitation {label}.",
        )
    if kind is StepKind.READ_INVITATION:
        return Call(
            state.cursor,
            kind.value,
            step.key,
            TOOL_QUERY,
            {"query": _invitation_query(progress.invitation_id)},
            "Read the link Salesforce generated for the new invitation.",
        )
    if kind is StepKind.CREATE_SURVEY_SET:
        data = survey_set_fields(
            project_id=command.project_id,
            survey_id=command.survey_id,
            language=command.language,
            kind=SurveyKind(command.kind),
            invitation_id=progress.invitation_id,
            link=progress.invitation_link,
            config=config,
        )
        return Call(
            state.cursor,
            kind.value,
            step.key,
            TOOL_CREATE,
            {"sobjectType": SURVEY_SET_OBJECT, "data": data},
            f"WRITE: create the survey set {label} with its link and QR.",
        )
    return Call(
        state.cursor,
        kind.value,
        step.key,
        TOOL_UPDATE,
        {
            "sobjectType": PROJECT_OBJECT,
            "id": command.project_id,
            "data": project_fields(progress.invitation_id),
        },
        f"WRITE: point the project {command.project_name} to its NPS invitation.",
    )


# --- applying a result -----------------------------------------------------------


def apply_result(
    state: ExecutionState,
    plan: CreationPlan,
    config: CreationConfig,
    registry: CountryRegistry,
    result_text: str | None,
    *,
    is_error: bool = False,
    recorded_at: str,
) -> ExecutionState:
    """Validate the result of the current call and move on (or stop)."""
    call = next_call(state, plan, config, registry)
    if call is None:
        raise ExecutionError(f"The run has already finished ({state.status})")
    state.log.append(
        {
            "step": call.step,
            "kind": call.kind,
            "key": call.key,
            "tool": call.tool,
            "input": call.input,
            "result": result_text,
            "is_error": is_error,
            "recorded_at": recorded_at,
        }
    )
    try:
        if is_error:
            raise ResponseError(f"The connector returned an error: {result_text!r}")
        _apply(state, plan, config, call, result_text)
    except (ResponseError, RecipeError) as error:
        _fail(state, call, str(error))
        return state
    _advance(state)
    return state


def _apply(
    state: ExecutionState,
    plan: CreationPlan,
    config: CreationConfig,
    call: Call,
    text: str | None,
) -> None:
    kind = StepKind(call.kind)
    if kind is StepKind.PREFLIGHT:
        needs, fields = _PREFLIGHT_NEEDS[call.key]
        problems = describe_problems(text, needs=needs, fields=fields)
        if problems:
            raise ResponseError(
                "Missing Salesforce permissions: " + "; ".join(problems)
            )
        return
    if kind is StepKind.SITE_CHECK:
        if len(query_records(text)) != 1:
            raise ResponseError(
                f"This user cannot use the survey site (Network {config.community_id})"
                ", so Salesforce would reject the invitations. Nothing was written. "
                "Ask a Salesforce admin to give this user access to the site."
            )
        return
    progress = state.commands[call.key]
    command = _command(plan, call.key)
    if kind is StepKind.CHECK:
        if query_records(text):
            progress.status = CommandStatus.SKIPPED.value
            progress.note = "Already in Salesforce at the check; nothing written"
        return
    if kind is StepKind.CREATE_INVITATION:
        progress.invitation_id = created_id(
            text, config.key_prefixes[INVITATION_OBJECT]
        )
        return
    if kind is StepKind.READ_INVITATION:
        records = query_records(text)
        if len(records) != 1 or str(records[0].get("Id")) != progress.invitation_id:
            raise ResponseError("The new invitation could not be read back")
        record = records[0]
        link = record.get("InvitationLink")
        if not isinstance(link, str):
            raise ResponseError("The new invitation has no link")
        progress.invitation_link = survey_link(
            link, progress.invitation_id, command.language
        )
        _set_operator(state, record)
        return
    if kind is StepKind.CREATE_SURVEY_SET:
        progress.survey_set_id = created_id(
            text, config.key_prefixes[SURVEY_SET_OBJECT]
        )
        if command.kind != SurveyKind.NPS.value:
            progress.status = CommandStatus.DONE.value
        return
    update_ok(text)
    progress.project_updated = True
    progress.status = CommandStatus.DONE.value


def _set_operator(state: ExecutionState, record: Mapping[str, Any]) -> None:
    operator_id = str(record.get("CreatedById") or "")
    created_by = record.get("CreatedBy")
    name = str(created_by.get("Name", "")) if isinstance(created_by, Mapping) else ""
    if not operator_id:
        raise ResponseError("The new invitation has no creator")
    if state.operator_id and state.operator_id != operator_id:
        raise ResponseError("The records are being created by a different user")
    state.operator_id, state.operator_name = operator_id, name


def _fail(state: ExecutionState, call: Call, message: str) -> None:
    state.status = RunStatus.FAILED.value
    state.error = f"Step {call.step} ({call.kind}): {message}"
    if call.kind not in _RUN_CHECKS:
        progress = state.commands[call.key]
        wrote = bool(progress.invitation_id)
        progress.status = (
            CommandStatus.PARTIAL.value if wrote else CommandStatus.FAILED.value
        )
        progress.note = message


def _advance(state: ExecutionState) -> None:
    state.cursor += 1
    while state.cursor < len(state.steps):
        step = state.steps[state.cursor]
        if step.kind in _RUN_CHECKS:
            return
        if state.commands[step.key].status != CommandStatus.SKIPPED.value:
            return
        state.cursor += 1
    state.status = RunStatus.DONE.value


_RUN_CHECKS = (StepKind.PREFLIGHT.value, StepKind.SITE_CHECK.value)
SITE_OBJECT = "Network"


def _site_query(config: CreationConfig) -> str:
    return f"SELECT Id FROM {SITE_OBJECT} WHERE Id = {soql_string(config.community_id)}"


def _check_plan(state: ExecutionState, plan: CreationPlan) -> None:
    if state.plan_hash != plan.hash:
        raise ExecutionError("The execution state belongs to another plan")


def _command(plan: CreationPlan, key: str) -> SurveyCommand:
    for command in plan.commands:
        if command.key == key:
            return command
    raise ExecutionError(f"Unknown command {key!r}")


def _check_query(command: SurveyCommand, registry: CountryRegistry) -> str:
    project = soql_string(command.project_id)
    if command.kind == SurveyKind.NPS.value:
        condition = "SurveyNPS__c = true"
    else:
        family = ", ".join(
            soql_string(str(s)) for s in sorted(registry.facilitator_family, key=str)
        )
        condition = f"Survey__c IN ({family})"
    return (
        f"SELECT Id FROM {SURVEY_SET_OBJECT} WHERE Project__c = {project} "
        f"AND {condition} LIMIT 10"
    )


def _invitation_query(invitation_id: str) -> str:
    return (
        "SELECT Id, InvitationLink, CreatedById, CreatedBy.Name "
        f"FROM {INVITATION_OBJECT} WHERE Id = {soql_string(invitation_id)}"
    )
