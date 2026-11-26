"""Run report sections, special cases and data-quality notes."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nps_v2.watchlist import Watchlist, WatchlistError, load_watchlist
from tests.v2.synthetic import WATCHED, project, scenario


def ids(rows: list[dict[str, object]]) -> list[str]:
    return [str(row["project"]) for row in rows]


class ReportSectionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.report = scenario().report

    def test_each_project_is_in_one_section(self) -> None:
        self.assertEqual(ids(self.report["complete"]), ["Synthetic Session 01"])
        self.assertEqual(
            ids(self.report["pending"]),
            ["Synthetic Session 07", "Sessão | Turma 2", "Synthetic Session 03"],
        )
        self.assertEqual(ids(self.report["excluded"]), ["Synthetic Session 04"])
        self.assertEqual(ids(self.report["review"]), ["Synthetic Session 05 REVENUE"])
        self.assertEqual(ids(self.report["out_of_scope"]), ["Synthetic Session 06"])

    def test_surveys_to_create_use_country_survey_and_language(self) -> None:
        _, brazil, mexico = self.report["pending"]
        self.assertEqual(
            brazil["surveys_to_create"],
            [
                {
                    "kind": "FACILITATORS",
                    "label": "Facilitators",
                    "survey_name": "Facilitators SP",
                    "survey_id": "0KdPP0000000H450AE",
                    "language": "pt-BR",
                }
            ],
        )
        self.assertEqual(
            [(s["survey_name"], s["language"]) for s in mexico["surveys_to_create"]],
            [("Survey NPS", "es"), ("Facilitators SP", "es")],
        )
        self.assertEqual(self.report["summary"]["surveys_to_create"], 5)

    def test_complete_rows_carry_links_and_qr(self) -> None:
        (complete,) = self.report["complete"]
        self.assertTrue(complete["nps_link"].endswith("INV1"))
        self.assertTrue(complete["facilitators_link"].endswith("INV2"))
        self.assertTrue(complete["qr_code"].startswith("https://api.qrserver.com/"))

    def test_special_cases_package(self) -> None:
        (case,) = self.report["special_cases"]
        self.assertEqual(case["matched_facilitators"], [WATCHED])
        self.assertEqual(case["project"], "Synthetic Session 01")
        self.assertTrue(self.report["complete"][0]["special_case"])

    def test_quality_notes(self) -> None:
        notes = {(n["project"], n["note"]) for n in self.report["quality"]}
        self.assertEqual(
            notes,
            {
                (
                    "Sessão | Turma 2",
                    "Survey NPS BR: language es, the country uses pt-BR",
                ),
                ("Synthetic Session 03", "No facilitator assigned yet (PRELIM)"),
                (
                    "Synthetic Session 07",
                    "Also has the survey Synthetic Pilot Survey",
                ),
                (
                    "Synthetic Session 04",
                    "Has surveys but is not eligible "
                    "(Status Prelim is not an eligible status)",
                ),
            },
        )

    def test_summary_counts(self) -> None:
        self.assertEqual(
            self.report["summary"],
            {
                "pending": 3,
                "complete": 1,
                "worklist_review": 0,
                "review": 1,
                "excluded": 1,
                "out_of_scope": 1,
                "filtered_out": 0,
                "special_cases": 1,
                "quality_notes": 4,
                "surveys_to_create": 5,
            },
        )

    def test_report_is_json_serialisable(self) -> None:
        json.dumps(self.report)

    def test_without_watchlist_no_special_cases_are_claimed(self) -> None:
        report = scenario(watchlist=Watchlist(())).report
        self.assertEqual(report["special_cases"], [])


class WatchlistTest(unittest.TestCase):
    def test_matching_ignores_accents_and_case(self) -> None:
        watchlist = Watchlist(("José  Example",))
        self.assertEqual(
            watchlist.matches(project(1, all_staffings="Other,JOSE EXAMPLE")),
            ("José  Example",),
        )
        self.assertEqual(watchlist.matches(project(1)), ())

    def test_missing_file_means_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(load_watchlist(Path(directory) / "watchlist.json"))

    def test_file_is_loaded_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "watchlist.json"
            path.write_text('{"facilitators": ["A  B", "C"]}', encoding="utf-8")
            loaded = load_watchlist(path)
            assert loaded is not None
            self.assertEqual(loaded.names, ("A B", "C"))

    def test_invalid_files_fail_closed(self) -> None:
        for text in ('{"facilitators": [""]}', '{"facilitators": "A"}', "{", "{}"):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "watchlist.json"
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(WatchlistError):
                    load_watchlist(path)

    def test_repository_ships_only_the_synthetic_template(self) -> None:
        root = Path(__file__).resolve().parents[2]
        template = load_watchlist(root / "config" / "v2" / "watchlist.example.json")
        assert template is not None
        self.assertTrue(all(name.startswith("Example ") for name in template.names))
        gitignore = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("config/v2/watchlist.json", gitignore.splitlines())


if __name__ == "__main__":
    unittest.main()
