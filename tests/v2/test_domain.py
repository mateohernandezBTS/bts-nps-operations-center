"""Domain invariants of the V2 engine."""

from __future__ import annotations

import unittest
from datetime import date

from nps_v2.domain import (
    DomainError,
    ProjectSnapshot,
    SalesforceId,
    SurveyKind,
    SurveyState,
)

ID_18 = "a0gAA000001AbCdEAF"


class SalesforceIdTest(unittest.TestCase):
    def test_accepts_15_and_18_characters(self) -> None:
        for value in (ID_18, ID_18[:15]):
            with self.subTest(value=value):
                self.assertEqual(str(SalesforceId(value)), value)

    def test_15_and_18_forms_are_the_same_record(self) -> None:
        self.assertEqual(SalesforceId(ID_18), SalesforceId(ID_18[:15]))
        self.assertEqual(len({SalesforceId(ID_18), SalesforceId(ID_18[:15])}), 1)

    def test_comparison_is_case_sensitive(self) -> None:
        self.assertNotEqual(SalesforceId(ID_18), SalesforceId(ID_18.lower()))

    def test_rejects_invalid_values(self) -> None:
        for value in ("", "short", ID_18 + "X", ID_18[:16], "a0gAA000001AbC-EAF", None):
            with self.subTest(value=value):
                with self.assertRaises(DomainError):
                    SalesforceId(value)  # type: ignore[arg-type]


class SurveyStateTest(unittest.TestCase):
    def test_every_presence_combination(self) -> None:
        cases = {
            (False, False): (
                SurveyState.PENDING_BOTH,
                (SurveyKind.NPS, SurveyKind.FACILITATORS),
            ),
            (True, False): (
                SurveyState.PENDING_FACILITATORS,
                (SurveyKind.FACILITATORS,),
            ),
            (False, True): (SurveyState.PENDING_NPS, (SurveyKind.NPS,)),
            (True, True): (SurveyState.COMPLETE, ()),
        }
        for (has_nps, has_sp), (state, missing) in cases.items():
            with self.subTest(has_nps=has_nps, has_facilitators=has_sp):
                result = SurveyState.from_presence(
                    has_nps=has_nps, has_facilitators=has_sp
                )
                self.assertIs(result, state)
                self.assertEqual(result.missing_kinds, missing)


class ProjectSnapshotTest(unittest.TestCase):
    def test_doubtful_dates_are_kept_for_review_not_rejected(self) -> None:
        snapshot = ProjectSnapshot(
            project_id=SalesforceId(ID_18),
            name="Synthetic Session",
            billing_country="Argentina",
            start_date=date(2026, 12, 2),
            end_date=date(2026, 12, 1),
            client_name="Synthetic Client",
            sub_type="Workshop",
            status="Conf",
            all_staffings="Facilitator One",
            ignore_reporting=False,
        )
        self.assertEqual(snapshot.end_date, date(2026, 12, 1))
        self.assertIsNone(snapshot.survey_invitation_id)


if __name__ == "__main__":
    unittest.main()
