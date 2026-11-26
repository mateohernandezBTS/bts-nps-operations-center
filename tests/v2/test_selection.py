"""Flexible selection: presets, adjustments, filters and serialisation."""

from __future__ import annotations

import unittest
from datetime import UTC, date, datetime, timedelta, timezone

from nps_v2.domain import ProjectSnapshot, SalesforceId
from nps_v2.selection import (
    MAX_SPAN_DAYS,
    SearchFilters,
    Selection,
    SelectionError,
    day_selection,
    range_selection,
    reference_monday,
    standard_week,
    standard_week_selection,
    today_in_buenos_aires,
)


def project(**overrides: object) -> ProjectSnapshot:
    values: dict[str, object] = {
        "project_id": SalesforceId("a0gAA000001AbCdEAF"),
        "name": "Liderazgo Ágil – Sesión 2",
        "billing_country": "Argentina",
        "start_date": date(2026, 11, 26),
        "end_date": None,
        "client_name": "Compañía Sintética S.A.",
        "sub_type": "Virtual Workshop",
        "status": "Conf",
        "all_staffings": "Facilitadora Uno, Facilitador Dos",
        "ignore_reporting": False,
    }
    values.update(overrides)
    return ProjectSnapshot(**values)  # type: ignore[arg-type]


class StandardWeekTest(unittest.TestCase):
    def test_every_weekday_maps_to_its_monday(self) -> None:
        monday = date(2026, 11, 23)
        for offset in range(7):
            day = monday + timedelta(days=offset)
            with self.subTest(day=day.isoformat()):
                self.assertEqual(reference_monday(day), monday)
                self.assertEqual(
                    standard_week(day), (date(2026, 11, 24), date(2026, 11, 30))
                )

    def test_documented_example(self) -> None:
        # Wednesday 5 → Monday 3 (example in the requirements, August 2026).
        self.assertEqual(reference_monday(date(2026, 8, 5)), date(2026, 8, 3))

    def test_month_and_year_boundaries(self) -> None:
        cases = {
            date(2026, 12, 30): (date(2026, 12, 29), date(2027, 1, 4)),
            date(2027, 3, 1): (date(2027, 3, 2), date(2027, 3, 8)),
            date(2028, 2, 28): (date(2028, 2, 29), date(2028, 3, 6)),
        }
        for day, window in cases.items():
            with self.subTest(day=day.isoformat()):
                self.assertEqual(standard_week(day), window)

    def test_selection_label_names_monday_and_window(self) -> None:
        selection = standard_week_selection(date(2026, 11, 25))
        self.assertEqual(selection.days, 7)
        self.assertEqual(
            selection.label,
            "Standard week of Monday 23 Nov 2026 (24 Nov 2026–30 Nov 2026)",
        )


class TodayInBuenosAiresTest(unittest.TestCase):
    def test_date_follows_buenos_aires_not_utc(self) -> None:
        cases = {
            datetime(2026, 11, 30, 2, 59, tzinfo=UTC): date(2026, 11, 29),
            datetime(2026, 11, 30, 3, 0, tzinfo=UTC): date(2026, 11, 30),
            datetime(2026, 11, 30, 23, 0, tzinfo=timezone(timedelta(hours=-3))): date(
                2026, 11, 30
            ),
            datetime(2026, 7, 1, 12, 0, tzinfo=UTC): date(2026, 7, 1),  # no DST
        }
        for moment, expected in cases.items():
            with self.subTest(moment=moment.isoformat()):
                self.assertEqual(today_in_buenos_aires(moment), expected)

    def test_naive_datetimes_are_rejected(self) -> None:
        with self.assertRaises(SelectionError):
            today_in_buenos_aires(datetime(2026, 11, 30, 12, 0))

    def test_default_is_now(self) -> None:
        self.assertIsInstance(today_in_buenos_aires(), date)


