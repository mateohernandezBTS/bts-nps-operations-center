"""Outputs of a creation run (D-V2-2): result page, audit.json and the Excel log."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from nps_v2.creation.execution import ExecutionState
from nps_v2.creation.plan import CreationPlan
from nps_v2.creation.reconcile import SurveyOutcome, counts
from nps_v2.outputs.creation_pages import render_result_page
from nps_v2.outputs.xlsx import Sheet, write_xlsx

RESULT_PAGE = "result.html"
AUDIT_FILE = "audit.json"
LOG_FILE = "creation_log.xlsx"
SURVEY_COLUMNS = (
    "Date",
    "Country",
    "Client",
    "Session",
    "Kind",
    "Survey",
    "Language",
    "Status",
    "Note",
    "Link",
    "Invitation Id",
    "Survey Set Id",
    "Project Id",
    "Personalised e-mail",
)


@dataclass(frozen=True, slots=True)
class CreationOutputs:
    result_page: Path
    audit: Path
    log: Path


def write_creation_outputs(
    directory: Path,
    *,
    outcomes: Sequence[SurveyOutcome],
    plan: CreationPlan,
    state: ExecutionState,
    approved_at: str,
    reconciled_at: str,
    country_names: Mapping[str, str],
) -> CreationOutputs:
    directory.mkdir(parents=True, exist_ok=True)
    operator = state.operator_name or state.operator_id
    page = directory / RESULT_PAGE
    page.write_text(
        render_result_page(
            outcomes,
            plan=plan,
            operator=operator,
            run_error=state.error,
            country_names=country_names,
            generated_at=reconciled_at,
        ),
        encoding="utf-8",
    )
    audit = directory / AUDIT_FILE
    audit.write_text(
        json.dumps(
            {
                "run_id": plan.run_id,
                "selection": plan.selection_label,
                "plan_hash": plan.hash,
                "approved_at": approved_at,
                "reconciled_at": reconciled_at,
                "operator": {"id": state.operator_id, "name": state.operator_name},
                "run_status": state.status,
                "run_error": state.error,
                "counts": counts(outcomes),
                "surveys": [o.to_dict() for o in outcomes],
                "calls": state.log,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    log = write_xlsx(
        directory / LOG_FILE,
        [
            Sheet(
                name="Surveys",
                header=SURVEY_COLUMNS,
                rows=[_survey_row(o) for o in outcomes],
                widths=(12, 8, 28, 42, 13, 18, 9, 16, 50, 60, 20, 20, 20, 12),
            ),
            Sheet(
                name="Run",
                header=("Field", "Value"),
                rows=_run_rows(
                    outcomes, plan, state, operator, approved_at, reconciled_at
                ),
                widths=(24, 80),
            ),
        ],
    )
    return CreationOutputs(result_page=page, audit=audit, log=log)


def _survey_row(outcome: SurveyOutcome) -> list[str | bool]:
    command = outcome.command
    return [
        command.start_date,
        command.country,
        command.client,
        command.project_name,
        command.kind,
        command.survey_name,
        command.language,
        outcome.outcome.value,
        outcome.note,
        outcome.link,
        outcome.invitation_id,
        outcome.survey_set_id,
        command.project_id,
        command.special_case,
    ]


def _run_rows(
    outcomes: Sequence[SurveyOutcome],
    plan: CreationPlan,
    state: ExecutionState,
    operator: str,
    approved_at: str,
    reconciled_at: str,
) -> list[list[str | int]]:
    rows: list[list[str | int]] = [
        ["Run", plan.run_id],
        ["Selection", plan.selection_label],
        ["Approved plan (code)", plan.short_hash],
        ["Approved plan (full hash)", plan.hash],
        ["Approved at", approved_at],
        ["Created by", operator or "unknown"],
        ["Run status", state.status],
        ["Run error", state.error],
        ["Reconciled at", reconciled_at],
    ]
    rows += [[f"Surveys: {name}", value] for name, value in counts(outcomes).items()]
    rows += [["Removed from the plan", p] for p in plan.excluded_projects]
    rows += [["Already in Salesforce at the re-check", k] for k in plan.already_created]
    return rows
