"""Shared UI kit (D-V2-11): Ionic + BTS theme, pinned version, mandatory fallback."""

from __future__ import annotations

import re
import unittest

from nps_v2.outputs import ui_kit
from nps_v2.outputs.slack_page import PageContext, render_page
from nps_v2.outputs.ui_kit import (
    IONIC_MODE,
    IONIC_SCRIPT,
    IONIC_VERSION,
    Tile,
    kpi_tiles,
    render_document,
    safe_url,
)

ION_TAG = re.compile(r"<(ion-[a-z-]+)")
FALLBACK_RULE = re.compile(r"(ion-[a-z-]+)(?:\[[^\]]*\]|\.[\w-]+)*:not\(:defined\)")


def slack_page() -> str:
    row = {
        "Country": "Argentina",
        "Client": "Synthetic Client",
        "Session": "Synthetic Session",
        "Date": "11/24/2026",
        "Facilitator": "Facilitator One",
        "Link NPS Survey": "https://example.invalid/nps",
        "Link Insights Facilitators": "https://example.invalid/sp",
        "QR-Code": "https://api.qrserver.com/v1/create-qr-code/?data=x",
        "Results": "NO",
        "Link for Results": "https://example.invalid/results",
        "Project ID": "a0gAA0000000001",
    }
    return render_page(
        [row],
        context=PageContext("V2-X", "Test week", "2026-11-26", 1),
        country_order=["Argentina"],
        special_cases={"a0gAA0000000001": ("Someone",)},
    )


def creation_pages() -> dict[str, str]:
    from nps_v2.creation.execution import ExecutionState
    from nps_v2.creation.plan import build_plan
    from nps_v2.creation.reconcile import reconcile
    from nps_v2.outputs.creation_pages import render_plan_page, render_result_page
    from tests.v2.synthetic import scenario

    plan = build_plan(scenario().report)
    names = {"AR": "Argentina", "BR": "Brazil", "MX": "Mexico"}
    state = ExecutionState(plan_hash=plan.hash, steps=[], commands={})
    outcomes = reconcile(plan, state, [], {})
    return {
        "plan page": render_plan_page(plan, country_names=names, generated_at="t"),
        "result page": render_result_page(
            outcomes,
            plan=plan,
            operator="Synthetic User",
            run_error="",
            country_names=names,
            generated_at="t",
        ),
    }


class UiKitTest(unittest.TestCase):
    def test_ionic_version_is_exact_and_mode_is_ios(self) -> None:
        self.assertRegex(IONIC_VERSION, r"^\d+\.\d+\.\d+$")
        self.assertIn(f"@ionic/core@{IONIC_VERSION}/", IONIC_SCRIPT)
        self.assertEqual(IONIC_MODE, "ios")

    def test_document_loads_ionic_with_the_bts_theme(self) -> None:
        page = render_document(title="T <x>", header="<div>h</div>", body="<p>b</p>")
        self.assertTrue(page.startswith('<!DOCTYPE html>\n<html lang="en">'))
        self.assertIn(f'<script type="module" src="{IONIC_SCRIPT}"></script>', page)
        self.assertIn("window.Ionic={config:{mode:'ios'}}", page)
        self.assertIn("--ion-color-primary:#CA1C68", page)
        self.assertIn("<title>T &lt;x&gt;</title>", page)
        self.assertIn("window.BTSUI=ui", page)
        self.assertNotIn("Ionic loaded", page)  # no proof banner in the product

    def test_every_ionic_tag_of_every_view_has_a_fallback(self) -> None:
        covered = set(FALLBACK_RULE.findall(ui_kit.KIT_CSS))
        views = {"slack page": slack_page(), **creation_pages()}
        for name, page in views.items():
            used = set(ION_TAG.findall(page))
            self.assertTrue(used, name)
            with self.subTest(view=name):
                self.assertEqual(used - covered, set())

    def test_safe_url(self) -> None:
        self.assertEqual(safe_url(" https://a.b/c "), "https://a.b/c")
        self.assertEqual(safe_url("HTTP://a.b"), "HTTP://a.b")
        for bad in ("javascript:alert(1)", "data:text/html,x", "/relative", ""):
            with self.subTest(url=bad):
                self.assertEqual(safe_url(bad), "")

    def test_kpi_tiles_warn_only_when_non_zero(self) -> None:
        tiles = kpi_tiles((Tile("A", 0, warn=True), Tile("B", 2, warn=True)))
        self.assertIn('<div class="tile"><span class="tile-n">0</span>', tiles)
        self.assertIn('<div class="tile warn"><span class="tile-n">2</span>', tiles)


if __name__ == "__main__":
    unittest.main()
