"""English wording of engine decisions; guard that user-facing outputs are English."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from engine.paths import config_path
from engine.stages.business_rules import classify_record, load_business_rules_config
from engine.stages.normalize import normalize_record
from engine.stages.worklist import create_worklist_record, load_operational_config
from nps_v2.compare import compare, render_comparison
from nps_v2.outputs.preview import render_preview
from nps_v2.outputs.slack_page import PageContext, render_page
from nps_v2.reasons import ReasonTexts, ReasonTextsError, load_reason_texts
from tests.v2.synthetic import scenario

VALID = {
    "start_date": "11/24/2026",
    "end_date": "",
    "client_name": "Synthetic Client",
    "project_name": "Synthetic Session",
    "project_sub_type": "Workshop",
    "status": "Conf",
    "ignore_reporting": "false",
}

# Words that only appear in Spanish UI text (data such as "Sessão" is not checked).
SPANISH_MARKERS = re.compile(
    r"\b(Fecha|Facilitador|Encuestas?|Sesión|Cliente|Corrida|corrida|pendientes?|"
    r"Revisión|Copiar|Copiá|Resultados|Motivo|Ninguno|Ninguna|Coinciden|vacío|"
    r"incluido|elegibles|Excluir|Tiene|además|presioná|Cerrar)\b"
)


def engine_messages() -> list[str]:
    """Every fixed message the certified engine can write, produced by the engine."""
    rules = load_business_rules_config()
    messages: list[str] = []
    broken_inputs = [
        {"start_date": "31/31/2026"},
        {"ignore_reporting": "maybe"},
        {"status": ""},
        {"status": "Unknown"},
        {"client_name": ""},
    ]
    for change in broken_inputs:
        _, issues = normalize_record({**VALID, **change}, row_number=1)
        messages += issues
    for change in ({"status": "Prelim"}, {"ignore_reporting": "true"}):
        record, _ = normalize_record({**VALID, **change}, row_number=1)
        messages += classify_record(record, rules)["decision_reasons"].split(" | ")
    worklist = create_worklist_record(
        {"project_url": "", "project_name": "", "start_date": ""},
        load_operational_config(),
    )
    messages += worklist["Output Issues"].split(" | ")
    return messages


class ReasonTextsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.texts = load_reason_texts()

    def test_every_enabled_rule_has_an_english_label(self) -> None:
        rules = load_business_rules_config()["exclusion_rules"]
        enabled = {rule["id"] for rule in rules if rule.get("enabled")}
        self.assertTrue(enabled)
        self.assertEqual(enabled - set(self.texts.rule_labels), set())

    def test_every_fixed_engine_message_is_worded_in_english(self) -> None:
        messages = engine_messages()
        self.assertGreaterEqual(len(messages), 10)
        for message in messages:
            with self.subTest(message=message):
                english = self.texts.message(message)
                self.assertNotEqual(english, " ".join(message.split()))
                self.assertIsNone(SPANISH_MARKERS.search(english), english)

    def test_values_are_kept(self) -> None:
        self.assertEqual(
            self.texts.message("Status Prelim no incluido en los estados elegibles."),
            "Status Prelim is not an eligible status",
        )
        self.assertEqual(
            self.texts.message("Campo obligatorio vacío: client_name"),
            "Required field is empty: client_name",
        )

    def test_rule_decisions_use_labels_and_others_use_the_wording(self) -> None:
        reasons = self.texts.decision(
            ("STATUS_NOT_ELIGIBLE", "POD"),
            ("Status Tent no incluido en los estados elegibles.", "Excluir PODs"),
        )
        self.assertEqual(
            reasons, ["Status Tent is not an eligible status", "POD session"]
        )

    def test_validation_issue_with_several_messages(self) -> None:
        reasons = self.texts.decision(
            ("VALIDATION_ISSUE",), ("Status vacío", "Campo obligatorio vacío: status")
        )
        self.assertEqual(
            reasons, ["Status is empty", "Required field is empty: status"]
        )

    def test_unknown_text_is_shown_as_written(self) -> None:
        self.assertEqual(self.texts.message("  Mensaje   nuevo "), "Mensaje nuevo")
        self.assertEqual(
            self.texts.decision(("NEW_RULE",), ("Regla nueva",)), ["Regla nueva"]
        )

    def test_issue_lists(self) -> None:
        self.assertEqual(
            self.texts.issues("Session vacío | Date vacío"),
            "Session is empty; Date is empty",
        )
        self.assertEqual(self.texts.issues(""), "")


class LoadReasonTextsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)

    def test_default_file_is_the_v2_config(self) -> None:
        raw = json.loads(
            config_path("v2", "rule_labels.json").read_text(encoding="utf-8")
        )
        self.assertEqual(load_reason_texts().rule_labels, raw["rule_labels"])

    def test_invalid_files(self) -> None:
        cases = {
            "missing.json": None,
            "not_json.json": "{",
            "no_key.json": "{}",
            "empty_label.json": '{"rule_labels": {"POD": " "}}',
            "not_text.json": '{"rule_labels": {"POD": 1}}',
        }
        for name, content in cases.items():
            path = self.directory / name
            if content is not None:
                path.write_text(content, encoding="utf-8")
            with self.subTest(file=name):
                with self.assertRaises(ReasonTextsError):
                    load_reason_texts(path)

    def test_custom_labels(self) -> None:
        texts = ReasonTexts(rule_labels={"POD": "Custom"})
        self.assertEqual(texts.decision(("POD",), ("Excluir PODs",)), ["Custom"])


class EnglishOutputsTest(unittest.TestCase):
    """What users see or operate must not contain Spanish UI text."""

    def setUp(self) -> None:
        self.report = scenario().report

    def assert_english(self, text: str) -> None:
        found = sorted(set(SPANISH_MARKERS.findall(text)))
        self.assertEqual(found, [], f"Spanish UI text found: {found}")

    def test_preview(self) -> None:
        self.assert_english(render_preview(self.report))
        self.assert_english(
            render_preview({**self.report, "watchlist_configured": False})
        )

    def test_slack_page(self) -> None:
        row = {
            "Country": "Argentina",
            "Client": "Synthetic Client",
            "Session": "Synthetic Session",
            "Date": "11/24/2026",
            "Facilitator": "",
            "Project ID": "a0gAA0000000001",
            "Results": "NO",
        }
        context = PageContext("V2-X", "Test week", "2026-11-26", 1)
        for rows, special in (([row], {"a0gAA0000000001": ("Someone",)}), ([], {})):
            with self.subTest(rows=len(rows)):
                page = render_page(
                    rows,
                    context=context,
                    country_order=["Argentina"],
                    special_cases=special,
                )
                self.assert_english(page)
                self.assertIn('<html lang="en">', page)

    def test_review_pages(self) -> None:
        from tests.v2.test_ui_kit import review_pages

        for name, page in review_pages().items():
            with self.subTest(page=name):
                self.assert_english(page)
                self.assertIn('<html lang="en">', page)

    def test_comparison(self) -> None:
        ready = [*self.report["pending"], *self.report["complete"]]
        desktop = {
            "a0gAA0000000999": {"Session": "Deleted later", "Client": "X"},
            self.report["excluded"][0]["project_id"][:15]: {"Session": "E"},
        }
        result = compare(self.report, desktop)
        self.assertEqual(result.only_v2.__len__(), len(ready))
        self.assert_english(
            render_comparison(result, run_id="V2-X", desktop_name="worklist.csv")
        )


if __name__ == "__main__":
    unittest.main()
