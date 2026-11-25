"""Country registry loading and fail-closed validation."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from nps_v2.domain import SalesforceId
from nps_v2.registry import RegistryError, load_registry, parse_registry

NPS_A = "0KdAA0000000001AAA"
NPS_B = "0KdAA0000000002AAA"
SP = "0KdAA0000000003AAA"
SP_VARIANT = "0KdAA0000000004AAA"


def synthetic_registry() -> dict[str, Any]:
    return {
        "version": "test",
        "supported_languages": ["es", "pt-BR"],
        "surveys": {
            "nps_a": {"id": NPS_A, "name": "NPS A"},
            "nps_b": {"id": NPS_B, "name": "NPS B"},
            "sp": {"id": SP, "name": "Facilitators"},
        },
        "facilitator_survey_family": [
            {"id": SP, "name": "Facilitators"},
            {"id": SP_VARIANT, "name": "Facilitators variant"},
        ],
        "countries": [
            {
                "code": "aa",
                "name": "Country A",
                "billing_country_values": ["Alpha"],
                "language": "es",
                "nps_survey": "nps_a",
                "facilitators_survey": "sp",
                "slack_section": "Alpha",
            },
            {
                "code": "BB",
                "name": "Country B",
                "billing_country_values": ["Beta", "Beta Partner"],
                "language": "pt-BR",
                "nps_survey": "nps_b",
                "facilitators_survey": "sp",
                "slack_section": "Beta / Partner",
            },
        ],
    }


class RegistryParsingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = parse_registry(synthetic_registry())

    def test_codes_are_normalised_and_order_is_kept(self) -> None:
        self.assertEqual([c.code for c in self.registry.countries], ["AA", "BB"])
        self.assertEqual(self.registry.by_code(" bb ").name, "Country B")

    def test_unknown_code_fails(self) -> None:
        with self.assertRaisesRegex(RegistryError, "Unknown country code"):
            self.registry.by_code("ZZ")

    def test_billing_lookup_is_case_insensitive_and_maps_partners(self) -> None:
        country = self.registry.country_for_billing(" beta partner ")
        assert country is not None
        self.assertEqual(country.code, "BB")
        self.assertIsNone(self.registry.country_for_billing("Gamma"))

    def test_billing_values_for_all_or_selected_countries(self) -> None:
        self.assertEqual(
            self.registry.billing_values(), ("Alpha", "Beta", "Beta Partner")
        )
        self.assertEqual(self.registry.billing_values(["BB"]), ("Beta", "Beta Partner"))

    def test_surveys_and_language_per_country(self) -> None:
        country = self.registry.by_code("BB")
        self.assertEqual(country.language, "pt-BR")
        self.assertEqual(country.nps_survey.survey_id, SalesforceId(NPS_B))
        self.assertEqual(country.facilitators_survey.survey_id, SalesforceId(SP))

    def test_facilitator_family_membership_uses_15_char_key(self) -> None:
        self.assertTrue(
            self.registry.is_facilitator_survey(SalesforceId(SP_VARIANT[:15]))
        )
        self.assertFalse(self.registry.is_facilitator_survey(SalesforceId(NPS_A)))
        self.assertFalse(self.registry.is_facilitator_survey(None))


class RegistryValidationTest(unittest.TestCase):
    def assert_invalid(self, mutate: Any, message: str) -> None:
        raw = copy.deepcopy(synthetic_registry())
        mutate(raw)
        with self.assertRaisesRegex(RegistryError, message):
            parse_registry(raw)

    def test_fail_closed_cases(self) -> None:
        a = 0  # index of the first country
        cases = {
            "missing countries": (lambda r: r.pop("countries"), "countries"),
            "empty countries": (lambda r: r.update(countries=[]), "at least one"),
            "unsupported language": (
                lambda r: r["countries"][a].update(language="xx"),
                "unsupported language",
            ),
            "unknown survey key": (
                lambda r: r["countries"][a].update(nps_survey="nope"),
                "unknown survey key",
            ),
            "invalid survey id": (
                lambda r: r["surveys"]["nps_a"].update(id="bad"),
                "Invalid Salesforce Id",
            ),
            "facilitators outside family": (
                lambda r: r["countries"][a].update(facilitators_survey="nps_a"),
                "not in facilitator_survey_family",
            ),
            "nps survey inside family": (
                lambda r: r["surveys"]["nps_a"].update(id=SP_VARIANT),
                "is a facilitator survey",
            ),
            "empty family": (
                lambda r: r.update(facilitator_survey_family=[]),
                "must not be empty",
            ),
            "duplicate code": (
                lambda r: r["countries"][1].update(code="AA"),
                "Duplicate country code",
            ),
            "billing value in two countries": (
                lambda r: r["countries"][1]["billing_country_values"].append("ALPHA"),
                "belongs to both",
            ),
            "blank billing value": (
                lambda r: r["countries"][a].update(billing_country_values=[" "]),
                "non-empty",
            ),
            "country not an object": (
                lambda r: r["countries"].append("AR"),
                "must be an object",
            ),
            "blank slack section": (
                lambda r: r["countries"][a].update(slack_section=""),
                "slack_section",
            ),
        }
        for name, (mutate, message) in cases.items():
            with self.subTest(case=name):
                self.assert_invalid(mutate, message)


class RegistryFileTest(unittest.TestCase):
    def test_unreadable_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "countries.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaisesRegex(RegistryError, "Cannot read registry"):
                load_registry(path)
            with self.assertRaisesRegex(RegistryError, "Cannot read registry"):
                load_registry(Path(directory) / "missing.json")

    def test_loads_a_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "countries.json"
            path.write_text(json.dumps(synthetic_registry()), encoding="utf-8")
            self.assertEqual(len(load_registry(path).countries), 2)


class ShippedRegistryTest(unittest.TestCase):
    """The versioned configuration encodes the decisions of 2026-11-25."""

    def setUp(self) -> None:
        self.registry = load_registry()

    def test_latam_scope_is_ar_br_mx(self) -> None:
        self.assertEqual([c.code for c in self.registry.countries], ["AR", "BR", "MX"])

    def test_nexo_belongs_to_brazil(self) -> None:
        country = self.registry.country_for_billing("Nexo")
        assert country is not None
        self.assertEqual(country.code, "BR")

    def test_language_and_nps_survey_per_country(self) -> None:
        expected = {
            "AR": ("es", "0Kd7V000000KymySAC"),
            "BR": ("pt-BR", "0KdPP0000000PT30AM"),
            "MX": ("es", "0Kd7V000000KymySAC"),
        }
        for code, (language, nps_id) in expected.items():
            with self.subTest(country=code):
                country = self.registry.by_code(code)
                self.assertEqual(country.language, language)
                self.assertEqual(country.nps_survey.survey_id, SalesforceId(nps_id))
                self.assertEqual(
                    country.facilitators_survey.survey_id,
                    SalesforceId("0KdPP0000000H450AE"),
                )


if __name__ == "__main__":
    unittest.main()
