"""Runs the certified stages on Salesforce snapshots.

Order: selection checks → text filters → report scope → legacy adapter →
``normalize_records`` → ``apply_business_rules`` → ``generate_worklist`` (weekly window
disabled, because the selection already bounded the dates). Nothing is dropped
silently: every project ends in exactly one bucket of :class:`PipelineResult`.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from engine.paths import config_path
from engine.stages.business_rules import apply_business_rules
from engine.stages.normalize import normalize_records
from engine.stages.worklist import generate_worklist, load_operational_config
from nps_v2.adapters import PROJECT_ID_KEY, to_legacy_record
from nps_v2.domain import ProjectSnapshot
from nps_v2.registry import CountryRegistry
from nps_v2.selection import Selection

DEFAULT_SCOPE_PATH_PARTS = ("v2", "report_scope.json")


class PipelineError(ValueError):
    """The input violates the query contract; the run must stop."""


class Decision(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    EXCLUDED = "EXCLUDED"
    REVIEW = "REVIEW"


@dataclass(frozen=True, slots=True)
class ReportScope:
    """Rows the subscribed reports never contained (D-V2-1). Matching ignores case."""

    excluded_statuses: frozenset[str]
    excluded_sub_types: frozenset[str]

    @classmethod
    def everything(cls) -> ReportScope:
        return cls(excluded_statuses=frozenset(), excluded_sub_types=frozenset())

    def reason(self, project: ProjectSnapshot) -> str | None:
        status = project.status.strip()
        if status.casefold() in self.excluded_statuses:
            return f"Outside the report scope: status {status}"
        sub_type = project.sub_type.strip()
        if sub_type.casefold() in self.excluded_sub_types:
            shown = sub_type or "(empty)"
            return f"Outside the report scope: sub-type {shown}"
        return None


def load_report_scope(path: Path | None = None) -> ReportScope:
    scope_path = path or config_path(*DEFAULT_SCOPE_PATH_PARTS)
    try:
        raw = json.loads(scope_path.read_text(encoding="utf-8"))
        statuses = raw["excluded_statuses"]
        sub_types = raw["excluded_sub_types"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise PipelineError(
            f"Cannot read report scope {scope_path}: {error}"
        ) from error
    for name, values in (
        ("excluded_statuses", statuses),
        ("excluded_sub_types", sub_types),
    ):
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise PipelineError(f"{name} must be a list of strings")
    return ReportScope(
        excluded_statuses=frozenset(v.strip().casefold() for v in statuses),
        excluded_sub_types=frozenset(v.strip().casefold() for v in sub_types),
    )


@dataclass(frozen=True, slots=True)
class OutOfScope:
    project: ProjectSnapshot
    country_code: str
    reason: str


@dataclass(frozen=True, slots=True)
class ClassifiedProject:
    project: ProjectSnapshot
    country_code: str
    decision: Decision
    decision_codes: tuple[str, ...]
    decision_reasons: tuple[str, ...]
    validation_issues: str


@dataclass(frozen=True, slots=True)
class WorklistEntry:
    project: ProjectSnapshot
    country_code: str
    row: Mapping[str, str]

    @property
    def ready(self) -> bool:
        return self.row.get("Output Status") == "READY"

    @property
    def issues(self) -> str:
        return self.row.get("Output Issues", "")


@dataclass(frozen=True, slots=True)
class PipelineResult:
    filtered_out: tuple[ProjectSnapshot, ...]
    out_of_scope: tuple[OutOfScope, ...]
    classified: tuple[ClassifiedProject, ...]
    worklist: tuple[WorklistEntry, ...]

    @property
    def excluded(self) -> tuple[ClassifiedProject, ...]:
        return tuple(c for c in self.classified if c.decision is Decision.EXCLUDED)

    @property
    def review(self) -> tuple[ClassifiedProject, ...]:
        return tuple(c for c in self.classified if c.decision is Decision.REVIEW)

    @property
    def ready(self) -> tuple[WorklistEntry, ...]:
        return tuple(entry for entry in self.worklist if entry.ready)

    @property
    def worklist_review(self) -> tuple[WorklistEntry, ...]:
        return tuple(entry for entry in self.worklist if not entry.ready)


def run_pipeline(
    projects: Sequence[ProjectSnapshot],
    selection: Selection,
    registry: CountryRegistry,
    scope: ReportScope,
    *,
    business_rules_config: dict[str, Any] | None = None,
    operational_config: dict[str, Any] | None = None,
) -> PipelineResult:
    countries = {p.project_id: _country_code(p, selection, registry) for p in projects}
    if len(countries) != len(projects):
        raise PipelineError("Duplicate project Ids in the input")

    filtered_out = tuple(p for p in projects if not selection.filters.matches(p))
    selected = [p for p in projects if selection.filters.matches(p)]

    out_of_scope = []
    in_scope = []
    for project in selected:
        reason = scope.reason(project)
        if reason is None:
            in_scope.append(project)
        else:
            out_of_scope.append(
                OutOfScope(project, countries[project.project_id], reason)
            )

    by_id = {str(p.project_id): p for p in in_scope}
    normalized, _ = normalize_records([to_legacy_record(p) for p in in_scope])
    rules = apply_business_rules(normalized, config=business_rules_config)

    classified = tuple(
        _classified(record, by_id, countries) for record in rules["classified"]
    )
    worklist = _worklist(rules["eligible"], by_id, countries, operational_config)

    return PipelineResult(
        filtered_out=filtered_out,
        out_of_scope=tuple(out_of_scope),
        classified=classified,
        worklist=worklist,
    )


def windowless_operational_config(
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Operational config with the weekly window off: the selection decides dates."""
    result = copy.deepcopy(dict(config or load_operational_config()))
    window = dict(result.get("weekly_window", {}))
    window["enabled"] = False
    result["weekly_window"] = window
    return result


