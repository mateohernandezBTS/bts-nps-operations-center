"""Which surveys each project already has (D-V2-7: detection by family).

* NPS present ⇔ a Survey Set with ``SurveyNPS__c = true`` (standard or client-specific).
* Facilitators present ⇔ a Survey Set whose survey is in the configured facilitator
  family.
* Anything else is an *other* survey: shown, but it never satisfies a kind.

Doubtful data never changes the state silently; it becomes a warning for the preview.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from nps_v2.domain import (
    ProjectSnapshot,
    SalesforceId,
    SurveyKind,
    SurveySetSnapshot,
    SurveyState,
)
from nps_v2.registry import CountryRegistry

# Same image the Salesforce formula fields QR_Code__c / QR_Code_Image__c render;
# QR_Code_URL__c already holds the URL-encoded invitation link.
QR_IMAGE_URL_TEMPLATE = (
    "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={data}"
)

SLACK_QR_COLUMN = "QR-Code"
SLACK_NPS_LINK_COLUMN = "Link NPS Survey"
SLACK_FACILITATORS_LINK_COLUMN = "Link Insights Facilitators"


class SurveyStateError(ValueError):
    """Survey sets do not belong to the projects that were queried."""


def survey_kind(
    survey_set: SurveySetSnapshot, registry: CountryRegistry
) -> SurveyKind | None:
    if survey_set.survey_nps:
        return SurveyKind.NPS
    if registry.is_facilitator_survey(survey_set.survey_id):
        return SurveyKind.FACILITATORS
    return None


def qr_image_url(survey_set: SurveySetSnapshot) -> str:
    data = survey_set.qr_code_url.strip()
    return QR_IMAGE_URL_TEMPLATE.format(data=data) if data else ""


@dataclass(frozen=True, slots=True)
class ProjectSurveys:
    project_id: SalesforceId
    state: SurveyState
    nps_sets: tuple[SurveySetSnapshot, ...]
    facilitator_sets: tuple[SurveySetSnapshot, ...]
    other_sets: tuple[SurveySetSnapshot, ...]
    nps: SurveySetSnapshot | None
    facilitators: SurveySetSnapshot | None
    warnings: tuple[str, ...]

    def slack_columns(self) -> dict[str, str]:
        """QR and links for the Slack table; empty when the survey does not exist."""
        return {
            SLACK_QR_COLUMN: qr_image_url(self.nps) if self.nps else "",
            SLACK_NPS_LINK_COLUMN: self.nps.invitation_link if self.nps else "",
            SLACK_FACILITATORS_LINK_COLUMN: (
                self.facilitators.invitation_link if self.facilitators else ""
            ),
        }


def derive_survey_states(
    projects: Sequence[ProjectSnapshot],
    survey_sets: Iterable[SurveySetSnapshot],
    registry: CountryRegistry,
) -> dict[SalesforceId, ProjectSurveys]:
    by_project: dict[SalesforceId, list[SurveySetSnapshot]] = defaultdict(list)
    known = {p.project_id for p in projects}
    for survey_set in survey_sets:
        if survey_set.project_id not in known:
            raise SurveyStateError(
                f"Survey set {survey_set.survey_set_id} belongs to project "
                f"{survey_set.project_id}, which was not queried"
            )
        by_project[survey_set.project_id].append(survey_set)

    return {
        project.project_id: _project_surveys(
            project, by_project.get(project.project_id, []), registry
        )
        for project in projects
    }


def _project_surveys(
    project: ProjectSnapshot,
    survey_sets: Sequence[SurveySetSnapshot],
    registry: CountryRegistry,
) -> ProjectSurveys:
    grouped: Mapping[SurveyKind | None, list[SurveySetSnapshot]] = _group(
        survey_sets, registry
    )
    nps_sets = tuple(grouped.get(SurveyKind.NPS, []))
    facilitator_sets = tuple(grouped.get(SurveyKind.FACILITATORS, []))
    other_sets = tuple(grouped.get(None, []))

    warnings: list[str] = []
    nps = _pick_nps(project, nps_sets)
    facilitators = facilitator_sets[0] if facilitator_sets else None

    for kind, sets in (
        (SurveyKind.NPS, nps_sets),
        (SurveyKind.FACILITATORS, facilitator_sets),
    ):
        if len(sets) > 1:
            warnings.append(f"{len(sets)} {_label(kind)} surveys (possible duplicate)")

    country = registry.country_for_billing(project.billing_country)
    for survey_set in (*nps_sets, *facilitator_sets):
        name = survey_set.survey_name or str(survey_set.survey_id or "no survey")
        if not survey_set.language:
            warnings.append(f"{name}: language is empty")
        elif country is not None and survey_set.language != country.language:
            warnings.append(
                f"{name}: language {survey_set.language}, the country uses "
                f"{country.language}"
            )
        if not survey_set.invitation_link:
            warnings.append(f"{name}: no invitation link")
    for survey_set in nps_sets:
        if registry.is_facilitator_survey(survey_set.survey_id):
            warnings.append(
                f"{survey_set.survey_name or survey_set.survey_id}: "
                "flagged as NPS but it is a facilitators survey"
            )

    return ProjectSurveys(
        project_id=project.project_id,
        state=SurveyState.from_presence(
            has_nps=bool(nps_sets), has_facilitators=bool(facilitator_sets)
        ),
        nps_sets=nps_sets,
        facilitator_sets=facilitator_sets,
        other_sets=other_sets,
        nps=nps,
        facilitators=facilitators,
        warnings=tuple(warnings),
    )


def _group(
    survey_sets: Sequence[SurveySetSnapshot], registry: CountryRegistry
) -> dict[SurveyKind | None, list[SurveySetSnapshot]]:
    grouped: dict[SurveyKind | None, list[SurveySetSnapshot]] = defaultdict(list)
    for survey_set in sorted(
        survey_sets, key=lambda s: (s.created_at, s.survey_set_id.key)
    ):
        grouped[survey_kind(survey_set, registry)].append(survey_set)
    return grouped


def _pick_nps(
    project: ProjectSnapshot, nps_sets: Sequence[SurveySetSnapshot]
) -> SurveySetSnapshot | None:
    """The set the project's invitation points to; otherwise the oldest one."""
    if not nps_sets:
        return None
    invitation = project.survey_invitation_id
    if invitation is not None:
        for survey_set in nps_sets:
            # The 15-character key also matches links that carry the 18-character Id.
            if f"invitationId={invitation.key}" in survey_set.invitation_link:
                return survey_set
    return nps_sets[0]


def _label(kind: SurveyKind) -> str:
    return "NPS" if kind is SurveyKind.NPS else "facilitators"
