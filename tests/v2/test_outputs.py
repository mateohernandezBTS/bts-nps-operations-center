"""Run outputs: report.json, preview.md (snapshot) and the Slack table."""

from __future__ import annotations

import csv
import json
import os
import tempfile
import unittest
from pathlib import Path

from nps_v2.outputs.preview import render_preview
from nps_v2.outputs.slack import SLACK_CSV_COLUMNS
from nps_v2.outputs.writer import write_outputs
from tests.v2.synthetic import scenario

SNAPSHOT = (
    Path(__file__).resolve().parents[1] / "snapshots" / "v2" / "preview_synthetic.md"
)
UPDATE_VARIABLE = "NPS_V2_UPDATE_SNAPSHOTS"


class PreviewSnapshotTest(unittest.TestCase):
    """Set NPS_V2_UPDATE_SNAPSHOTS=1 to rewrite the snapshot after a reviewed change."""

    def test_preview_matches_snapshot(self) -> None:
        preview = render_preview(scenario().report)
        if os.environ.get(UPDATE_VARIABLE) == "1":
            SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
            SNAPSHOT.write_text(preview, encoding="utf-8", newline="\n")
        expected = SNAPSHOT.read_text(encoding="utf-8").replace("\r\n", "\n")
        self.assertEqual(preview, expected)

    def test_pipes_in_names_are_escaped_inside_tables(self) -> None:
        preview = render_preview(scenario().report)
        self.assertIn("Sessão \\| Turma 2", preview)

    def test_missing_watchlist_is_announced(self) -> None:
        report = dict(scenario().report, watchlist_configured=False)
        self.assertIn(
            "lista de casos especiales no está configurada", render_preview(report)
        )


class SlackTableTest(unittest.TestCase):
    def test_csv_contract_matches_the_desktop_output(self) -> None:
        from engine.selam_output import CSV_COLUMNS

        self.assertEqual(list(SLACK_CSV_COLUMNS), CSV_COLUMNS)

    def test_written_outputs(self) -> None:
        run = scenario()
        with tempfile.TemporaryDirectory() as directory:
            outputs = write_outputs(
                Path(directory),
                report=run.report,
                selection=run.selection,
                registry=run.registry,
                result=run.result,
                surveys=run.surveys,
            )
            report = json.loads(outputs.report.read_text(encoding="utf-8"))
            self.assertEqual(report["run_id"], "V2-SYNTHETIC")
            self.assertTrue(
                outputs.preview.read_text(encoding="utf-8").startswith("# ")
            )

            with (outputs.slack_html.parent / "selam_worklist.csv").open(
                encoding="utf-8", newline=""
            ) as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(
                [(r["Session"], r["Country"]) for r in rows],
                [
                    ("Synthetic Session 01", "Argentina"),
                    ("Sessão | Turma 2", "Brazil"),
                    ("Synthetic Session 03", "Mexico"),
                    ("Synthetic Session 07", "Argentina"),
                ],
            )
            complete = rows[0]
            self.assertTrue(complete["Link NPS Survey"].endswith("INV1"))
            self.assertTrue(complete["Link Insights Facilitators"].endswith("INV2"))
            self.assertTrue(complete["QR-Code"].startswith("https://api.qrserver.com/"))
            self.assertEqual(rows[2]["Link NPS Survey"], "")
            self.assertEqual({r["Output Status"] for r in rows}, {"READY"})

            summary = json.loads(
                (outputs.slack_html.parent / "selam_weekly_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                (summary["window_start"], summary["window_end"]),
                ("11/24/2026", "11/30/2026"),
            )
            self.assertEqual(summary["review_records"], 1)

            page = outputs.slack_html.read_text(encoding="utf-8")
            self.assertIn("Synthetic Client 01", page)
            self.assertIn("V2-SYNTHETIC", page)


if __name__ == "__main__":
    unittest.main()
