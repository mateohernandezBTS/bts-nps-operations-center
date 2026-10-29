"""Synthetic complete, missing, duplicate and detection inventories."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

from engine.report_detection import detect_report, load_detection_config
from engine.source_inventory import build_source_inventory
from tests.support.weekly_cases import IsolatedWeeklyCase


class SourceInventoryTest(IsolatedWeeklyCase):
    def test_complete(self) -> None:
        inventory = self.inventory("complete_weekly")
        self.assertEqual(
            (
                inventory.files_scanned,
                inventory.matched_files,
                inventory.configured_sources,
            ),
            (3, 3, 3),
        )
        self.assertEqual(
            (
                inventory.missing_required_sources,
                inventory.duplicate_sources,
                inventory.review_files,
                inventory.unconfigured_files,
            ),
            (0, 0, 0, 0),
        )
        self.assertEqual([s.status for s in inventory.sources], ["RECEIVED"] * 3)
        self.assertEqual(
            [s.country for s in inventory.sources], ["Argentina", "Brazil", "Mexico"]
        )
        for item in inventory.items:
            self.assert_local(item.source_path)
            self.assertEqual(item.inventory_status, "MATCHED")

    def test_missing_sources(self) -> None:
        for country in ("argentina", "brazil", "mexico"):
            with self.subTest(country=country):
                inventory = self.inventory("missing_" + country, self.root / country)
                self.assertEqual(
                    (inventory.matched_files, inventory.missing_required_sources),
                    (2, 1),
                )
                missing = [s for s in inventory.sources if s.status == "MISSING"]
                self.assertEqual(
                    [s.source_id for s in missing], ["upcoming_" + country]
                )
                self.assertEqual(missing[0].matched_files, [])

    def test_duplicate_source(self) -> None:
        inventory = self.inventory("duplicate_source")
        self.assertEqual(
            (
                inventory.files_scanned,
                inventory.matched_files,
                inventory.duplicate_sources,
            ),
            (4, 4, 1),
        )
        duplicates = [s for s in inventory.sources if s.status == "DUPLICATE"]
        self.assertEqual([s.source_id for s in duplicates], ["upcoming_mexico"])
        self.assertEqual(len(duplicates[0].matched_files), 2)

    def test_unknown_and_out_of_scope(self) -> None:
        for bundle, count in (
            ("unknown_report", 1),
            ("unconfigured_source", 1),
            ("complete_six_reports", 0),
        ):
            with self.subTest(bundle=bundle):
                inventory = self.inventory(bundle, self.root / bundle)
                self.assertEqual(inventory.review_files, count)
                self.assertEqual(inventory.unconfigured_files, 0)
                self.assertEqual(
                    inventory.known_out_of_scope_files, 3 if not count else 0
                )
                self.assertEqual(
                    inventory.matched_files
                    + inventory.known_out_of_scope_files
                    + inventory.review_files
                    + inventory.unconfigured_files,
                    inventory.files_scanned,
                )
        directory = self.root / "unconfigured_source"
        path = next(directory.glob("*.eml"))
        # Stock Chile detection is REVIEW; inject only detector attribution to
        # exercise the existing unconfigured-source inventory branch.
        detected = replace(
            detect_report(path, load_detection_config()),
            country="Chile",
            report_type="Upcoming",
            detection_status="DETECTED",
            detection_issues=[],
        )
        with patch(
            "engine.source_inventory.detect_pending_reports", return_value=[detected]
        ):
            inventory = build_source_inventory(directory, "weekly_upcoming")
        self.assertEqual(inventory.unconfigured_files, 1)
        self.assertEqual(inventory.review_files, 0)