def _country_code(
    project: ProjectSnapshot, selection: Selection, registry: CountryRegistry
) -> str:
    if not selection.contains(project.start_date):
        raise PipelineError(
            f"Project {project.project_id} starts on {project.start_date}, "
            "outside the selection; the query and the selection disagree"
        )
    country = registry.country_for_billing(project.billing_country)
    if country is None:
        raise PipelineError(
            f"Project {project.project_id} has billing country "
            f"{project.billing_country!r}, which is not in the registry"
        )
    if selection.country_codes and country.code not in selection.country_codes:
        raise PipelineError(
            f"Project {project.project_id} belongs to {country.code}, "
            "which the selection excludes"
        )
    return country.code


def _classified(
    record: Mapping[str, Any],
    by_id: Mapping[str, ProjectSnapshot],
    countries: Mapping[Any, str],
) -> ClassifiedProject:
    project = by_id[record[PROJECT_ID_KEY]]
    return ClassifiedProject(
        project=project,
        country_code=countries[project.project_id],
        decision=Decision(record["decision"]),
        decision_codes=_split(record.get("decision_codes", "")),
        decision_reasons=_split(record.get("decision_reasons", "")),
        validation_issues=str(record.get("validation_issues", "")),
    )


def _worklist(
    eligible: Sequence[Mapping[str, Any]],
    by_id: Mapping[str, ProjectSnapshot],
    countries: Mapping[Any, str],
    operational_config: Mapping[str, Any] | None,
) -> tuple[WorklistEntry, ...]:
    result = generate_worklist(
        [dict(record) for record in eligible],
        config=windowless_operational_config(operational_config),
    )
    rows = result["worklist"]
    if result["outside_window"] or len(rows) != len(eligible):
        raise PipelineError("Worklist stage dropped records; window must be disabled")
    entries = []
    for record, row in zip(eligible, rows, strict=True):
        project = by_id[record[PROJECT_ID_KEY]]
        entries.append(
            WorklistEntry(
                project=project,
                country_code=countries[project.project_id],
                row={str(k): str(v) for k, v in row.items()},
            )
        )
    return tuple(entries)


def _split(value: Any) -> tuple[str, ...]:
    return tuple(part.strip() for part in str(value).split(" | ") if part.strip())
