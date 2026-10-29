"""Real weekly orchestration and success/failure lifecycle."""

from __future__ import annotations

from tests.support.weekly_cases import IsolatedWeeklyCase, read_json


class WeeklyOrchestratorTest(IsolatedWeeklyCase):
    def test_success(self) -> None:
        path = self.prepare()
        result = self.process(path)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(
            result["processing_summary"],
            dict(
                configured_sources=3,
                processed_sources=3,
                failed_sources=0,
                received_sources=0,
                missing_sources=0,
                duplicate_sources=0,
            ),
        )
        self.assertEqual(read_json(path), result)

    def test_continue_after_failure(self) -> None:
        path = self.prepare("partial_failure")
        result = self.process(path)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            [s["status"] for s in result["expected_sources"]],
            ["PROCESSED", "FAILED", "PROCESSED"],
        )
        self.assertEqual(result["processing_summary"]["failed_sources"], 1)
        self.assertEqual(result["processing_summary"]["processed_sources"], 2)
        failed = result["expected_sources"][1]
        self.assertEqual(failed["processing_error"]["error_type"], "ValueError")
        self.assertIsNone(failed["execution_result"])
        self.assertEqual(len(list((self.root / "error").glob("*.eml"))), 1)
        self.assertEqual(read_json(path), result)

    def test_stop_on_error(self) -> None:
        path = self.prepare("partial_failure")
        with self.assertRaises(ValueError):
            self.process(path, stop_on_error=True)
        saved = read_json(path)
        self.assertEqual(saved["status"], "FAILED")
        self.assertEqual(
            [s["status"] for s in saved["expected_sources"]],
            ["PROCESSED", "FAILED", "RECEIVED"],
        )
        self.assertEqual(saved["processing_summary"]["received_sources"], 1)
        self.assertEqual(
            [p.name for p in self.pending.glob("*.eml")], ["weekly_Mexico_upcoming.eml"]
        )

    def test_source_results_and_lifecycle(self) -> None:
        result = self.process(self.prepare())
        self.assertEqual(list(self.pending.glob("*.eml")), [])
        self.assertEqual(list((self.root / "processing").glob("*.eml")), [])
        self.assertEqual(len(list((self.root / "processed").glob("*.eml"))), 3)
        for source in result["expected_sources"]:
            execution = source["execution_result"]
            self.assertEqual(execution["status"], "COMPLETED")
            self.assertEqual(execution["country"], source["country"])
            self.assertEqual(execution["summary"]["counts"]["raw_records"], 2)
            for key in ("run_directory", "worklist_path", "execution_summary_path"):
                self.assertTrue(self.assert_local(execution[key]).exists())
            context = read_json(
                self.assert_local(execution["run_directory"])
                / "execution_manifest.json"
            )
            self.assertEqual(context["execution_status"], "COMPLETED")
            self.assertTrue(self.assert_local(context["processing_path"]).is_file())
            self.assertEqual(
                read_json(self.root / "logs" / (execution["execution_id"] + ".json")),
                context,
            )
