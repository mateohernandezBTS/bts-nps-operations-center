"""Run report: every project of the selection, grouped for the product owner.

Pure data (JSON-serialisable dicts). Sections:

* ``pending`` — eligible, ready, and missing at least one survey kind;
* ``complete`` — eligible, ready, both kinds exist (QR and links filled);
* ``worklist_review`` — eligible but the worklist stage flagged it;
* ``review`` / ``excluded`` — decisions of the certified rules, with reasons;
* ``out_of_scope`` — rows the subscribed reports never contained;
* ``special_cases`` — eligible projects of watch-listed facilitators, with an ordered
  data package for a personalised e-mail;
* ``quality`` — data-quality notes (survey warnings, placeholder staffing, surveys on
  projects that are not eligible).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from nps_v2.adapters import project_url
from nps_v2.domain import ProjectSnapshot, SalesforceId, SurveyKind, SurveyState
from nps_v2.pipeline import PipelineResult, WorklistEntry
from nps_v2.registry import CountryRegistry
from nps_v2.selection import Selection, normalize_text
from nps_v2.surveys.state import ProjectSurveys, qr_image_url
from nps_v2.watchlist import Watchlist

REPORT_VERSION = "1.0"
PLACEHOLDER_STAFFING = "prelim selam"
KIND_LABEL = {SurveyKind.NPS: "NPS", SurveyKind.FACILITATORS: "Facilitadores"}


@dataclass(frozen=True, slots=True)
class RunContext:
    run_id: str
    generated_at: (
        str  # ISO timestamp supplied by the caller (keeps output deterministic)
    )


def build_report(
    *,
    context: RunContext,
    selection: Selection,
    registry: CountryRegistry,
    result: PipelineResult,
    surveys: Mapping[SalesforceId, ProjectSurveys],
    watchlist: Watchlist | None,
) -> dict[str, Any]:
    ready = result.ready
    pending = [
        e
        for e in ready
        if surveys[e.project.project_id].state is not SurveyState.COMPLETE
    ]
    complete = [
        e for e in ready if surveys[e.project.project_id].state is SurveyState.COMPLETE
    ]

    report: dict[str, Any] = {
        "version": REPORT_VERSION,
        "run_id": context.run_id,
        "generated_at": context.generated_at,
        "selection": selection.to_dict(),
        "watchlist_configured": watchlist is not None,
        "pending": [
            _pending(e, surveys[e.project.project_id], registry, watchlist)
            for e in pending
        ],
        "complete": [
            _complete(e, surveys[e.project.project_id], watchlist) for e in complete
        ],
        "worklist_review": [
            {**_base(e.project, e.country_code), "issues": e.issues}
            for e in result.worklist_review
        ],
        "review": [
            {**_base(c.project, c.country_code), "reasons": list(c.decision_reasons)}
            for c in result.review
        ],
        "excluded": [
            {
                **_base(c.project, c.country_code),
                "codes": list(c.decision_codes),
                "reasons": list(c.decision_reasons),
            }
            for c in result.excluded
        ],
        "out_of_scope": [
            {**_base(o.project, o.country_code), "reason": o.reason}
            for o in result.out_of_scope
        ],
        "filtered_out_count": len(result.filtered_out),
        "special_cases": _special_cases(ready, surveys, watchlist),
        "quality": _quality(result, surveys),
    }
    for section in (
        "pending",
        "complete",
        "worklist_review",
        "review",
        "excluded",
        "out_of_scope",
        "quality",
    ):
        report[section].sort(key=_display_order)
    report["summary"] = {
        "pending": len(report["pending"]),
        "complete": len(report["complete"]),
        "worklist_review": len(report["worklist_review"]),
        "review": len(report["review"]),
        "excluded": len(report["excluded"]),
        "out_of_scope": len(report["out_of_scope"]),
        "filtered_out": report["filtered_out_count"],
        "special_cases": len(report["special_cases"]),
        "quality_notes": len(report["quality"]),
        "surveys_to_create": sum(
            len(p["surveys_to_create"]) for p in report["pending"]
        ),
    }
    return report


def _display_order(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (row["start_date"], row["country"], row["client"], row["project"])


def _base(project: ProjectSnapshot, country_code: str) -> dict[str, Any]:
    return {
        "project_id": str(project.project_id),
        "country": country_code,
        "billing_country": project.billing_country,
        "start_date": project.start_date.isoformat(),
        "client": project.client_name,
        "project": project.name,
        "sub_type": project.sub_type,
        "status": project.status,
        "facilitators": project.all_staffings,
        "salesforce_url": project_url(project),
    }


def _links(state: ProjectSurveys) -> dict[str, str]:
    return {
        "nps_link": state.nps.invitation_link if state.nps else "",
        "qr_code": qr_image_url(state.nps) if state.nps else "",
        "facilitators_link": state.facilitators.invitation_link
        if state.facilitators
        else "",
    }


def _pending(
    entry: WorklistEntry,
    state: ProjectSurveys,
    registry: CountryRegistry,
    watchlist: Watchlist | None,
) -> dict[str, Any]:
    country = registry.by_code(entry.country_code)
    to_create = []
    for kind in state.state.missing_kinds:
        survey = (
            country.nps_survey
            if kind is SurveyKind.NPS
            else country.facilitators_survey
        )
        to_create.append(
            {
                "kind": kind.value,
                "label": KIND_LABEL[kind],
                "survey_name": survey.name,
                "survey_id": str(survey.survey_id),
                "language": country.language,
            }
        )
    return {
        **_base(entry.project, entry.country_code),
        "state": state.state.value,
        "surveys_to_create": to_create,
        **_links(state),
        "warnings": list(state.warnings),
        "special_case": bool(watchlist and watchlist.matches(entry.project)),
    }


def _complete(
    entry: WorklistEntry, state: ProjectSurveys, watchlist: Watchlist | None
) -> dict[str, Any]:
    return {
        **_base(entry.project, entry.country_code),
        "state": state.state.value,
        **_links(state),
        "warnings": list(state.warnings),
        "special_case": bool(watchlist and watchlist.matches(entry.project)),
    }


def _special_cases(
    ready: Sequence[WorklistEntry],
    surveys: Mapping[SalesforceId, ProjectSurveys],
    watchlist: Watchlist | None,
) -> list[dict[str, Any]]:
    if watchlist is None:
        return []
    cases = []
    for entry in sorted(
        ready, key=lambda e: (e.project.start_date, e.project.client_name)
    ):
        matched = watchlist.matches(entry.project)
        if matched:
            state = surveys[entry.project.project_id]
            cases.append(
                {
                    "matched_facilitators": list(matched),
                    **_base(entry.project, entry.country_code),
                    "state": state.state.value,
                    **_links(state),
                }
            )
    return cases


def _quality(
    result: PipelineResult, surveys: Mapping[SalesforceId, ProjectSurveys]
) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []

    def note(project: ProjectSnapshot, country: str, message: str) -> None:
        notes.append({**_base(project, country), "note": message})

    for entry in result.ready:
        state = surveys[entry.project.project_id]
        for warning in state.warnings:
            note(entry.project, entry.country_code, warning)
        if PLACEHOLDER_STAFFING in normalize_text(entry.project.all_staffings):
            note(entry.project, entry.country_code, "Facilitador sin asignar (PRELIM)")
        for other in state.other_sets:
            if other.survey_id is None:
                note(
                    entry.project,
                    entry.country_code,
                    "Survey Set sin encuesta asignada",
                )
            else:
                label = other.survey_name or str(other.survey_id)
                note(
                    entry.project,
                    entry.country_code,
                    f"Tiene además la encuesta {label}",
                )

    not_eligible = [
        (c.project, c.country_code, "; ".join(c.decision_reasons))
        for c in (*result.excluded, *result.review)
    ] + [(o.project, o.country_code, o.reason) for o in result.out_of_scope]
    for project, country, reason in not_eligible:
        state = surveys[project.project_id]
        if state.nps_sets or state.facilitator_sets:
            note(
                project,
                country,
                f"Tiene encuesta creada pero no es elegible ({reason})",
            )
    return notes
