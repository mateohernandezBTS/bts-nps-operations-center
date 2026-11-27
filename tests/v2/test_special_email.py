"""V2-5 first step: the personalised e-mail for special cases (copy and paste)."""

from __future__ import annotations

import re
import unittest
from datetime import date

from nps_v2.outputs import special_email
from nps_v2.outputs.slack_page import PageContext, render_page
from tests.v2.test_slack_page import row

CONTEXT = PageContext(
    run_id="V2-TEST",
    title="Test week",
    generated_at="2026-11-26",
    review_count=0,
    week_start=date(2026, 12, 1),
)


class EmailTextTest(unittest.TestCase):
    def test_subject_uses_the_report_monday(self) -> None:
        self.assertEqual(special_email.subject(date(2026, 12, 1)), "NPS week 30/11/26")
        self.assertEqual(special_email.subject(date(2026, 11, 30)), "NPS week 30/11/26")
        self.assertEqual(special_email.subject(date(2026, 10, 29)), "NPS week 26/10/26")
        self.assertEqual(special_email.subject(None), "NPS week")

    def test_greeting_uses_the_first_name_and_is_escaped(self) -> None:
        self.assertIn("Hola Ana, ¿cómo estás?", special_email.intro("Ana Example", 1))
        self.assertIn("de tu sesión,", special_email.intro("Ana", 1))
        self.assertIn("de tus sesiones,", special_email.intro("Ana", 2))
        self.assertIn("Hola &lt;b&gt;,", special_email.intro("<b>", 1))

    def test_dates_are_day_first(self) -> None:
        rows = [row(1, Date="12/1/2026"), row(2, Date="TBD")]
        fixed = special_email.day_first(rows)
        self.assertEqual([r["Date"] for r in fixed], ["01/12/2026", "TBD"])
        self.assertEqual(rows[0]["Date"], "12/1/2026")  # the Slack rows are untouched

    def test_sessions_are_grouped_by_facilitator(self) -> None:
        rows = [row(1), row(2), row(3)]
        cases = {
            rows[0]["Project ID"]: ("Ana",),
            rows[2]["Project ID"]: ("Ana", "Bruno"),
        }
        grouped = special_email.by_facilitator(rows, cases)
        self.assertEqual(list(grouped), ["Ana", "Bruno"])
        self.assertEqual(
            [r["Session"] for r in grouped["Ana"]], ["Session 01", "Session 03"]
        )
        self.assertEqual([r["Session"] for r in grouped["Bruno"]], ["Session 03"])


class EmailCardsTest(unittest.TestCase):
    def render(
        self, rows: list[dict[str, str]], cases: dict[str, tuple[str, ...]]
    ) -> str:
        return render_page(
            rows, context=CONTEXT, country_order=["Argentina"], special_cases=cases
        )

    def test_no_section_without_special_cases(self) -> None:
        self.assertNotIn("Personalised e-mails", self.render([row(1)], {}))

    def test_one_card_per_facilitator_with_subject_and_copy(self) -> None:
        rows = [row(1), row(2)]
        page = self.render(rows, {r["Project ID"]: ("Ana Example",) for r in rows})
        self.assertIn("Personalised e-mails", page)
        self.assertEqual(page.count('<ion-card class="email"'), 1)
        self.assertIn('data-copy-subject="NPS week 30/11/26"', page)
        template = re.search(r'<template id="email-0">(.*?)</template>', page, re.S)
        assert template is not None
        body = template.group(1)
        self.assertTrue(body.startswith("<p>Hola Ana, ¿cómo estás?</p>"))
        self.assertIn("de tus sesiones", body)
        self.assertIn("<h3>Session 01</h3>", body)
        self.assertIn("<h3>Session 02</h3>", body)
        self.assertIn("<b>Date:</b> 21/11/2026", body)
        self.assertTrue(body.endswith("<p>¡Gracias!</p>"))
        self.assertNotIn("callout", body)  # notices are never copied

    def test_warns_when_surveys_are_not_created_yet(self) -> None:
        pending = row(1, **{"Link NPS Survey": "", "Link Insights Facilitators": ""})
        page = self.render([pending], {pending["Project ID"]: ("Ana",)})
        self.assertIn("Surveys not created yet:</b> Session 01", page)


if __name__ == "__main__":
    unittest.main()
