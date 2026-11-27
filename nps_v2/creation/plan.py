"""Creation plan: which surveys to create, built only from an Upcoming report.

One command per missing survey kind of each pending (eligible, ready) session. Excluded,
review and out-of-scope sessions are never planned, because they are not in the report's
``pending`` section. The plan has a canonical JSON form and a SHA-256 hash: the user
approves that hash, and nothing else can be executed with it (D-V2-12).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from nps_v2.domain import DomainError, SalesforceId, SurveyKind

PLAN_VERSION = "1.0"
KIND_ORDER = {SurveyKind.NPS: 0, SurveyKind.FACILITATORS: 1}


class PlanError(ValueError):
    """The plan cannot be built (bad report or exclusions)."""


@dataclass(frozen=True, slots=True)
class SurveyCommand:
    """Create one survey kind for one project (key: ``<project 15-char id>:<kind>``)."""

    key: str
    project_id: str
    project_name: str
    client: str
    country: str
    start_date: str
    kind: str
    survey_id: str
    survey_name: str
    language: str
    special_case: bool
    facilitators: str = ""  # shown on the plan page for a manual check
    salesforce_url: str = ""  # link to the project, for a manual check


@dataclass(frozen=True, slots=True)
class CreationPlan:
    run_id: str
    selection_label: str
    commands: tuple[SurveyCommand, ...]
    excluded_projects: tuple[str, ...]
    already_created: tuple[str, ...] = ()  # keys found in Salesforce by a re-check

    def canonical(self) -> dict[str, Any]:
        return {
            "version": PLAN_VERSION,
            "run_id": self.run_id,
            "selection": self.selection_label,
            "commands": [asdict(c) for c in self.commands],
            "excluded_projects": list(self.excluded_projects),
            "already_created": list(self.already_created),
        }

    @property
    def hash(self) -> str:
        text = json.dumps(
            self.canonical(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @property
    def short_hash(self) -> str:
        """What the user types to approve (first 12 hex characters)."""
        return self.hash[:12]

    def to_dict(self) -> dict[str, Any]:
        return {**self.canonical(), "hash": self.hash, "short_hash": self.short_hash}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CreationPlan:
        try:
            plan = cls(
                run_id=str(raw["run_id"]),
                selection_label=str(raw["selection"]),
                commands=tuple(SurveyCommand(**c) for c in raw["commands"]),
                excluded_projects=tuple(str(p) for p in raw["excluded_projects"]),
                already_created=tuple(str(k) for k in raw.get("already_created", ())),
            )
        except (KeyError, TypeError) as error:
            raise PlanError(f"Invalid plan document: {error}") from error
        if raw.get("hash") not in (None, plan.hash):
            raise PlanError("The plan was modified after it was built (hash mismatch)")
        return plan


def exclude_all_but(report: Mapping[str, Any], only: Iterable[str]) -> list[str]:
    """Project Ids to exclude so that the plan keeps only ``only`` (pilot runs).

    Every value must be a session with surveys to create, as for ``exclude``.
    """
    pending_ids = {
        _key(row["project_id"]): row["project_id"] for row in report["pending"]
    }
    keep = set()
    for value in only:
        key = _key(value)
        if key not in pending_ids:
            raise PlanError(
                f"Cannot keep {value!r}: it is not a session with surveys to create"
            )
        keep.add(key)
    if not keep:
        raise PlanError("--only needs at least one project Id")
    return [str(pid) for key, pid in pending_ids.items() if key not in keep]


def build_plan(
    report: Mapping[str, Any],
    *,
    exclude: Iterable[str] = (),
    already_created: Iterable[str] = (),
) -> CreationPlan:
    """Plan for the report. ``already_created``: command keys that a re-check found in
    Salesforce; they are left out and listed, so the plan (and its hash) changes."""
    pending: Sequence[Mapping[str, Any]] = report["pending"]
    pending_keys = {_key(row["project_id"]): row for row in pending}
    excluded = set()
    for value in exclude:
        key = _key(value)
        if key not in pending_keys:
            raise PlanError(
                f"Cannot exclude {value!r}: it is not a session with surveys to create"
            )
        excluded.add(key)

    existing = set(already_created)
    commands = []
    for row in pending:
        key = _key(row["project_id"])
        if key in excluded:
            continue
        for survey in row["surveys_to_create"]:
            kind = SurveyKind(survey["kind"])
            if f"{key}:{kind.value}" in existing:
                continue
            commands.append(
                SurveyCommand(
                    key=f"{key}:{kind.value}",
                    project_id=str(row["project_id"]),
                    project_name=str(row["project"]),
                    client=str(row["client"]),
                    country=str(row["country"]),
                    start_date=str(row["start_date"]),
                    kind=kind.value,
                    survey_id=str(survey["survey_id"]),
                    survey_name=str(survey["survey_name"]),
                    language=str(survey["language"]),
                    special_case=bool(row.get("special_case")),
                    facilitators=str(row.get("facilitators", "")),
                    salesforce_url=str(row.get("salesforce_url", "")),
                )
            )
    commands.sort(
        key=lambda c: (
            c.start_date,
            c.country,
            c.client,
            c.project_name,
            KIND_ORDER[SurveyKind(c.kind)],
        )
    )
    if len({c.key for c in commands}) != len(commands):
        raise PlanError("The report lists the same survey twice for one project")
    return CreationPlan(
        run_id=str(report["run_id"]),
        selection_label=str(report["selection"]["label"]),
        commands=tuple(commands),
        excluded_projects=tuple(
            sorted(str(pending_keys[k]["project_id"]) for k in excluded)
        ),
        already_created=tuple(sorted(existing)),
    )


def _key(value: object) -> str:
    try:
        return SalesforceId(str(value).strip()).key
    except DomainError as error:
        raise PlanError(f"Invalid project id {value!r}") from error
