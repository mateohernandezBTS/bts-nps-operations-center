"""Per-source Markdown content and grouping contracts."""

from __future__ import annotations

import unittest
from collections import Counter

from engine.stages.slack_output import SLACK_COLUMNS, generate_slack_output
from engine.stages.worklist import load_operational_config
from tests.support.stage_cases import worklist


class SlackOutputTest(unittest.TestCase):
    def test_per_source_markdown(self) -> None:
        for country in ("Argentina", "Brazil", "Mexico"):
            with self.subTest(country=country):
                rows = worklist(f"weekly_{country}_upcoming")["worklist"]
                result = generate_slack_output(
                    rows, load_operational_config(), country, "8/4/2026", "8/10/2026"
                )
                self.assertIn(
                    f"# Upcoming NPS | {country} | 8/4/2026 to 8/10/2026",
                    result["markdown"],
                )
                self.assertIn("Total de sesiones: 2", result["markdown"])
                self.assertEqual(len(result["records"]), 2)
                for row in rows:
                    self.assertIn(row["Session"], result["markdown"])
                    self.assertIn(
                        "[Home](" + row["Link for Results"] + ")", result["markdown"]
                    )
                self.assertEqual(list(result["records"][0]), SLACK_COLUMNS)

    def test_summary_grouping_and_ready_filter(self) -> None:
        rows = worklist("classification_Mexico_worklist_review")
        result = generate_slack_output(
            rows["worklist"][::-1],
            load_operational_config(),
            "Mexico",
            "8/4/2026",
            "8/10/2026",
        )
        self.assertEqual(
            result["summary_by_client"],
            dict(Counter(r["Client"] for r in rows["ready"])),
        )
        self.assertEqual(len(result["records"]), len(rows["ready"]))
        for row in rows["review"]:
            self.assertNotIn(row["Session"], result["markdown"])
        for client in result["summary_by_client"]:
            self.assertEqual(result["markdown"].count("## " + client + "\n"), 1)
