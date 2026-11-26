"""V2 Slack page: styled preview vs. Slack-safe copy payload."""

from __future__ import annotations

import re
import unittest

from engine.slack_canvas_renderer import SPECIAL_EMAIL_NAMES
from nps_v2.outputs.slack_page import PageContext, payload_cards, render_page

QR = "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=https%3A%2F%2Fx"
CONTEXT = PageContext(
    run_id="V2-TEST",
    title="Test week",
    generated_at="2026-11-26",
    review_count=2,
)


def row(number: int, **overrides: str) -> dict[str, str]:
    values = {
        "Client": "Synthetic Client",
        "Country": "Argentina",
        "Session": f"Session {number:02d}",
        "Date": f"11/{20 + number}/2026",
        "Facilitator": "Facilitator One",
        "QR-Code": "",
        "Link NPS Survey": f"https://example.invalid/nps/{number}",
        "Link Insights Facilitators": f"https://example.invalid/sp/{number}",
        "Results": "NO",
        "Link for Results": f"https://example.invalid/results/{number}",
        "Project ID": f"a0gAA{number:010d}AAA",
    }
    values.update(overrides)
    return values


class PayloadTest(unittest.TestCase):
    def test_one_card_per_session_in_desktop_order(self) -> None:
        payload = payload_cards([row(3), row(1), row(2)])
        titles = [payload.index(f"<h3>Session 0{n}</h3>") for n in (1, 2, 3)]
        self.assertEqual(titles, sorted(titles))
        self.assertNotIn("<table", payload)

    def test_card_content(self) -> None:
        payload = payload_cards([row(1, **{"QR-Code": QR})])
        self.assertEqual(
            payload,
            "<h3>Session 01</h3>"
            "<p><b>Date:</b> 11/21/2026 · <b>Facilitator:</b> Facilitator One</p>"
            '<p><b>Surveys:</b> <a href="https://example.invalid/nps/1">NPS</a> · '
            '<a href="https://example.invalid/sp/1">Facilitators</a></p>'
            '<p><img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150'
            '&amp;data=https%3A%2F%2Fx" alt="QR" data-row="0" width="150" '
            'height="150"></p>'
            '<p><b>Link for Results:</b> <a href="https://example.invalid/results/1">'
            "Home</a></p>"
            "<p><b>Results:</b> NO</p>"
            "<hr>",
        )

    def test_missing_links_and_qr(self) -> None:
        payload = payload_cards(
            [
                row(
                    1,
                    **{
                        "Link Insights Facilitators": "",
                        "Link NPS Survey": "",
                        "Facilitator": "",
                        "Link for Results": "",
                    },
                )
            ]
        )
        self.assertIn("<b>Surveys:</b> not created yet", payload)
        self.assertIn("<b>Facilitator:</b> —", payload)
        self.assertIn("<p><b>QR:</b> survey not created yet</p>", payload)
        self.assertIn("<p><b>Link for Results:</b> —</p>", payload)
        self.assertIn("<p><b>Results:</b> NO</p>", payload)

    def test_every_card_keeps_the_results_marker(self) -> None:
        payload = payload_cards([row(1), row(2), row(3, Results="")])
        self.assertEqual(payload.count("<p><b>Results:</b> NO</p>"), 3)
        self.assertEqual(payload.count("<hr>"), 3)

    def test_qr_placeholders_follow_card_order(self) -> None:
        payload = payload_cards(
            [row(2, **{"QR-Code": QR}), row(1), row(3, **{"QR-Code": QR})]
        )
        self.assertEqual(re.findall(r'data-row="(\d)"', payload), ["1", "2"])

    def test_payload_has_no_styles_classes_or_warnings(self) -> None:
        # A name the desktop renderer would flag with a warning row.
        flagged = SPECIAL_EMAIL_NAMES[0].title()
        payload = payload_cards([row(1, Facilitator=flagged)])
        for forbidden in (
            "class=",
            "style=",
            "ENVÍO",
            "Envío",
            "Send by e-mail",
            "<table",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, payload)

    def test_text_is_escaped(self) -> None:
        payload = payload_cards([row(1, Session="A <b> & C")])
        self.assertIn("<h3>A &lt;b&gt; &amp; C</h3>", payload)


