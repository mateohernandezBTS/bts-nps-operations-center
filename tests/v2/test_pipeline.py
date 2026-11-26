"""Pipeline over the certified stages, including equivalence with the e-mail path."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from typing import Any

from engine.stages.business_rules import apply_business_rules
from engine.stages.normalize import normalize_boolean, normalize_records
from engine.stages.worklist import extract_salesforce_id, generate_worklist
from nps_v2.domain import DomainError, ProjectSnapshot, SalesforceId
from nps_v2.pipeline import (
    Decision,
    PipelineError,
    ReportScope,
    load_report_scope,
    run_pipeline,
    windowless_operational_config,
)
from nps_v2.registry import load_registry
from nps_v2.selection import SearchFilters, range_selection
from tests.support.stage_cases import parsed_rows

WEEK = range_selection(date(2026, 11, 24), date(2026, 11, 30))
_counter = iter(range(1, 10_000))


def snapshot(**overrides: object) -> ProjectSnapshot:
    values: dict[str, object] = {
        "project_id": SalesforceId(f"a0gAA{next(_counter):010d}AAA"),
        "name": "Synthetic Session",
        "billing_country": "Argentina",
        "start_date": date(2026, 11, 26),
        "end_date": date(2026, 11, 26),
        "client_name": "Synthetic Client",
        "sub_type": "Workshop",
        "status": "Conf",
        "all_staffings": "Facilitator One",
        "ignore_reporting": False,
    }
    values.update(overrides)
    return ProjectSnapshot(**values)  # type: ignore[arg-type]


class PipelineBucketsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_registry()
        self.scope = load_report_scope()

    def run_one(self, project: ProjectSnapshot, **kwargs: Any) -> Any:
        return run_pipeline([project], WEEK, self.registry, self.scope, **kwargs)

    def test_eligible_project_reaches_the_worklist(self) -> None:
        project = snapshot(billing_country="Nexo")
        result = self.run_one(project)
        (entry,) = result.worklist
        self.assertTrue(entry.ready)
        self.assertEqual(entry.country_code, "BR")
        self.assertEqual(entry.row["Project ID"], str(project.project_id))
        self.assertEqual(entry.row["Date"], "11/26/2026")
        self.assertTrue(entry.row["Link for Results"].endswith(str(project.project_id)))
        self.assertEqual(result.classified[0].decision, Decision.ELIGIBLE)

    def test_certified_rules_decide(self) -> None:
        cases = {
            "prelim": (snapshot(status="Prelim"), "STATUS_NOT_ELIGIBLE"),
            "ignore reporting": (snapshot(ignore_reporting=True), "IGNORE_REPORTING"),
            "pod": (snapshot(sub_type="Group/POD Coaching"), "POD"),
            "bts client": (
                snapshot(client_name="BTS Germany - Synthetic"),
                "BTS_CLIENT",
            ),
        }
        for name, (project, code) in cases.items():
            with self.subTest(case=name):
                result = self.run_one(project)
                (classified,) = result.excluded
                self.assertIn(code, classified.decision_codes)
                self.assertEqual(result.worklist, ())

    def test_review_rule_and_empty_required_field(self) -> None:
        revenue = self.run_one(snapshot(name="Synthetic Session REVENUE"))
        self.assertEqual(revenue.review[0].decision_codes, ("REVENUE_ADMIN",))
        empty_client = self.run_one(snapshot(client_name=""))
        self.assertEqual(empty_client.review[0].decision_codes, ("VALIDATION_ISSUE",))
        self.assertIn("client_name", empty_client.review[0].validation_issues)

    def test_report_scope_lists_rows_instead_of_hiding_them(self) -> None:
        cases = {
            "cancelled": (snapshot(status="Cancelled"), "status Cancelled"),
            "empty sub-type": (snapshot(sub_type="  "), "sub-type (empty)"),
            "license": (snapshot(sub_type="license"), "sub-type license"),
        }
        for name, (project, reason) in cases.items():
            with self.subTest(case=name):
                result = self.run_one(project)
                (out,) = result.out_of_scope
                self.assertIn(reason, out.reason)
                self.assertEqual(result.classified, ())

    def test_text_filters_are_applied_first(self) -> None:
        keep = snapshot(client_name="Alpha Synthetic")
        drop = snapshot(client_name="Beta Synthetic")
        selection = WEEK.with_filters(filters=SearchFilters(client="alpha"))
        result = run_pipeline([keep, drop], selection, self.registry, self.scope)
        self.assertEqual(result.filtered_out, (drop,))
        self.assertEqual([e.project for e in result.worklist], [keep])

    def test_every_project_lands_in_exactly_one_bucket(self) -> None:
        projects = [
            snapshot(),
            snapshot(status="Prelim"),
            snapshot(status="Cancelled"),
            snapshot(name="X REVENUE"),
            snapshot(client_name="Nope"),
        ]
        selection = WEEK.with_filters(filters=SearchFilters(client="synthetic"))
        result = run_pipeline(projects, selection, self.registry, self.scope)
        buckets = (
            list(result.filtered_out)
            + [o.project for o in result.out_of_scope]
            + [c.project for c in result.classified]
        )
        self.assertCountEqual(buckets, projects)
        self.assertEqual(len(result.ready), 1)

    def test_contract_violations_stop_the_run(self) -> None:
        cases = {
            "outside selection": snapshot(start_date=date(2026, 12, 1)),
            "unknown country": snapshot(billing_country="Chile"),
        }
        for name, project in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(PipelineError):
                    self.run_one(project)
        only_ar = WEEK.with_filters(country_codes=("AR",))
        with self.assertRaisesRegex(PipelineError, "selection excludes"):
            run_pipeline(
                [snapshot(billing_country="Mexico")], only_ar, self.registry, self.scope
            )
        twin = snapshot()
        with self.assertRaisesRegex(PipelineError, "Duplicate"):
            run_pipeline([twin, twin], WEEK, self.registry, self.scope)

    def test_window_is_disabled_without_touching_the_shipped_config(self) -> None:
        original = {"weekly_window": {"enabled": True, "reference_monday": "7/27/2026"}}
        changed = windowless_operational_config(original)
        self.assertFalse(changed["weekly_window"]["enabled"])
        self.assertTrue(original["weekly_window"]["enabled"])


class ReportScopeFileTest(unittest.TestCase):
    def test_shipped_scope(self) -> None:
        scope = load_report_scope()
        self.assertEqual(scope.excluded_statuses, frozenset({"cancelled"}))
        self.assertEqual(scope.excluded_sub_types, frozenset({"", "license"}))

    def test_invalid_files_fail_closed(self) -> None:
        documents = ["{", "{}", '{"excluded_statuses": "x", "excluded_sub_types": []}']
        for text in documents:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "scope.json"
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(PipelineError):
                    load_report_scope(path)

    def test_everything_scope_keeps_all(self) -> None:
        self.assertIsNone(ReportScope.everything().reason(snapshot(sub_type="")))


# --- Equivalence with the certified e-mail path ------------------------------------

EQUIVALENCE_FIXTURES = (
    "weekly_Argentina_upcoming",
    "weekly_Brazil_upcoming",
    "weekly_Mexico_upcoming",
    "classification_Argentina_rules",
    "classification_Brazil_normalization",
    "classification_Mexico_worklist_review",
)
COMPARED_RULE_KEYS = (
    "validation_status",
    "validation_issues",
    "decision",
    "decision_codes",
    "decision_reasons",
)


def snapshot_from_parsed(raw: dict[str, str]) -> ProjectSnapshot | None:
    """The snapshot Salesforce would return for a parsed row, or None if impossible.

    Salesforce cannot produce invalid dates, unknown booleans or a missing Id, so those
    synthetic e-mail rows have no Salesforce equivalent and are skipped.
    """
    try:
        start = datetime.strptime(raw["start_date"], "%m/%d/%Y").date()
        end = (
            datetime.strptime(raw["end_date"], "%m/%d/%Y").date()
            if raw["end_date"]
            else None
        )
        ignore, _ = normalize_boolean(raw["ignore_reporting"])
        project_id = SalesforceId(extract_salesforce_id(raw["project_url"]))
    except (ValueError, DomainError):
        return None
    if ignore is None:
        return None
    invitation: SalesforceId | None
    try:
        invitation = SalesforceId(raw["survey_invitation"])
    except DomainError:
        invitation = None
    return ProjectSnapshot(
        project_id=project_id,
        name=raw["project_name"],
        billing_country=raw["billing_office"],
        start_date=start,
        end_date=end,
        client_name=raw["client_name"],
        sub_type=raw["project_sub_type"],
        status=raw["status"],
        all_staffings=raw["all_staffings"],
        ignore_reporting=ignore,
        survey_invitation_id=invitation,
    )


class EmailEquivalenceTest(unittest.TestCase):
    """Same rows through both paths must give the same decisions and worklist."""

    def test_salesforce_path_matches_email_path(self) -> None:
        registry = load_registry()
        compared = 0
        for fixture_id in EQUIVALENCE_FIXTURES:
            pairs = []
            seen: set[SalesforceId] = set()
            for raw in parsed_rows(fixture_id).values():
                project = snapshot_from_parsed(raw)
                if project is not None and project.project_id not in seen:
                    seen.add(project.project_id)
                    pairs.append((raw, project))
            if not pairs:
                continue
            with self.subTest(fixture=fixture_id):
                compared += self.assert_equivalent(pairs, registry)
        self.assertGreaterEqual(compared, 80, "equivalence must cover the fixture rows")

    def assert_equivalent(
        self, pairs: list[tuple[dict[str, str], ProjectSnapshot]], registry: Any
    ) -> int:
        raws = [raw for raw, _ in pairs]
        projects = [project for _, project in pairs]
        start = min(p.start_date for p in projects)
        end = max(p.start_date for p in projects)

        normalized, _ = normalize_records([dict(r) for r in raws])
        email_rules = apply_business_rules(normalized)
        email_worklist = generate_worklist(
            email_rules["eligible"], config=windowless_operational_config()
        )["worklist"]

        result = run_pipeline(
            projects, range_selection(start, end), registry, ReportScope.everything()
        )

        email_by_id = {
            extract_salesforce_id(r["project_url"]): r
            for r in email_rules["classified"]
        }
        for classified in result.classified:
            expected = email_by_id[str(classified.project.project_id)]
            actual = {
                "validation_status": "VALID"
                if not classified.validation_issues
                else "REVIEW",
                "validation_issues": classified.validation_issues,
                "decision": classified.decision.value,
                "decision_codes": " | ".join(classified.decision_codes),
                "decision_reasons": " | ".join(classified.decision_reasons),
            }
            self.assertEqual(
                actual,
                {key: expected[key] for key in COMPARED_RULE_KEYS},
                msg=str(classified.project.project_id),
            )

        def comparable(row: dict[str, Any]) -> str:
            return json.dumps(
                {k: v for k, v in row.items() if k != "Project URL"}, sort_keys=True
            )

        self.assertEqual(
            [comparable(dict(e.row)) for e in result.worklist],
            [comparable(r) for r in email_worklist],
        )
        self.assertEqual(len(result.classified), len(pairs))
        return len(pairs)


if __name__ == "__main__":
    unittest.main()
