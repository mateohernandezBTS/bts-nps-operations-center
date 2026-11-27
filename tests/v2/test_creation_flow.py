"""V2-2 end to end through the CLI with a simulated connector (no Salesforce)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from tests.v2.test_cli import CliRunMixin, run_cli

ORG_HOST = "https://example.invalid/act/survey/runtimeApp.app"
OPERATOR = {
    "CreatedById": "005AA0000000001AAA",
    "CreatedBy": {"Name": "Synthetic User"},
}


class FakeSalesforce:
    """Answers the calls the engine prints, like the BTS connector would."""

    def __init__(self) -> None:
        self.counter = 0
        self.invitations: dict[str, dict[str, Any]] = {}
        self.survey_sets: list[dict[str, Any]] = []
        self.projects: dict[str, str] = {}
        self.fail_on: str = ""
        self.existing_check: set[str] = set()

    def _id(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}ZZ{self.counter:010d}AAA"

    def answer(self, call: dict[str, Any]) -> str:
        tool, data = call["tool"], call["input"]
        if call["kind"] == self.fail_on:
            return json.dumps({"success": False, "errors": ["SIMULATED_FAILURE"]})
        if tool == "salesforce_describe":
            return json.dumps(
                {
                    "name": data["sobjectType"],
                    "createable": True,
                    "updateable": True,
                    "fields": [{"name": "Name", "createable": True}],
                }
            )
        if tool == "salesforce_query" and call["kind"] == "check":
            found = call["key"] in self.existing_check
            records = [{"Id": "aHqAA0000000777AAA"}] if found else []
            return json.dumps(
                {"totalSize": len(records), "done": True, "records": records}
            )
        if tool == "salesforce_query":  # read the invitation
            invitation_id = data["query"].split("'")[1]
            invitation = self.invitations[invitation_id]
            record = {"Id": invitation_id, **invitation, **OPERATOR}
            return json.dumps({"totalSize": 1, "done": True, "records": [record]})
        if tool == "salesforce_create" and data["sobjectType"] == "SurveyInvitation":
            new_id = self._id("0Ki")
            survey = data["data"]["Name"].split(" for ")[0].lower().replace(" ", "_")
            self.invitations[new_id] = {
                "InvitationLink": (
                    f"{ORG_HOST}?invitationId={new_id[:15]}&surveyName={survey}"
                    f"&UUID=00000000-0000-0000-0000-{self.counter:012d}"
                )
            }
            return json.dumps({"id": new_id, "success": True, "errors": []})
        if tool == "salesforce_create":
            new_id = self._id("aHq")
            self.survey_sets.append({"Id": new_id, **data["data"]})
            return json.dumps({"id": new_id, "success": True, "errors": []})
        if tool == "salesforce_update":
            self.projects[data["id"]] = data["data"]["Survey_Invitation__c"]
            return json.dumps({"success": True})
        raise AssertionError(f"Unexpected call {call}")


class CreationFlowTest(CliRunMixin):
    """Reuses the V2-1 CLI fixtures: 3 projects, 2 pending sessions."""

    def setUp(self) -> None:
        super().setUp()
        self.fake = FakeSalesforce()
        self.response_file = self.directory / "response.json"

    # --- helpers --------------------------------------------------------------
    def upcoming(self) -> dict[str, Any]:
        self.select()
        self.save("responses/projects.json", self.projects)
        self.save(
            "responses/projects_control.json", self.project_control(self.projects)
        )
        run_cli("surveys", "--run", str(self.run_dir))
        self.save("responses/survey_sets_01.json", self.sets)
        self.save("responses/survey_sets_01_control.json", self.set_control(self.sets))
        code, out = run_cli(
            "upcoming",
            "--run",
            str(self.run_dir),
            "--run-id",
            "V2-CREATE-TEST",
            "--watchlist",
            str(self.directory / "absent.json"),
        )
        self.assertEqual(code, 0, out)
        return out

    def cli(self, *argv: str) -> dict[str, Any]:
        code, out = run_cli(*argv[:1], "--run", str(self.run_dir), *argv[1:])
        self.assertEqual(code, 0, out)
        return out

    def plan_and_approve(
        self, recheck_records: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        plan = self.cli("plan")
        approved = self.cli("approve", "--code", plan["approval_code"])
        (query,) = approved["queries"]
        self.save(
            query["save_as"],
            {"totalSize": 0, "done": True, "records": recheck_records or []},
        )
        return plan

    def run_all(self, first: dict[str, Any]) -> dict[str, Any]:
        out = first
        guard = 0
        while "call" in out:
            guard += 1
            self.assertLess(guard, 100)
            self.response_file.write_text(
                self.fake.answer(out["call"]), encoding="utf-8"
            )
            out = self.cli("record", "--response-file", str(self.response_file))
        return out

    def reconcile(self) -> dict[str, Any]:
        first = self.cli("reconcile")
        names = [q["name"] for q in first["queries"]]
        self.assertEqual(
            names[:2], ["after_survey_sets_01", "after_survey_sets_01_control"]
        )
        sets = self.sets["records"] + [
            {
                "attributes": {"type": "Survey_Set__c"},
                "Id": s["Id"],
                "Project__c": s["Project__c"],
                "Survey__c": s["Survey__c"],
                "Survey__r": {"Name": "Synthetic"},
                "Survey_Language__c": s["Survey_Language__c"],
                "SurveyNPS__c": s["SurveyNPS__c"],
                "Survey_Invitation_Link__c": s["Survey_Invitation_Link__c"],
                "QR_Code_URL__c": s["QR_Code_URL__c"],
                "CreatedDate": "2026-11-27T12:00:00.000+0000",
            }
            for s in self.fake.survey_sets
        ]
        raw = {"totalSize": len(sets), "done": True, "records": sets}
        self.save("responses/after_survey_sets_01.json", raw)
        self.save("responses/after_survey_sets_01_control.json", self.set_control(raw))
        if "after_projects" in names:
            records = [
                {"Id": pid, "Survey_Invitation__c": inv}
                for pid, inv in self.fake.projects.items()
            ]
            self.save(
                "responses/after_projects.json",
                {"totalSize": len(records), "done": True, "records": records},
            )
        return self.cli("reconcile")

    # --- tests ----------------------------------------------------------------
    def test_happy_path_creates_and_reconciles_every_survey(self) -> None:
        upcoming = self.upcoming()
        plan = self.plan_and_approve()
        self.assertEqual(
            plan["surveys_to_create"], upcoming["summary"]["surveys_to_create"]
        )
        self.assertTrue(Path(plan["outputs"]["plan_html"]).exists())

        first = self.cli("execute")
        self.assertEqual(first["call"]["tool"], "salesforce_describe")
        self.assertFalse(first["call"]["writes_to_salesforce"])
        done = self.run_all(first)
        self.assertEqual(done["run_status"], "done")
        self.assertEqual(done["error"], "")

        created = len(self.fake.survey_sets)
        self.assertEqual(created, plan["surveys_to_create"])
        self.assertEqual(len(self.fake.invitations), created)
        for survey_set in self.fake.survey_sets:
            link = survey_set["Survey_Invitation_Link__c"]
            self.assertIn(f"invitationId={survey_set['Survey_Invitation__c']}&", link)
            self.assertTrue(
                link.endswith("&guestUserLang=" + survey_set["Survey_Language__c"])
            )

        result = self.reconcile()
        self.assertEqual(result["counts"]["created"], created)
        self.assertEqual(result["operator"], "Synthetic User")
        for path in result["outputs"].values():
            self.assertTrue(Path(path).exists(), path)
        self.assertEqual(result["summary_after"]["pending"], 0)
        page = Path(result["outputs"]["result_html"]).read_text(encoding="utf-8")
        self.assertIn("Created", page)
        with zipfile.ZipFile(result["outputs"]["creation_log"]) as book:
            surveys = book.read("xl/worksheets/sheet1.xml").decode("utf-8")
            run = book.read("xl/worksheets/sheet2.xml").decode("utf-8")
        self.assertEqual(surveys.count(">created<"), created)
        self.assertIn(plan["approval_code"], run)
        audit = json.loads(Path(result["outputs"]["audit"]).read_text(encoding="utf-8"))
        self.assertEqual(len(audit["surveys"]), created)
        self.assertTrue(all(c["result"] for c in audit["calls"]))

    def test_pilot_plan_with_only_one_session(self) -> None:
        self.upcoming()
        report = json.loads((self.run_dir / "report.json").read_text(encoding="utf-8"))
        target = report["pending"][0]["project_id"]
        plan = self.cli("plan", "--only", target[:15])
        self.assertEqual(plan["sessions"], 1)
        self.assertEqual(
            plan["surveys_to_create"], len(report["pending"][0]["surveys_to_create"])
        )
        code, out = run_cli(
            "plan", "--run", str(self.run_dir), "--only", target, "--exclude", target
        )
        self.assertEqual(code, 2)
        self.assertIn("either --exclude or --only", out["message"])

    def test_approval_must_match_the_current_plan(self) -> None:
        self.upcoming()
        self.cli("plan")
        code, out = run_cli(
            "approve", "--run", str(self.run_dir), "--code", "000000000000"
        )
        self.assertEqual(code, 2)
        self.assertIn("does not match", out["message"])
        code, out = run_cli("execute", "--run", str(self.run_dir))
        self.assertEqual(code, 2)
        self.assertIn("not approved", out["message"])

    def test_recheck_finding_a_survey_changes_the_plan(self) -> None:
        self.upcoming()
        plan = self.cli("plan")
        doc = json.loads(
            (self.run_dir / "creation" / "plan.json").read_text(encoding="utf-8")
        )
        target = doc["commands"][0]
        self.cli("approve", "--code", plan["approval_code"])
        self.save(
            "responses/creation_recheck.json",
            {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "Id": "aHqAA0000000555AAA",
                        "Project__c": target["project_id"],
                        "Survey__c": target["survey_id"],
                        "SurveyNPS__c": target["kind"] == "NPS",
                    }
                ],
            },
        )
        out = self.cli("execute")
        self.assertTrue(out["plan_changed"])
        self.assertNotEqual(out["approval_code"], plan["approval_code"])
        self.assertEqual(out["surveys_to_create"], plan["surveys_to_create"] - 1)
        code, out = run_cli("execute", "--run", str(self.run_dir))
        self.assertEqual(code, 2)  # the new plan needs a new approval
        self.assertEqual(self.fake.survey_sets, [])

    def test_a_survey_found_at_its_check_is_skipped(self) -> None:
        self.upcoming()
        self.plan_and_approve()
        doc = json.loads(
            (self.run_dir / "creation" / "plan.json").read_text(encoding="utf-8")
        )
        self.fake.existing_check = {doc["commands"][0]["key"]}
        done = self.run_all(self.cli("execute"))
        self.assertEqual(done["run_status"], "done")
        self.assertEqual(len(self.fake.survey_sets), len(doc["commands"]) - 1)
        result = self.reconcile()
        self.assertEqual(result["counts"]["already existed"], 1)

    def test_a_failed_write_stops_the_run_and_is_reported(self) -> None:
        self.upcoming()
        self.plan_and_approve()
        self.fake.fail_on = "create_survey_set"
        done = self.run_all(self.cli("execute"))
        self.assertEqual(done["run_status"], "failed")
        self.assertIn("rejected the create", done["error"])
        self.assertIn("reconcile", done["next"])
        self.assertEqual(self.fake.survey_sets, [])
        self.assertEqual(len(self.fake.invitations), 1)  # stopped right after
        code, out = run_cli(
            "record",
            "--run",
            str(self.run_dir),
            "--response-file",
            str(self.response_file),
        )
        self.assertEqual(code, 2)  # nothing more can be recorded
        result = self.reconcile()
        self.assertEqual(result["counts"]["partial"], 1)
        self.assertEqual(result["counts"]["created"], 0)
        self.assertGreaterEqual(result["counts"]["not run"], 1)

    def test_missing_permissions_stop_before_any_write(self) -> None:
        self.upcoming()
        self.plan_and_approve()
        self.fake.fail_on = ""
        first = self.cli("execute")
        self.response_file.write_text(
            json.dumps({"name": "SurveyInvitation", "createable": False, "fields": []}),
            encoding="utf-8",
        )
        out = self.cli("record", "--response-file", str(self.response_file))
        self.assertEqual(out["run_status"], "failed")
        self.assertIn("not createable", out["error"])
        self.assertEqual(first["call"]["kind"], "preflight")
        self.assertEqual(self.fake.invitations, {})

    def test_record_reads_the_transcript_and_refuses_double_writes(self) -> None:
        self.upcoming()
        self.plan_and_approve()
        transcript = self.directory / "session.jsonl"
        lines: list[str] = []

        def call_and_log(call: dict[str, Any], times: int = 1) -> None:
            for number in range(times):
                use_id = f"toolu_{len(lines)}_{number}"
                lines.append(
                    json.dumps(
                        {
                            "message": {
                                "content": [
                                    {
                                        "type": "tool_use",
                                        "id": use_id,
                                        "name": "mcp__BTS__" + call["tool"],
                                        "input": call["input"],
                                    }
                                ]
                            }
                        }
                    )
                )
                lines.append(
                    json.dumps(
                        {
                            "message": {
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": use_id,
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": self.fake.answer(call),
                                            }
                                        ],
                                    }
                                ]
                            }
                        }
                    )
                )
            transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")

        out = self.cli("execute")
        while out["call"]["kind"] != "create_invitation":
            call_and_log(out["call"])
            out = self.cli("record", "--transcript", str(transcript))
        call_and_log(out["call"], times=2)  # the same write run twice
        out = self.cli("record", "--transcript", str(transcript))
        self.assertEqual(out["run_status"], "failed")
        self.assertIn("executed 2 times", out["error"])


if __name__ == "__main__":
    import unittest

    unittest.main()
