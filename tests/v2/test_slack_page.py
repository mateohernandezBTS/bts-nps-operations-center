"""V2 Slack page: styled preview vs. Slack-safe copy payload."""

from __future__ import annotations

import re
import unittest

from engine.slack_canvas_renderer import SPECIAL_EMAIL_NAMES, render_client_table
from nps_v2.outputs.slack_page import (
    PageContext,
    payload_table,
    qr_payload_cell,
    render_page,
)

QR = "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=https%3A%2F%2Fx"
CONTEXT = PageContext(
    run_id="V2-TEST",
    title="Semana de prueba",
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


def compact(markup: str) -> str:
    return re.sub(r">\s+<", "><", " ".join(markup.split()))


def legacy_table(markup: str) -> str:
    return compact(re.search(r"<table.*</table>", markup, re.S).group(0))  # type: ignore[union-attr]


class PayloadTest(unittest.TestCase):
    def test_payload_is_the_desktop_table_when_there_is_no_qr(self) -> None:
        records = [row(3), row(1), row(2, Facilitator="Facilitator Two")]
        expected = legacy_table(render_client_table("Synthetic Client", records))
        self.assertEqual(payload_table("Synthetic Client", records), expected)

    def test_qr_cell_carries_the_image(self) -> None:
        payload = payload_table("Synthetic Client", [row(1, **{"QR-Code": QR})])
        self.assertIn(
            '<td><img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150'
            '&amp;data=https%3A%2F%2Fx" alt="QR" width="150" height="150"></td>',
            payload,
        )
        self.assertEqual(qr_payload_cell("  "), "")

    def test_payload_has_no_styles_classes_or_warnings(self) -> None:
        # A name the desktop renderer would flag with a warning row.
        flagged = SPECIAL_EMAIL_NAMES[0].title()
        payload = payload_table("Synthetic Client", [row(1, Facilitator=flagged)])
        for forbidden in ("class=", "style=", "ENVÍO", "colspan"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, payload)


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
        self.assertNotIn("Envío por mail", template)
        self.assertNotIn("row-special", template)
        preview = page.replace(template, "")
        self.assertIn(
            "Envío por mail por separado:</b> Session 02 · Watched Person", preview
        )
        self.assertIn('<tr class="row-special">', preview)
        self.assertIn('data-copy="payload-client-table-', preview)

    def test_preview_draws_qr_locally_with_fallback(self) -> None:
        page = self.render([row(1, **{"QR-Code": QR})], {})
        self.assertIn('class="qr" data-text="https://example.invalid/nps/1"', page)
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

    def test_kpis_and_empty_state(self) -> None:
        page = self.render([], {})
        self.assertIn("No hay sesiones listas", page)
        self.assertIn(
            '<span class="tile-n">2</span><span class="tile-l">Revisión manual', page
        )


if __name__ == "__main__":
    unittest.main()
