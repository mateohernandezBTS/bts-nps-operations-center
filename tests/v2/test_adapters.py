"""Legacy adapter: Salesforce snapshot → e-mail parser dialect."""

from __future__ import annotations

import unittest
from datetime import date

from engine.stages.worklist import extract_salesforce_id
from nps_v2.adapters import (
    LEGACY_FIELDS,
    PROJECT_ID_KEY,
    legacy_date,
    to_legacy_record,
)
from nps_v2.domain import ProjectSnapshot, SalesforceId

PROJECT_ID = "a0gAA0000000001AAA"


def snapshot(**overrides: object) -> ProjectSnapshot:
    values: dict[str, object] = {
        "project_id": SalesforceId(PROJECT_ID),
        "name": "Synthetic Session",
        "billing_country": "Nexo",
        "start_date": date(2026, 8, 4),
        "end_date": date(2026, 12, 31),
        "client_name": "Synthetic Client",
        "sub_type": "Workshop",
        "status": "Conf",
        "all_staffings": "Facilitator One,Facilitator Two",
        "ignore_reporting": False,
        "survey_invitation_id": SalesforceId("0KiAA0000000001AAA"),
    }
    values.update(overrides)
    return ProjectSnapshot(**values)  # type: ignore[arg-type]


class LegacyFieldsTest(unittest.TestCase):
    def test_fields_match_the_certified_parser_contract(self) -> None:
        from engine.stages.email_parser import OUTPUT_COLUMNS

        self.assertEqual(list(LEGACY_FIELDS), OUTPUT_COLUMNS)

    def test_record_has_every_field_plus_the_join_key(self) -> None:
        record = to_legacy_record(snapshot())
        self.assertEqual(list(record), [*LEGACY_FIELDS, PROJECT_ID_KEY])
        self.assertEqual(record[PROJECT_ID_KEY], PROJECT_ID)


class ConversionTest(unittest.TestCase):
    def test_dates_use_month_day_year_without_padding(self) -> None:
        self.assertEqual(legacy_date(date(2026, 8, 4)), "8/4/2026")
        self.assertEqual(legacy_date(date(2026, 12, 31)), "12/31/2026")
        self.assertEqual(legacy_date(None), "")

    def test_values(self) -> None:
        record = to_legacy_record(snapshot())
        self.assertEqual(record["billing_office"], "Nexo")
        self.assertEqual(record["start_date"], "8/4/2026")
        self.assertEqual(record["end_date"], "12/31/2026")
        self.assertEqual(record["ignore_reporting"], "✕")
        self.assertEqual(record["survey_invitation"], "0KiAA0000000001AAA")
        self.assertEqual(record["evaluation_programme"], "")

    def test_ignore_reporting_true_and_missing_optionals(self) -> None:
        record = to_legacy_record(
            snapshot(ignore_reporting=True, end_date=None, survey_invitation_id=None)
        )
        self.assertEqual(record["ignore_reporting"], "✔")
        self.assertEqual((record["end_date"], record["survey_invitation"]), ("", ""))

    def test_certified_stage_reads_the_id_from_the_url(self) -> None:
        for project_id in (PROJECT_ID, PROJECT_ID[:15]):
            with self.subTest(project_id=project_id):
                record = to_legacy_record(snapshot(project_id=SalesforceId(project_id)))
                self.assertEqual(
                    extract_salesforce_id(record["project_url"]), project_id
                )


if __name__ == "__main__":
    unittest.main()
