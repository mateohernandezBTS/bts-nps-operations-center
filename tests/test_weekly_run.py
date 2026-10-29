"""Independent weekly run creation and persistence cases."""

from __future__ import annotations

from dataclasses import asdict

from engine.weekly_run import WeeklyRunError, build_weekly_run, create_weekly_run
from tests.support.weekly_cases import IsolatedWeeklyCase, read_json


class WeeklyRunTest(IsolatedWeeklyCase):
    def test_default_window(self) -> None:
        run = build_weekly_run("8/3/2026", output_root=self.output)
        self.assertEqual(run.weekly_run_id, "NPS_WEEK_2026-08-04_2026-08-10")
        self.assertEqual(
            (run.reference_date, run.window_start, run.window_end),
            ("08/03/2026", "08/04/2026", "08/10/2026"),
        )
        self.assertEqual(
            (run.execution_weekday, run.window_length_days, run.status),
            ("monday", 7, "INITIALIZED"),
        )
        self.assertEqual(len(run.expected_sources), 3)
        self.assertEqual(run.required_sources, run.expected_sources)
        self.assert_local(run.output_directory)
        self.assertFalse(self.output.exists())

    def test_manifest_persistence(self) -> None:
        run, path = create_weekly_run("8/3/2026", output_root=self.output)
        self.assertEqual(read_json(self.assert_local(path)), asdict(run))
        for source in read_json(path)["expected_sources"]:
            self.assertEqual(source["status"], "MISSING")
            self.assertIsNone(source["matched_file"])

    def test_existing_run_rejected(self) -> None:
        _, path = create_weekly_run("8/3/2026", output_root=self.output)
        original = path.read_bytes()
        with self.assertRaisesRegex(WeeklyRunError, "already exists"):
            create_weekly_run("8/3/2026", output_root=self.output)
        self.assertEqual(path.read_bytes(), original)

    def test_invalid_weekday(self) -> None:
        with self.assertRaisesRegex(WeeklyRunError, "Wednesday"):
            build_weekly_run("8/5/2026", output_root=self.output)
        self.assertFalse(self.output.exists())