class PageTest(unittest.TestCase):
    def render(
        self, rows: list[dict[str, str]], special: dict[str, tuple[str, ...]]
    ) -> str:
        return render_page(
            rows,
            context=CONTEXT,
            country_order=["Argentina", "Brazil", "Mexico"],
            special_cases=special,
        )

    def test_layers_are_separate(self) -> None:
        special_row = row(2, Facilitator="Watched Person", **{"QR-Code": QR})
        page = self.render(
            [row(1), special_row], {special_row["Project ID"]: ("Watched Person",)}
        )
        template = re.search(r"<template[^>]*>(.*?)</template>", page, re.S).group(1)  # type: ignore[union-attr]
        self.assertNotIn("Send by e-mail", template)
        self.assertNotIn("special", template)
        self.assertNotIn("ion-", template)
        preview = page.replace(template, "")
        self.assertIn(
            "Send by e-mail separately:</b> Session 02 · Watched Person", preview
        )
        self.assertIn('class="session special"', preview)
        self.assertIn('data-copy="payload-client-table-', preview)

    def test_preview_draws_qr_locally_with_fallback(self) -> None:
        page = self.render([row(1, **{"QR-Code": QR})], {})
        self.assertIn('data-text="https://example.invalid/nps/1"', page)
        self.assertIn('data-fallback="https://api.qrserver.com/', page)
        self.assertIn(
            "cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js", page
        )
        self.assertIn("embedQrImages", page)

    def test_countries_follow_registry_order_and_names_are_escaped(self) -> None:
        page = self.render(
            [
                row(1, Country="Mexico", Client="Z <Client>"),
                row(2, Country="Brazil"),
                row(3, Country="Argentina"),
            ],
            {},
        )
        positions = [
            page.index(f'country-title">{c}') for c in ("Argentina", "Brazil", "Mexico")
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Z &lt;Client&gt;", page)
        self.assertNotIn("Z <Client>", page)

    def test_copy_has_fallbacks_for_blocked_clipboards(self) -> None:
        page = self.render([row(1, **{"QR-Code": QR})], {})
        self.assertIn('<div id="manual-copy" hidden>', page)
        for function in ("writeAsync", "writeWithCopyEvent", "writeBySelection"):
            with self.subTest(function=function):
                self.assertIn(f"function {function}(", page)

    def test_each_client_can_show_how_it_looks_in_slack(self) -> None:
        page = self.render([row(1), row(2, Client="Other Client")], {})
        self.assertEqual(page.count('<ion-accordion-group class="slack-view">'), 2)
        self.assertIn("function payloadFor(", page)

    def test_sessions_follow_payload_order(self) -> None:
        # The copy script maps each payload QR (data-row) to the n-th session item.
        page = self.render([row(3), row(1), row(2)], {})
        items = re.findall(r'data-index="(\d)" data-search="[^"]*session (0\d)', page)
        self.assertEqual(items, [("0", "01"), ("1", "02"), ("2", "03")])

    def test_search_and_country_tabs(self) -> None:
        page = self.render([row(1, Country="Brazil"), row(2, Country="Argentina")], {})
        self.assertIn("<ion-searchbar", page)
        tabs = re.findall(r'<ion-segment-button value="([^"]+)"', page)
        self.assertEqual(tabs, ["all", "Argentina", "Brazil"])
        self.assertIn('data-search="synthetic client session 01 facilitator one', page)

    def test_only_http_links_are_rendered(self) -> None:
        unsafe = row(
            1,
            **{
                "Link NPS Survey": "javascript:alert(1)",
                "Link Insights Facilitators": "data:text/html,x",
                "Link for Results": "javascript:alert(2)",
            },
        )
        preview = self.render([unsafe], {}).split("<template")[0]
        self.assertNotIn("javascript:", preview)
        self.assertNotIn("data:text/html", preview)
        self.assertIn("Surveys not created yet", preview)

    def test_kpis_and_empty_state(self) -> None:
        page = self.render([], {})
        self.assertIn("No sessions are ready", page)
        self.assertIn(
            '<span class="tile-n">2</span><span class="tile-l">Manual review', page
        )


if __name__ == "__main__":
    unittest.main()
