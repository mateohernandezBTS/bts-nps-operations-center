"""V2-2 creation plan: built only from the report's pending sessions, hashed."""

from __future__ import annotations

import copy
import json
import unittest

from nps_v2.creation.plan import CreationPlan, PlanError, build_plan
from tests.v2.synthetic import scenario


class BuildPlanTest(unittest.TestCase):
    def setUp(self) -> None:
        self.report = scenario().report
        self.plan = build_plan(self.report)

    def test_one_command_per_missing_survey_of_pending_sessions(self) -> None:
        expected = self.report["summary"]["surveys_to_create"]
        self.assertEqual(len(self.plan.commands), expected)
        pending = {row["project_id"] for row in self.report["pending"]}
        self.assertEqual({c.project_id for c in self.plan.commands}, pending)
        never = [
            row["project_id"]
            for section in ("complete", "excluded", "review", "out_of_scope")
            for row in self.report[section]
        ]
        self.assertFalse(set(never) & {c.project_id for c in self.plan.commands})

    def test_commands_carry_country_survey_and_language(self) -> None:
        brazil = [c for c in self.plan.commands if c.country == "BR"]
        self.assertEqual(
            [(c.kind, c.survey_name, c.language) for c in brazil],
            [("FACILITATORS", "Facilitators SP", "pt-BR")],
        )
        self.assertTrue(all(c.key.endswith(":" + c.kind) for c in self.plan.commands))
        self.assertTrue(all(len(c.key.split(":")[0]) == 15 for c in self.plan.commands))

    def test_order_is_by_date_then_nps_first(self) -> None:
        dates = [c.start_date for c in self.plan.commands]
        self.assertEqual(dates, sorted(dates))
        first = [c.kind for c in self.plan.commands if c.country == "AR"]
        self.assertEqual(first, ["NPS", "FACILITATORS"])

    def test_hash_is_deterministic_and_depends_on_content(self) -> None:
        again = build_plan(copy.deepcopy(self.report))
        self.assertEqual(again.hash, self.plan.hash)
        self.assertEqual(len(self.plan.hash), 64)
        self.assertEqual(self.plan.short_hash, self.plan.hash[:12])
        changed = copy.deepcopy(self.report)
        changed["pending"][0]["surveys_to_create"][0]["language"] = "en-US"
        self.assertNotEqual(build_plan(changed).hash, self.plan.hash)
        other_run = {**copy.deepcopy(self.report), "run_id": "V2-OTHER"}
        self.assertNotEqual(build_plan(other_run).hash, self.plan.hash)

    def test_exclusions_accept_15_or_18_characters(self) -> None:
        target = self.report["pending"][0]["project_id"]
        for value in (target, target[:15]):
            with self.subTest(value=value):
                plan = build_plan(self.report, exclude=[value])
                self.assertNotIn(target, {c.project_id for c in plan.commands})
                self.assertEqual(plan.excluded_projects, (target,))
                self.assertNotEqual(plan.hash, self.plan.hash)

    def test_unknown_or_invalid_exclusions_stop(self) -> None:
        complete = self.report["complete"][0]["project_id"]
        for value in (complete, "a0gAA0000000999AAA", "nope"):
            with self.subTest(value=value):
                with self.assertRaises(PlanError):
                    build_plan(self.report, exclude=[value])

    def test_round_trip_and_tamper_detection(self) -> None:
        document = json.loads(json.dumps(self.plan.to_dict()))
        self.assertEqual(CreationPlan.from_dict(document), self.plan)
        document["commands"][0]["language"] = "en-US"
        with self.assertRaises(PlanError):
            CreationPlan.from_dict(document)
        with self.assertRaises(PlanError):
            CreationPlan.from_dict({"run_id": "x"})

    def test_empty_plan(self) -> None:
        empty = {**copy.deepcopy(self.report), "pending": []}
        plan = build_plan(empty)
        self.assertEqual(plan.commands, ())
        self.assertEqual(len(plan.hash), 64)


if __name__ == "__main__":
    unittest.main()
