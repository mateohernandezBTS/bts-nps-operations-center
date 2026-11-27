"""Creation workflow on a run folder: plan → approve → re-check → execute → reconcile.

```text
<run>/creation/
  plan.json, plan.html      the plan and its preview (hash inside)
  approval.json             the hash the user approved, and when
  state.json                execution state (saved after every step)
  after/                    refreshed report, preview and Slack page (reconcile)
  result.html, audit.json, creation_log.xlsx
```

The re-check and reconcile queries go through ``queries.json`` like V2-1 (groups
``creation_recheck`` and ``creation_after``), so ``capture`` saves their responses.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from nps_v2.capture import ToolCall, tool_calls
from nps_v2.creation.execution import (
    WRITE_TOOLS,
    Call,
    ExecutionError,
    ExecutionState,
    apply_result,
    next_call,
    start,
)
from nps_v2.creation.plan import CreationPlan, PlanError, build_plan, exclude_all_but
from nps_v2.creation.recipe import SURVEY_SET_OBJECT, CreationConfig
from nps_v2.domain import SalesforceId, SurveyKind
from nps_v2.registry import CountryRegistry
from nps_v2.run_folder import RunFolder, RunFolderError
from nps_v2.salesforce.queries import Query, id_list

CREATION_DIRECTORY = "creation"
PLAN_FILE = "plan.json"
APPROVAL_FILE = "approval.json"
STATE_FILE = "state.json"
RECHECK_GROUP = "creation_recheck"
RECHECK_LIMIT = 2000


@dataclass(frozen=True, slots=True)
class CreationFolder:
    run: RunFolder

    @property
    def path(self) -> Path:
        return self.run.path / CREATION_DIRECTORY

    # --- report and plan --------------------------------------------------------
    def read_report(self) -> dict[str, Any]:
        path = self.run.path / "report.json"
        if not path.exists():
            raise RunFolderError("Missing report.json: run 'upcoming' first")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise RunFolderError("report.json is not a JSON object")
        return value

    def write_plan(self, plan: CreationPlan) -> None:
        self._write(PLAN_FILE, plan.to_dict())

    def read_plan(self) -> CreationPlan:
        return CreationPlan.from_dict(self._read(PLAN_FILE, "run 'plan' first"))

    # --- approval ---------------------------------------------------------------
    def write_approval(self, plan: CreationPlan, approved_at: str) -> None:
        self._write(
            APPROVAL_FILE,
            {
                "hash": plan.hash,
                "short_hash": plan.short_hash,
                "approved_at": approved_at,
            },
        )

    def approved_hash(self) -> str | None:
        if not (self.path / APPROVAL_FILE).exists():
            return None
        return str(self._read(APPROVAL_FILE, "")["hash"])

    def clear_approval(self) -> None:
        (self.path / APPROVAL_FILE).unlink(missing_ok=True)

    # --- execution state --------------------------------------------------------
    def has_state(self) -> bool:
        return (self.path / STATE_FILE).exists()

    def read_state(self) -> ExecutionState:
        return ExecutionState.from_dict(self._read(STATE_FILE, "run 'execute' first"))

    def write_state(self, state: ExecutionState) -> None:
        self._write(STATE_FILE, state.to_dict())

    # --- helpers ----------------------------------------------------------------
    def _write(self, name: str, value: Any) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def _read(self, name: str, hint: str) -> Any:
        path = self.path / name
        if not path.exists():
            raise RunFolderError(f"Missing creation/{name}: {hint}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise RunFolderError(f"creation/{name} is not JSON: {error}") from error


# --- plan and approval ---------------------------------------------------------


def make_plan(
    folder: CreationFolder, exclude: Iterable[str], only: Iterable[str] = ()
) -> CreationPlan:
    """Plan for the run. ``only`` (pilot) keeps just those sessions; it cannot be
    combined with ``exclude``."""
    if folder.has_state():
        raise ExecutionError(
            "This run already started creating surveys: use 'reconcile', then a new run"
        )
    exclude, only = list(exclude), list(only)
    if exclude and only:
        raise PlanError("Use either --exclude or --only, not both")
    report = folder.read_report()
    if only:
        exclude = exclude_all_but(report, only)
    plan = build_plan(report, exclude=exclude)
    folder.write_plan(plan)
    folder.clear_approval()
    return plan


def approve(folder: CreationFolder, code: str, approved_at: str) -> list[Query]:
    """Record the approval of exactly this plan and return the re-check query."""
    plan = folder.read_plan()
    given = code.strip().lower()
    if not given or given not in (plan.short_hash, plan.hash):
        raise ExecutionError(
            f"The code {code!r} does not match the current plan ({plan.short_hash}); "
            "show the plan again and ask for approval"
        )
    if not plan.commands:
        raise ExecutionError("The plan has no surveys to create")
    folder.write_approval(plan, approved_at)
    queries = [recheck_query(plan)]
    folder.run.write_queries(RECHECK_GROUP, queries)
    return queries


def recheck_query(plan: CreationPlan) -> Query:
    projects = sorted({SalesforceId(c.project_id) for c in plan.commands}, key=str)
    return Query(
        name="creation_recheck",
        soql=(
            f"SELECT Id, Project__c, Survey__c, SurveyNPS__c FROM {SURVEY_SET_OBJECT} "
            f"WHERE Project__c IN ({id_list(projects)}) ORDER BY Id ASC "
            f"LIMIT {RECHECK_LIMIT}"
        ),
        limit=RECHECK_LIMIT,
    )


def existing_keys(
    records: Sequence[Mapping[str, Any]], registry: CountryRegistry
) -> set[str]:
    """Command keys (``<project>:<kind>``) that already exist in Salesforce."""
    keys = set()
    for record in records:
        project = SalesforceId(str(record["Project__c"])).key
        if record.get("SurveyNPS__c") is True:
            keys.add(f"{project}:{SurveyKind.NPS.value}")
        survey = record.get("Survey__c")
        if survey and registry.is_facilitator_survey(SalesforceId(str(survey))):
            keys.add(f"{project}:{SurveyKind.FACILITATORS.value}")
    return keys


# --- execution -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExecuteOutcome:
    call: Call | None
    state: ExecutionState | None
    changed_plan: CreationPlan | None = None


def execute(
    folder: CreationFolder, config: CreationConfig, registry: CountryRegistry
) -> ExecuteOutcome:
    plan = folder.read_plan()
    if folder.has_state():
        state = folder.read_state()
        return ExecuteOutcome(next_call(state, plan, config, registry), state)
    if folder.approved_hash() != plan.hash:
        raise ExecutionError("The current plan is not approved: run 'approve' first")
    query = folder.run.read_queries(RECHECK_GROUP)[0]
    if query.soql != recheck_query(plan).soql:
        raise ExecutionError(
            "The re-check does not match the plan: run 'approve' again"
        )
    raw = folder.run.read_response(query)
    records = _records(raw, query)
    found = existing_keys(records, registry) & {c.key for c in plan.commands}
    if found:
        report = folder.read_report()
        changed = build_plan(
            report,
            exclude=plan.excluded_projects,
            already_created=[*plan.already_created, *found],
        )
        folder.write_plan(changed)
        folder.clear_approval()
        return ExecuteOutcome(None, None, changed_plan=changed)
    state = start(plan)
    folder.write_state(state)
    return ExecuteOutcome(next_call(state, plan, config, registry), state)


def record(
    folder: CreationFolder,
    config: CreationConfig,
    registry: CountryRegistry,
    *,
    transcript: Path | None,
    response_text: str | None,
    recorded_at: str,
) -> ExecuteOutcome:
    """Save the result of the current call (from the transcript or given by hand)."""
    plan = folder.read_plan()
    state = folder.read_state()
    call = next_call(state, plan, config, registry)
    if call is None:
        raise ExecutionError(f"The run has already finished ({state.status})")
    is_error = False
    if response_text is None:
        if transcript is None:
            raise ExecutionError("Give the transcript or the response text")
        matches = matching_calls(tool_calls(transcript), call)
        if not matches:
            raise ExecutionError(
                f"Step {call.step}: no '{call.tool}' call with exactly the printed "
                "input was found; run it exactly as printed, then 'record' again"
            )
        if call.writes and len(matches) > 1:
            state = apply_result(
                state,
                plan,
                config,
                registry,
                f"The write was executed {len(matches)} times",
                is_error=True,
                recorded_at=recorded_at,
            )
            folder.write_state(state)
            return ExecuteOutcome(None, state)
        latest = matches[-1]
        if latest.result_text is None:
            raise ExecutionError(f"Step {call.step}: the call has no result yet")
        response_text, is_error = latest.result_text, latest.is_error
    state = apply_result(
        state,
        plan,
        config,
        registry,
        response_text,
        is_error=is_error,
        recorded_at=recorded_at,
    )
    folder.write_state(state)
    return ExecuteOutcome(next_call(state, plan, config, registry), state)


def matching_calls(calls: Sequence[ToolCall], call: Call) -> list[ToolCall]:
    """Transcript calls of the same tool with exactly the same input."""
    expected = _canonical(call.input)
    return [
        c
        for c in calls
        if c.name.endswith(call.tool) and _canonical(c.input) == expected
    ]


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _records(raw: Any, query: Query) -> list[Mapping[str, Any]]:
    if not isinstance(raw, Mapping) or raw.get("done") is not True:
        raise RunFolderError(f"The response of {query.name} is incomplete")
    records = raw.get("records")
    if not isinstance(records, list):
        raise RunFolderError(f"The response of {query.name} has no records")
    if len(records) >= query.limit:
        raise RunFolderError(f"The response of {query.name} may be truncated")
    return records


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


__all__ = [
    "WRITE_TOOLS",
    "CreationFolder",
    "ExecuteOutcome",
    "PlanError",
    "approve",
    "execute",
    "existing_keys",
    "make_plan",
    "matching_calls",
    "now_iso",
    "record",
    "recheck_query",
]
