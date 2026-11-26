"""Synthetic run scenario shared by report and output tests (no real data)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from nps_v2.domain import ProjectSnapshot, SalesforceId, SurveySetSnapshot
from nps_v2.pipeline import PipelineResult, load_report_scope, run_pipeline
from nps_v2.registry import CountryRegistry, load_registry
from nps_v2.report import RunContext, build_report
from nps_v2.selection import Selection, range_selection
from nps_v2.surveys.state import ProjectSurveys, derive_survey_states
from nps_v2.watchlist import Watchlist

NPS_STANDARD = "0Kd7V000000KymySAC"
NPS_BR = "0KdPP0000000PT30AM"
FACILITATORS_SP = "0KdPP0000000H450AE"
OTHER_SURVEY = "0KdAA0000000088AAA"
WATCHED = "Watched Facilitator"
CONTEXT = RunContext(run_id="V2-SYNTHETIC", generated_at="2026-11-26T10:00:00-03:00")


def _id(prefix: str, number: int) -> SalesforceId:
    return SalesforceId(f"{prefix}{number:010d}AAA")


def project(number: int, **overrides: Any) -> ProjectSnapshot:
    values: dict[str, Any] = {
        "project_id": _id("a0gAA", number),
        "name": f"Synthetic Session {number:02d}",
        "billing_country": "Argentina",
        "start_date": date(2026, 11, 24) + timedelta(days=number % 7),
        "end_date": None,
        "client_name": f"Synthetic Client {number:02d}",
        "sub_type": "Workshop",
        "status": "Conf",
        "all_staffings": "Facilitator One",
        "ignore_reporting": False,
    }
    values.update(overrides)
    return ProjectSnapshot(**values)


def survey_set(
    number: int,
    owner: ProjectSnapshot,
    survey: str | None,
    *,
    nps: bool,
    language: str = "es",
) -> SurveySetSnapshot:
    return SurveySetSnapshot(
        survey_set_id=_id("aHqAA", number),
        project_id=owner.project_id,
        survey_id=None if survey is None else SalesforceId(survey),
        survey_name={
            NPS_STANDARD: "Survey NPS",
            NPS_BR: "Survey NPS BR",
            FACILITATORS_SP: "Facilitators SP",
            OTHER_SURVEY: "Synthetic Pilot Survey",
        }.get(survey or "", ""),
        language=language,
        survey_nps=nps,
        invitation_link=f"https://example.invalid/survey?invitationId=INV{number}",
        qr_code_url=f"https%3A%2F%2Fexample.invalid%2Fsurvey%3FinvitationId%3DINV{number}",
        created_at=datetime(2026, 11, 20, tzinfo=UTC) + timedelta(minutes=number),
    )


@dataclass(frozen=True)
class Scenario:
    selection: Selection
    registry: CountryRegistry
    projects: list[ProjectSnapshot]
    survey_sets: list[SurveySetSnapshot]
    result: PipelineResult
    surveys: dict[SalesforceId, ProjectSurveys]
    report: dict[str, Any]


def scenario(*, watchlist: Watchlist | None = None) -> Scenario:
    complete = project(1, all_staffings=f"{WATCHED},Facilitator Two")
    only_nps = project(2, billing_country="Nexo", name="Sessão | Turma 2")
    nothing = project(3, billing_country="Mexico", all_staffings="PRELIM Selam")
    prelim_with_survey = project(4, status="Prelim")
    revenue = project(5, name="Synthetic Session 05 REVENUE")
    cancelled = project(6, billing_country="Brazil", status="Cancelled")
    other_only = project(7)
    projects = [
        complete,
        only_nps,
        nothing,
        prelim_with_survey,
        revenue,
        cancelled,
        other_only,
    ]
    survey_sets = [
        survey_set(1, complete, NPS_STANDARD, nps=True),
        survey_set(2, complete, FACILITATORS_SP, nps=False),
        survey_set(3, only_nps, NPS_BR, nps=True, language="es"),
        survey_set(4, prelim_with_survey, NPS_STANDARD, nps=True),
        survey_set(5, other_only, OTHER_SURVEY, nps=False),
    ]
    registry = load_registry()
    selection = range_selection(date(2026, 11, 24), date(2026, 11, 30))
    result = run_pipeline(projects, selection, registry, load_report_scope())
    surveys = derive_survey_states(projects, survey_sets, registry)
    report = build_report(
        context=CONTEXT,
        selection=selection,
        registry=registry,
        result=result,
        surveys=surveys,
        watchlist=Watchlist((WATCHED,)) if watchlist is None else watchlist,
    )
    return Scenario(selection, registry, projects, survey_sets, result, surveys, report)
