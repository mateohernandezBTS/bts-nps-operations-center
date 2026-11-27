"""End-to-end CLI flow on a synthetic run folder (select → surveys → upcoming)."""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any
from unittest import mock

from nps_v2.cli import EXIT_ERROR, main

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_cli(*argv: str) -> tuple[int, dict[str, Any]]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(list(argv))
    return code, json.loads(buffer.getvalue())


def aggregate(
    counts: Counter[tuple[Any, ...]], fields: tuple[str, ...]
) -> dict[str, Any]:
    records = [
        {
            "attributes": {"type": "AggregateResult"},
            **dict(zip(fields, key, strict=True)),
            "n": n,
        }
        for key, n in counts.items()
    ]
    return {"totalSize": len(records), "done": True, "records": records}


class CliRunMixin(unittest.TestCase):
    """Run-folder helpers shared by CLI tests (no tests of its own)."""

    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        self.run_dir = self.directory / "run"
        self.projects = json.loads(
            (FIXTURES / "connector_projects.json").read_text(encoding="utf-8")
        )
        self.sets = json.loads(
            (FIXTURES / "connector_survey_sets.json").read_text(encoding="utf-8")
        )

    def save(self, relative: str, value: Any) -> None:
        path = self.run_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def project_control(self, raw: dict[str, Any]) -> dict[str, Any]:
        fields = (
            "rosscrooke__Start_Date__c",
            "rosscrooke__Status__c",
            "rosscrooke__Ignore_Reporting__c",
            "Project_Sub_Type__c",
        )
        return aggregate(
            Counter(tuple(r[f] for f in fields) for r in raw["records"]), fields
        )

    def set_control(self, raw: dict[str, Any]) -> dict[str, Any]:
        fields = ("Survey__c", "SurveyNPS__c")
        return aggregate(
            Counter(tuple(r[f] for f in fields) for r in raw["records"]), fields
        )

    def select(self) -> dict[str, Any]:
        code, out = run_cli(
            "select",
            "--run",
            str(self.run_dir),
            "--from",
            "2026-11-24",
            "--to",
            "2026-11-30",
        )
        self.assertEqual(code, 0, out)
        return out