class PresetTest(unittest.TestCase):
    def test_single_day(self) -> None:
        selection = day_selection(date(2026, 11, 26))
        self.assertEqual(
            (selection.date_from, selection.date_to), (date(2026, 11, 26),) * 2
        )
        self.assertTrue(selection.contains(date(2026, 11, 26)))
        self.assertFalse(selection.contains(date(2026, 11, 27)))

    def test_range_is_inclusive(self) -> None:
        selection = range_selection(date(2026, 11, 26), date(2026, 11, 28))
        self.assertEqual(selection.days, 3)

    def test_reversed_range_is_rejected(self) -> None:
        with self.assertRaisesRegex(SelectionError, "is after end"):
            range_selection(date(2026, 11, 28), date(2026, 11, 26))

    def test_span_limit(self) -> None:
        start = date(2026, 1, 1)
        range_selection(start, start + timedelta(days=MAX_SPAN_DAYS - 1))
        with self.assertRaisesRegex(SelectionError, "maximum"):
            range_selection(start, start + timedelta(days=MAX_SPAN_DAYS))


class ExtendTest(unittest.TestCase):
    def setUp(self) -> None:
        self.week = standard_week_selection(date(2026, 11, 23))

    def test_add_days_at_either_end(self) -> None:
        extended = self.week.extended(start_days=1, end_days=2)
        self.assertEqual(extended.date_from, date(2026, 11, 23))
        self.assertEqual(extended.date_to, date(2026, 12, 2))
        self.assertIn("adjusted to 23 Nov 2026–2 Dec 2026", extended.label)

    def test_negative_values_shrink(self) -> None:
        shrunk = self.week.extended(start_days=-2, end_days=-4)
        self.assertEqual((shrunk.date_from, shrunk.date_to), (date(2026, 11, 26),) * 2)

    def test_shrinking_past_itself_is_rejected(self) -> None:
        with self.assertRaises(SelectionError):
            self.week.extended(end_days=-8)

    def test_no_change_returns_same_selection(self) -> None:
        self.assertIs(self.week.extended(), self.week)


class CountryCodesTest(unittest.TestCase):
    def test_codes_are_normalised(self) -> None:
        selection = day_selection(date(2026, 11, 26)).with_filters(
            country_codes=(" ar", "Mx")
        )
        self.assertEqual(selection.country_codes, ("AR", "MX"))

    def test_invalid_codes(self) -> None:
        base = day_selection(date(2026, 11, 26))
        for codes in (("AR", "ar"), ("",)):
            with self.subTest(codes=codes):
                with self.assertRaises(SelectionError):
                    base.with_filters(country_codes=codes)


class SearchFiltersTest(unittest.TestCase):
    def test_empty_filters_match_everything(self) -> None:
        self.assertTrue(SearchFilters().is_empty)
        self.assertTrue(SearchFilters().matches(project()))

    def test_contains_is_accent_and_case_insensitive(self) -> None:
        cases = {
            "project": ("liderazgo agil", True),
            "client": ("COMPANIA  sintetica", True),
            "facilitator": ("facilitador dos", True),
            "sub_type": ("workshop", True),
        }
        for name, (value, expected) in cases.items():
            with self.subTest(filter=name):
                self.assertIs(
                    SearchFilters(**{name: value}).matches(project()), expected
                )

    def test_filters_are_combined_with_and(self) -> None:
        self.assertTrue(
            SearchFilters(client="sintetica", project="sesion 2").matches(project())
        )
        self.assertFalse(
            SearchFilters(client="sintetica", project="sesion 3").matches(project())
        )

    def test_whitespace_is_collapsed_and_non_text_rejected(self) -> None:
        self.assertEqual(SearchFilters(client="  a   b ").client, "a b")
        with self.assertRaises(SelectionError):
            SearchFilters(client=3)  # type: ignore[arg-type]


class SerialisationTest(unittest.TestCase):
    def test_round_trip(self) -> None:
        selection = (
            standard_week_selection(date(2026, 11, 23))
            .extended(end_days=1)
            .with_filters(
                country_codes=("BR",), filters=SearchFilters(facilitator="uno")
            )
        )
        self.assertEqual(Selection.from_dict(selection.to_dict()), selection)

    def test_invalid_documents_fail_closed(self) -> None:
        valid = day_selection(date(2026, 11, 26)).to_dict()
        broken = [
            {k: v for k, v in valid.items() if k != "date_from"},
            {**valid, "date_to": "26/11/2026"},
            {**valid, "filters": {"unknown": "x"}},
            {**valid, "date_to": "2026-11-25"},
        ]
        for document in broken:
            with self.subTest(document=document):
                with self.assertRaises(SelectionError):
                    Selection.from_dict(document)


if __name__ == "__main__":
    unittest.main()
