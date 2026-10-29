"""The execution manager's test return path and durable artifacts."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from engine.execution_manager import (
    create_execution,
    ensure_directories,
    return_to_pending_after_test,
    update_execution,
)
from tests.support.fixture_paths import copy_fixture, fixture_path
from tests.support.weekly_cases import IsolatedWeeklyCase, read_json


class ExecutionLifecycleTest(IsolatedWeeklyCase):
    def test_return_to_pending(self) -> None:
        source = copy_fixture("weekly_Brazil_upcoming", self.pending / "Brazil.eml")
        content = source.read_bytes()
        directories = ensure_directories(self.config)
        context = create_execution(source, self.config, directories)
        self.assertFalse(source.exists())
        self.assertEqual(Path(context.processing_path).read_bytes(), content)
        self.assertEqual(context.execution_status, "STARTED")
        update_execution(context, "REPORT_DETECTION_TEST", "RUNNING")
        self.assertEqual(
            read_json(Path(context.run_directory) / "execution_manifest.json")[
                "current_stage"
            ],
            "REPORT_DETECTION_TEST",
        )
        returned = return_to_pending_after_test(context, directories)
        self.assertEqual(self.assert_local(returned), source)
        self.assertEqual(returned.read_bytes(), content)
        self.assertEqual(fixture_path("weekly_Brazil_upcoming").read_bytes(), content)
        self.assertEqual(list(directories["processing"].iterdir()), [])
        self.assertEqual(context.execution_status, "TEST_COMPLETED")

    def test_manifest_and_log_persist(self) -> None:
        source = copy_fixture("weekly_Brazil_upcoming", self.pending / "Brazil.eml")
        directories = ensure_directories(self.config)
        context = create_execution(source, self.config, directories)
        update_execution(
            context,
            "CONTROLLED_STAGE",
            "RUNNING",
            issue="Synthetic lifecycle observation",
        )
        return_to_pending_after_test(context, directories)
        manifest = self.assert_local(
            Path(context.run_directory) / "execution_manifest.json"
        )
        log = self.assert_local(directories["logs"] / (context.execution_id + ".json"))
        self.assertEqual(read_json(manifest), asdict(context))
        self.assertEqual(read_json(log), asdict(context))
        self.assertEqual(context.current_stage, "LIFECYCLE_TEST_COMPLETED")
        self.assertEqual(context.issues, ["Synthetic lifecycle observation"])
        self.assertEqual(context.processing_path, "")
        self.assertLessEqual(context.started_at, context.finished_at)
