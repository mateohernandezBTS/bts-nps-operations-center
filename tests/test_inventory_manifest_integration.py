"""Real inventory to manifest readiness and persistence."""

from __future__ import annotations

from engine.weekly_manifest import load_weekly_manifest
from tests.support.weekly_cases import IsolatedWeeklyCase, read_json


class InventoryManifestTest(IsolatedWeeklyCase):
    def test_ready_manifest(self) -> None:
        manifest = read_json(self.prepare())
        self.assertEqual(manifest["status"], "READY_TO_PROCESS")
        for source in manifest["expected_sources"]:
            self.assertEqual(source["status"], "RECEIVED")
            self.assertEqual(source["matched_files"], [source["matched_file"]])
        self.assertEqual(manifest["source_inventory"]["readiness_issues"], [])

    def test_blocked_manifest(self) -> None:
        manifest = read_json(self.prepare("missing_brazil"))
        self.assertEqual(manifest["status"], "WAITING_FOR_REPORTS")
        self.assertEqual(
            manifest["source_inventory"]["readiness_issues"],
            ["Missing required source: upcoming_brazil"],
        )
        source = manifest["expected_sources"][1]
        self.assertEqual(source["status"], "MISSING")
        self.assertIsNone(source["matched_file"])
        self.assertEqual(source["matched_files"], [])

    def test_persisted_round_trip(self) -> None:
        path = self.prepare()
        saved = load_weekly_manifest(path)
        self.assertEqual(saved, read_json(path))
        self.assertEqual(len(saved["inventory_items"]), 3)
        self.assertEqual(
            saved["source_inventory"]["scanned_directory"], str(self.pending)
        )
        self.assertEqual(saved["source_inventory"]["files_scanned"], 3)
        for item in saved["inventory_items"]:
            self.assertTrue(self.assert_local(item["source_path"]).is_file())

    def test_six_reports_three_out_of_scope(self) -> None:
        manifest = read_json(self.prepare("complete_six_reports"))
        inventory = manifest["source_inventory"]
        self.assertEqual(manifest["status"], "READY_TO_PROCESS")
        self.assertEqual(
            (
                inventory["files_scanned"],
                inventory["matched_files"],
                inventory["known_out_of_scope_files"],
            ),
            (6, 3, 3),
        )
        self.assertEqual(
            (inventory["unconfigured_files"], inventory["missing_required_sources"]),
            (0, 0),
        )
        self.assertEqual(inventory["readiness_issues"], [])
        self.assertEqual(
            [s["status"] for s in manifest["expected_sources"]], ["RECEIVED"] * 3
        )