class CliFlowTest(CliRunMixin):
    def test_full_flow(self) -> None:
        out = self.select()
        self.assertEqual(
            [q["save_as"] for q in out["queries"]],
            ["responses/projects.json", "responses/projects_control.json"],
        )
        self.save("responses/projects.json", self.projects)
        self.save(
            "responses/projects_control.json", self.project_control(self.projects)
        )

        code, out = run_cli("surveys", "--run", str(self.run_dir))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["projects"], 3)
        self.assertEqual(
            [q["name"] for q in out["queries"]],
            ["survey_sets_01", "survey_sets_01_control"],
        )
        self.save("responses/survey_sets_01.json", self.sets)
        self.save("responses/survey_sets_01_control.json", self.set_control(self.sets))

        code, out = run_cli(
            "upcoming",
            "--run",
            str(self.run_dir),
            "--run-id",
            "V2-CLI-TEST",
            "--generated-at",
            "2026-11-26T10:00:00-03:00",
            "--watchlist",
            str(self.directory / "absent.json"),
        )
        self.assertEqual(code, 0, out)
        self.assertEqual(out["summary"]["pending"], 2)
        self.assertEqual(out["summary"]["out_of_scope"], 1)
        self.assertFalse(out["watchlist_configured"])
        self.assertEqual(
            set(out["outputs"]), {"report", "preview", "preview_html", "slack_html"}
        )
        for path in out["outputs"].values():
            self.assertTrue(Path(path).exists(), path)

    def test_e_mail_language_from_the_facilitator_office(self) -> None:
        watchlist = self.directory / "watchlist.json"
        watchlist.write_text(
            json.dumps({"facilitators": ["Facilitator One", "Facilitator Three"]}),
            encoding="utf-8",
        )
        self.select()
        self.save("responses/projects.json", self.projects)
        self.save(
            "responses/projects_control.json", self.project_control(self.projects)
        )
        code, out = run_cli(
            "surveys", "--run", str(self.run_dir), "--watchlist", str(watchlist)
        )
        self.assertEqual(code, 0, out)
        lookup = out["queries"][-1]
        self.assertEqual(lookup["name"], "facilitator_offices")
        self.assertEqual(
            lookup["soql"],
            "SELECT Name, Department FROM User WHERE Name IN ('Facilitator One', "
            "'Facilitator Three') ORDER BY Name ASC LIMIT 200",
        )
        self.save("responses/survey_sets_01.json", self.sets)
        self.save("responses/survey_sets_01_control.json", self.set_control(self.sets))
        # Facilitator One works in a Brazilian office; Facilitator Three is not a user.
        self.save(
            lookup["save_as"],
            {
                "totalSize": 1,
                "done": True,
                "records": [{"Name": "Facilitator One", "Department": "BR-Nexo"}],
            },
        )
        code, out = run_cli(
            "upcoming", "--run", str(self.run_dir), "--watchlist", str(watchlist)
        )
        self.assertEqual(code, 0, out)
        page = Path(out["outputs"]["slack_html"]).read_text(encoding="utf-8")
        self.assertIn("Portuguese (office BR-Nexo)", page)
        self.assertIn("Olá Facilitator, tudo bem?", page)
        self.assertIn("Spanish (session country Mexico)", page)
        self.assertIn("Hola Facilitator, ¿cómo estás?", page)

    def test_capture_saves_responses_from_the_transcript(self) -> None:
        out = self.select()
        responses = {
            "projects": self.projects,
            "projects_control": self.project_control(self.projects),
        }
        lines = []
        for number, query in enumerate(out["queries"]):
            use: dict[str, Any] = {
                "type": "tool_use",
                "id": f"u{number}",
                "name": "x_salesforce_query",
            }
            use["input"] = {"query": query["soql"]}
            result = {"type": "tool_result", "tool_use_id": f"u{number}"}
            result["content"] = json.dumps(responses[query["name"]])
            lines += [
                {"message": {"content": [use]}},
                {"message": {"content": [result]}},
            ]
        transcript = self.directory / "session.jsonl"
        transcript.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")

        code, captured = run_cli(
            "capture",
            "--run",
            str(self.run_dir),
            "--group",
            "projects",
            "--transcript",
            str(transcript),
        )
        self.assertEqual(code, 0, captured)
        self.assertEqual(captured["captured"], ["projects", "projects_control"])
        self.assertEqual(captured["missing"], [])
        code, out = run_cli("surveys", "--run", str(self.run_dir))
        self.assertEqual(code, 0, out)

    def test_selection_presets_and_filters(self) -> None:
        code, out = run_cli(
            "select",
            "--run",
            str(self.run_dir),
            "--week-of",
            "2026-11-26",
            "--extend-end",
            "1",
            "--country",
            "br",
            "--client",
            "beta",
        )
        self.assertEqual(code, 0, out)
        self.assertEqual(out["selection"]["date_from"], "2026-11-24")
        self.assertEqual(out["selection"]["date_to"], "2026-12-01")
        self.assertEqual(out["selection"]["country_codes"], ["BR"])
        self.assertIn("IN ('Brazil', 'Nexo')", out["queries"][0]["soql"])

    def test_this_week_uses_today_in_buenos_aires(self) -> None:
        with mock.patch(
            "nps_v2.cli.today_in_buenos_aires", return_value=date(2026, 11, 30)
        ):
            code, out = run_cli("select", "--run", str(self.run_dir), "--this-week")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["selection"]["date_from"], "2026-12-01")
        self.assertEqual(out["selection"]["date_to"], "2026-12-07")

    def test_this_week_excludes_other_dates(self) -> None:
        argv = [
            "select",
            "--run",
            str(self.run_dir),
            "--this-week",
            "--day",
            "2026-11-26",
        ]
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stop:
                main(argv)
        self.assertEqual(stop.exception.code, 2)  # argparse usage error

    def test_errors_are_reported_not_raised(self) -> None:
        cases = {
            "no date": ("select", "--run", str(self.run_dir)),
            "unknown country": (
                "select",
                "--run",
                str(self.run_dir),
                "--day",
                "2026-11-26",
                "--country",
                "CL",
            ),
            "to without from": (
                "select",
                "--run",
                str(self.run_dir),
                "--to",
                "2026-11-26",
            ),
            "surveys before responses": ("surveys", "--run", str(self.run_dir)),
        }
        for name, argv in cases.items():
            with self.subTest(case=name):
                code, out = run_cli(*argv)
                self.assertEqual(code, EXIT_ERROR)
                self.assertEqual(out["status"], "error")

    def test_tampered_transcription_stops_the_run(self) -> None:
        self.select()
        tampered = json.loads(json.dumps(self.projects))
        tampered["records"][0]["rosscrooke__Status__c"] = "Prelim"
        self.save("responses/projects.json", tampered)
        self.save(
            "responses/projects_control.json", self.project_control(self.projects)
        )
        code, out = run_cli("surveys", "--run", str(self.run_dir))
        self.assertEqual(code, EXIT_ERROR)
        self.assertEqual(out["error"], "ControlMismatchError")

    def test_stale_survey_queries_are_rejected(self) -> None:
        self.select()
        self.save("responses/projects.json", self.projects)
        self.save(
            "responses/projects_control.json", self.project_control(self.projects)
        )
        run_cli("surveys", "--run", str(self.run_dir))
        fewer = json.loads(json.dumps(self.projects))
        fewer["records"] = fewer["records"][:2]
        fewer["totalSize"] = 2
        self.save("responses/projects.json", fewer)
        self.save("responses/projects_control.json", self.project_control(fewer))
        code, out = run_cli("upcoming", "--run", str(self.run_dir))
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("run 'surveys' again", out["message"])


if __name__ == "__main__":
    unittest.main()
