"""Public preflight and CLI contracts with real inventory and isolated inputs."""

from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from functools import partial
from typing import Any
from unittest.mock import patch

from engine import weekly_preflight
from engine.report_detection import load_detection_config
from engine.schedule_config import load_weekly_schedule
from engine.source_config import load_source_configuration
from engine.source_inventory import SourceInventoryError
from engine.weekly_run import WeeklyRunError, build_weekly_run
from tests.support.weekly_cases import IsolatedWeeklyCase

RUN_ID = "NPS_WEEK_2026-08-04_2026-08-10"


class WeeklyPreflightTest(IsolatedWeeklyCase):
    """Characterize current readiness, configuration and operator CLI behavior."""

    def _state(self) -> dict[str, bytes | None]:
        return {
            p.relative_to(self.root).as_posix(): None if p.is_dir() else p.read_bytes()
            for p in self.root.rglob("*")
        }

    def _preflight(self, date: str = "8/3/2026", **kwargs: Any) -> dict[str, Any]:
        before = self._state()
        try:
            result = weekly_preflight.run_weekly_preflight(
                date, test_mode=True, **kwargs
            )
            for key in ("input_directory", "output_root", "expected_run_directory"):
                self.assert_local(result[key])
            return result
        finally:
            self.assertEqual(self._state(), before, "Preflight must be read-only")

    def _sources(self, configuration: dict[str, Any]) -> None:
        path = self.root / "report_sources.json"
        path.write_text(json.dumps(configuration), encoding="utf-8")

        def load(*_args: object, **_kwargs: object) -> dict[str, Any]:
            return load_source_configuration(path)

        for module in (
            "engine.weekly_preflight",
            "engine.source_inventory",
            "engine.source_config",
        ):
            self.enterContext(
                patch(module + ".load_source_configuration", side_effect=load)
            )

    def _schedule(self, weekday: str, offset: int, length: int) -> None:
        path = self.root / "weekly_schedule.json"
        path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "weekly_schedule": {
                        "execution_weekday": weekday,
                        "window_start_offset_days": offset,
                        "window_length_days": length,
                    },
                }
            ),
            encoding="utf-8",
        )
        self.enterContext(
            patch(
                "engine.weekly_run.load_weekly_schedule",
                side_effect=partial(load_weekly_schedule, config_path=path),
            )
        )

    def _cli(self, *args: str) -> tuple[int, str, str]:
        before = self._state()
        stdout, stderr = io.StringIO(), io.StringIO()
        code = 0
        with (
            patch("sys.argv", ["weekly_preflight", *args]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            try:
                weekly_preflight.main()
            except SystemExit as error:
                if not isinstance(error.code, int):
                    raise AssertionError(
                        f"Unexpected CLI exit: {error.code}"
                    ) from error
                code = error.code
        self.assertEqual(self._state(), before, "CLI must not modify the TEST root")
        return code, stdout.getvalue(), stderr.getvalue()

    def test_invalid_reference_date_has_actionable_error(self) -> None:
        for value in ("not-a-date", "2/30/2026", "2026-08-03"):
            with (
                self.subTest(date=value),
                self.assertRaisesRegex(
                    weekly_preflight.WeeklyPreflightError,
                    "Invalid reference date. Use M/D/YYYY format, "
                    "for example 8/3/2026.",
                ) as caught,
            ):
                self._preflight(value)
            self.assertIsInstance(caught.exception.__cause__, ValueError)

    def test_monday_required_despite_configured_execution_day(self) -> None:
        # NPS-007: preflight ignores the configurable weekly-run execution weekday.
        self.populate("complete_weekly")
        self._schedule("wednesday", 1, 7)
        run = build_weekly_run("8/5/2026", output_root=self.output)
        self.assertEqual(run.execution_weekday, "wednesday")
        with self.assertRaisesRegex(
            weekly_preflight.WeeklyPreflightError, "must be a Monday"
        ):
            self._preflight("8/5/2026")
        self.assertEqual(self._preflight()["status"], "READY_TO_PROCESS")
        with self.assertRaisesRegex(
            WeeklyRunError, "configured execution day is Wednesday"
        ):
            build_weekly_run("8/3/2026", output_root=self.output)

    def test_window_ignores_configured_offsets(self) -> None:
        # NPS-007: preflight keeps Tuesday-to-Monday despite different schedule offsets.
        self.populate("complete_weekly")
        self._schedule("monday", 3, 2)
        run = build_weekly_run("8/3/2026", output_root=self.output)
        self.assertEqual(
            (run.window_start, run.window_end), ("08/06/2026", "08/07/2026")
        )
        result = self._preflight()
        self.assertEqual(
            (result["window_start"], result["window_end"]), ("8/4/2026", "8/10/2026")
        )
        self.assertEqual(result["weekly_run_id"], RUN_ID)
        self.assertNotEqual(result["weekly_run_id"], run.weekly_run_id)

    def test_environment_change_does_not_rebind_imported_paths(self) -> None:
        # NPS-017: inherited TEST constant patches remain necessary after env changes.
        self.populate("complete_weekly")
        later_root = self.root / "later_environment"
        with patch.dict(os.environ, {"BTS_SELAM_DATA_ROOT": str(later_root)}):
            result = self._preflight()
        self.assertEqual(result["input_directory"], str(self.pending))
        self.assertEqual(result["output_root"], str(self.output))
        self.assertEqual(result["status"], "READY_TO_PROCESS")
        self.assertFalse(later_root.exists())

    def test_unknown_source_group_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            weekly_preflight.WeeklyPreflightError,
            "Source group does not exist: fixture_missing",
        ):
            self._preflight(source_group="fixture_missing")

    def test_disabled_source_group_is_rejected(self) -> None:
        configuration = load_source_configuration()
        configuration["source_groups"]["weekly_upcoming"]["enabled"] = False
        self._sources(configuration)
        with self.assertRaisesRegex(
            weekly_preflight.WeeklyPreflightError,
            "Source group is disabled: weekly_upcoming",
        ):
            self._preflight()

    def test_input_file_is_rejected_as_directory(self) -> None:
        path = self.root / "not_a_directory"
        path.write_text("Synthetic file", encoding="utf-8")
        with patch("engine.weekly_preflight.TEST_INPUT", path):
            with self.assertRaises(weekly_preflight.WeeklyPreflightError) as caught:
                self._preflight()
        self.assertEqual(
            str(caught.exception), f"Input path is not a directory: {path}"
        )

    def test_ambiguous_source_mapping_preserves_inventory_error(self) -> None:
        self.populate("complete_weekly")
        configuration = load_source_configuration()
        sources = configuration["source_groups"]["weekly_upcoming"]["sources"]
        sources[1]["country"] = "Argentina"
        self._sources(configuration)
        with self.assertRaises(weekly_preflight.WeeklyPreflightError) as caught:
            self._preflight()
        self.assertEqual(
            str(caught.exception),
            "Two enabled sources use the same country and report type: "
            "upcoming_argentina and upcoming_brazil.",
        )
        self.assertIsInstance(caught.exception.__cause__, SourceInventoryError)

    def test_detected_unconfigured_report_blocks_ready_sources(self) -> None:
        self.populate("complete_weekly")
        self.populate("unconfigured_source")
        stock = self._preflight()
        self.assertEqual(stock["status"], "BLOCKED")
        self.assertEqual(stock["issues"], ["Files require report-detection review: 1"])
        self.assertEqual(stock["inventory"]["review_files"], 1)
        self.assertEqual(stock["inventory"]["unconfigured_files"], 0)
        self.assertEqual(stock["inventory"]["missing_required_sources"], 0)
        detection = load_detection_config()
        detection["report_patterns"].append(
            {
                "country": "Chile",
                "report_type": "Upcoming",
                "patterns": ["Chile Upcoming Deliveries/NPS"],
            }
        )
        path = self.root / "report_detection.json"
        path.write_text(json.dumps(detection), encoding="utf-8")
        with patch("engine.report_detection.CONFIG_FILE", path):
            result = self._preflight()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["issues"], ["Unknown or unconfigured reports detected: 1"]
        )
        inventory = result["inventory"]
        self.assertEqual(
            (
                inventory["matched_files"],
                inventory["unconfigured_files"],
                inventory["review_files"],
            ),
            (3, 1, 0),
        )
        self.assertEqual(inventory["missing_required_sources"], 0)

    def test_optional_group_allows_missing_reports(self) -> None:
        result = self._preflight(source_group="last_results")
        self.assertTrue(result["allow_partial_run"])
        self.assertEqual(result["status"], "READY_TO_PROCESS")
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["inventory"]["files_scanned"], 0)
        self.assertTrue(
            all(
                s["status"] == "MISSING" and not s["required"]
                for s in result["inventory"]["sources"]
            )
        )

    def test_cli_ready_human_output_explains_six_report_scope(self) -> None:
        self.populate("complete_six_reports")
        code, stdout, stderr = self._cli("8/3/2026", "--test")
        self.assertEqual((code, stderr), (0, ""))
        for value in (
            "NPS WEEKLY PREFLIGHT",
            "Environment: TEST",
            "Reference date: 8/3/2026",
            "Weekly window: 8/4/2026 - 8/10/2026",
            "Weekly Run ID: " + RUN_ID,
            "Input directory: " + str(self.pending),
            "EXPECTED SOURCES",
            "FILES",
            "Files scanned: 6",
            "Matched files: 3",
            "Known out of scope: 3",
            "Detection review: 0",
            "Unknown reports: 0",
            "Duplicate sources: 0",
            "Missing required sources: 0",
            "STATUS",
            "READY_TO_PROCESS",
        ):
            self.assertIn(value, stdout)
        for country in ("Argentina", "Brazil", "Mexico"):
            self.assertIn(country + " upcoming: RECEIVED", stdout)
            self.assertIn("weekly_" + country + "_upcoming.eml", stdout)
        self.assertNotIn("ISSUES", stdout)
        self.assertFalse(self.output.exists())

    def test_cli_blocked_human_output_lists_missing_source_and_policy(self) -> None:
        self.populate("missing_brazil")
        code, stdout, stderr = self._cli("8/3/2026", "--test")
        self.assertEqual((code, stderr), (2, ""))
        for value in (
            "Brazil upcoming: MISSING",
            "Missing required sources: 1",
            "BLOCKED",
            "ISSUES",
            "- Missing required source: Brazil upcoming",
            "- Partial weekly runs are disabled.",
        ):
            self.assertIn(value, stdout)
        self.assertNotIn("weekly_Brazil_upcoming.eml", stdout)

    def test_cli_default_production_uses_injected_paths_and_json(self) -> None:
        # NPS-017: redirect both imported PRODUCTION constants before the default CLI.
        pending = self.populate("complete_weekly", self.root / "production_input")
        output = self.root / "production_output"
        with (
            patch("engine.weekly_preflight.PRODUCTION_INPUT", pending),
            patch("engine.weekly_preflight.PRODUCTION_OUTPUT", output),
        ):
            code, stdout, stderr = self._cli("8/3/2026", "--json")
        self.assertEqual((code, stderr), (0, ""))
        result = json.loads(stdout)
        self.assertEqual(result["environment"], "PRODUCTION")
        self.assertEqual(result["status"], "READY_TO_PROCESS")
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["weekly_run_id"], RUN_ID)
        self.assertEqual(result["input_directory"], str(self.assert_local(pending)))
        self.assertEqual(result["output_root"], str(self.assert_local(output)))
        self.assertEqual(result["expected_run_directory"], str(output / RUN_ID))
        self.assertFalse(output.exists())

    def test_cli_duplicate_json_is_parseable_even_on_blocked_exit(self) -> None:
        self.populate("duplicate_source")
        code, stdout, stderr = self._cli("8/3/2026", "--test", "--json")
        self.assertEqual((code, stderr), (2, ""))
        result = json.loads(stdout)
        self.assertEqual(result["environment"], "TEST")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["issues"], ["Duplicate source: Mexico upcoming (2 files)"]
        )
        self.assertEqual(result["inventory"]["files_scanned"], 4)
        self.assertEqual(result["inventory"]["duplicate_sources"], 1)

    def test_cli_preflight_failure_uses_exit_one_and_actionable_message(self) -> None:
        for date, message in (
            ("not-a-date", "Invalid reference date. Use M/D/YYYY format"),
            ("8/5/2026", "The reference date must be a Monday."),
        ):
            with self.subTest(date=date):
                code, stdout, stderr = self._cli(date, "--test", "--json")
                self.assertEqual((code, stderr), (1, ""))
                self.assertIn("NPS WEEKLY PREFLIGHT FAILED", stdout)
                self.assertIn(message, stdout)
                self.assertNotIn('"inventory"', stdout)

    def test_cli_missing_reference_date_is_usage_error(self) -> None:
        code, stdout, stderr = self._cli("--test")
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("usage:", stderr)
        self.assertIn("the following arguments are required: reference_date", stderr)

    def test_cli_unknown_option_is_usage_error(self) -> None:
        code, stdout, stderr = self._cli("8/3/2026", "--test", "--fixture-unknown")
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("unrecognized arguments: --fixture-unknown", stderr)

    def test_cli_help_describes_date_environment_and_json_options(self) -> None:
        code, stdout, stderr = self._cli("--help")
        self.assertEqual((code, stderr), (0, ""))
        self.assertIn("Reference Monday in M/D/YYYY format.", stdout)
        self.assertIn("--test", stdout)
        self.assertIn("Use isolated testing input and output paths.", stdout)
        self.assertIn("--json", stdout)
        self.assertIn("Print the structured result as JSON.", stdout)
