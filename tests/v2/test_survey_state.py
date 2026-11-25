"""Per-kind survey state, detection by family (D-V2-7), QR and links."""

from __future__ import annotations

import unittest
from datetime import UTC, date, datetime, timedelta
from itertools import count

from nps_v2.domain import ProjectSnapshot, SalesforceId, SurveyKind, SurveyState
from nps_v2.domain import SurveySetSnapshot as Set
from nps_v2.registry import load_registry
from nps_v2.surveys.state import (
    SurveyStateError,
    derive_survey_states,
    qr_image_url,
    survey_kind,
)

NPS_STANDARD = "0Kd7V000000KymySAC"
NPS_BR = "0KdPP0000000PT30AM"
FACILITATORS_SP = "0KdPP0000000H450AE"
FACILITATORS_VARIANT = "0KdPP0000000FOr0AM"
CLIENT_NPS = "0KdAA0000000077AAA"
OTHER_SURVEY = "0KdAA0000000088AAA"

_ids = count(1)
_base_time = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


def project(
    country: str = "Argentina", invitation: str | None = None
) -> ProjectSnapshot:
    return ProjectSnapshot(
        project_id=SalesforceId(f"a0gAA{next(_ids):010d}AAA"),
        name="Synthetic Session",
        billing_country=country,
        start_date=date(2026, 11, 26),
        end_date=None,
        client_name="Synthetic Client",
        sub_type="Workshop",
        status="Conf",
        all_staffings="Facilitator One",
        ignore_reporting=False,
        survey_invitation_id=None if invitation is None else SalesforceId(invitation),
    )


def survey_set(
    owner: ProjectSnapshot,
    survey_id: str | None,
    *,
    nps: bool,
    language: str = "es",
    invitation: str = "0KiAA0000000001AAA",
    minutes: int = 0,
    name: str = "",
) -> Set:
    number = next(_ids)
    link = f"https://example.invalid/survey?invitationId={invitation}&n={number}"
    return Set(
        survey_set_id=SalesforceId(f"aHqAA{number:010d}AAA"),
        project_id=owner.project_id,
        survey_id=None if survey_id is None else SalesforceId(survey_id),
        survey_name=name,
        language=language,
        survey_nps=nps,
        invitation_link=link,
        qr_code_url=f"https%3A%2F%2Fexample.invalid%2Fsurvey%3Fn%3D{number}",
        created_at=_base_time + timedelta(minutes=minutes),
    )


class SurveyKindTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_registry()
        self.owner = project()

    def test_detection_by_family(self) -> None:
        cases = {
            "standard nps": (NPS_STANDARD, True, SurveyKind.NPS),
            "client-specific nps": (CLIENT_NPS, True, SurveyKind.NPS),
            "facilitators sp": (FACILITATORS_SP, False, SurveyKind.FACILITATORS),
            "facilitators variant": (
                FACILITATORS_VARIANT,
                False,
                SurveyKind.FACILITATORS,
            ),
            "other survey": (OTHER_SURVEY, False, None),
            "no survey": (None, False, None),
        }
        for name, (survey_id, nps, expected) in cases.items():
            with self.subTest(case=name):
                result = survey_kind(
                    survey_set(self.owner, survey_id, nps=nps), self.registry
                )
                self.assertIs(result, expected)


class SurveyStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_registry()

    def state_of(self, owner: ProjectSnapshot, *sets: Set):  # type: ignore[no-untyped-def]
        return derive_survey_states([owner], sets, self.registry)[owner.project_id]

    def test_every_state(self) -> None:
        owner = project()
        nps = survey_set(owner, NPS_STANDARD, nps=True)
        sp = survey_set(owner, FACILITATORS_SP, nps=False)
        other = survey_set(owner, OTHER_SURVEY, nps=False)
        cases = {
            "nothing": ((), SurveyState.PENDING_BOTH),
            "only other survey": ((other,), SurveyState.PENDING_BOTH),
            "only nps": ((nps,), SurveyState.PENDING_FACILITATORS),
            "only facilitators": ((sp,), SurveyState.PENDING_NPS),
            "both": ((nps, sp, other), SurveyState.COMPLETE),
        }
        for name, (sets, expected) in cases.items():
            with self.subTest(case=name):
                self.assertIs(self.state_of(owner, *sets).state, expected)

    def test_client_specific_nps_counts_as_nps(self) -> None:
        owner = project()
        result = self.state_of(
            owner,
            survey_set(owner, CLIENT_NPS, nps=True),
            survey_set(owner, FACILITATORS_SP, nps=False),
        )
        self.assertIs(result.state, SurveyState.COMPLETE)
        self.assertEqual(result.warnings, ())

    def test_other_surveys_are_reported(self) -> None:
        owner = project()
        other = survey_set(owner, OTHER_SURVEY, nps=False, name="Synthetic Pilot")
        self.assertEqual(self.state_of(owner, other).other_sets, (other,))

    def test_slack_columns(self) -> None:
        owner = project()
        nps = survey_set(owner, NPS_STANDARD, nps=True)
        sp = survey_set(owner, FACILITATORS_SP, nps=False)
        columns = self.state_of(owner, nps, sp).slack_columns()
        self.assertEqual(columns["Link NPS Survey"], nps.invitation_link)
        self.assertEqual(columns["Link Insights Facilitators"], sp.invitation_link)
        self.assertEqual(columns["QR-Code"], qr_image_url(nps))
        empty = self.state_of(project()).slack_columns()
        self.assertEqual(set(empty.values()), {""})

    def test_qr_matches_the_salesforce_formula(self) -> None:
        owner = project()
        nps = survey_set(owner, NPS_STANDARD, nps=True)
        self.assertEqual(
            qr_image_url(nps),
            "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data="
            + nps.qr_code_url,
        )

    def test_nps_link_follows_the_project_invitation(self) -> None:
        invitation = "0KiAA0000000555AAA"
        owner = project(invitation=invitation[:15])
        older = survey_set(owner, NPS_STANDARD, nps=True, minutes=0)
        pointed = survey_set(
            owner, NPS_STANDARD, nps=True, minutes=5, invitation=invitation
        )
        result = self.state_of(owner, pointed, older)
        self.assertIs(result.nps, pointed)
        self.assertIn("2 encuestas de tipo NPS", result.warnings[0])

    def test_without_matching_invitation_the_oldest_wins(self) -> None:
        owner = project()
        newer = survey_set(owner, NPS_STANDARD, nps=True, minutes=9)
        oldest = survey_set(owner, NPS_STANDARD, nps=True, minutes=1)
        self.assertIs(self.state_of(owner, newer, oldest).nps, oldest)

    def test_data_quality_warnings(self) -> None:
        brazil = project(country="Nexo")
        result = self.state_of(
            brazil,
            survey_set(brazil, NPS_BR, nps=True, language="es", name="NPS BR"),
            survey_set(brazil, FACILITATORS_SP, nps=False, language="", name="SP"),
        )
        self.assertIs(result.state, SurveyState.COMPLETE)
        self.assertEqual(
            result.warnings,
            ("NPS BR: idioma es, el país usa pt-BR", "SP: idioma vacío"),
        )

    def test_nps_flag_on_a_facilitator_survey_is_flagged(self) -> None:
        owner = project()
        odd = survey_set(owner, FACILITATORS_SP, nps=True, name="Facilitators SP")
        result = self.state_of(owner, odd)
        self.assertIs(result.state, SurveyState.PENDING_FACILITATORS)
        self.assertIn("marcada como NPS pero es de facilitadores", result.warnings[-1])

    def test_missing_link_is_flagged(self) -> None:
        owner = project()
        nps = survey_set(owner, NPS_STANDARD, nps=True, name="NPS")
        broken = Set(
            **{**{f: getattr(nps, f) for f in Set.__slots__}, "invitation_link": ""}
        )
        self.assertIn(
            "NPS: sin link de invitación", self.state_of(owner, broken).warnings
        )

    def test_sets_of_unknown_projects_stop_the_run(self) -> None:
        stranger = project()
        with self.assertRaises(SurveyStateError):
            derive_survey_states(
                [project()],
                [survey_set(stranger, NPS_STANDARD, nps=True)],
                self.registry,
            )


if __name__ == "__main__":
    unittest.main()
