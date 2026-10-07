from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from engine.application_controller import (
    NPSApplicationController,
)
from engine.weekly_preflight import (
    build_weekly_run_id,
    calculate_weekly_window,
    parse_reference_date,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

FIXTURE_DIRECTORY = (
    PROJECT_ROOT
    / "tests"
    / "runtime"
    / "weekly_pipeline"
    / "processed"
)


def find_report_fixture(country: str) -> Path:
    """
    Locate a previously processed EML fixture by country.
    """
    country_key = country.casefold()

    matches = [
        path
        for path in FIXTURE_DIRECTORY.glob("*.eml")
        if country_key in path.name.casefold()
    ]

    if not matches:
        raise FileNotFoundError(
            f"No processed fixture found for {country}: "
            f"{FIXTURE_DIRECTORY}"
        )

    return sorted(matches)[0]


def copy_fixture(
    country: str,
    destination: Path,
    *,
    filename: str | None = None,
) -> Path:
    """
    Copy one known EML fixture into an isolated test folder.
    """
    source = find_report_fixture(country)

    target = destination / (
        filename
        if filename is not None
        else source.name
    )

    shutil.copy2(
        source,
        target,
    )

    return target


class BackendBlockingScenariosTest(unittest.TestCase):
    """
    Validate that unsafe weekly runs are blocked before
    processing begins.
    """

    def setUp(self) -> None:
        self.controller = NPSApplicationController()

    def run_isolated_preflight(
        self,
        input_directory: Path,
        output_directory: Path,
        *,
        reference_date: str = "8/3/2026",
    ):
        """
        Execute the controller against isolated directories.
        """
        with (
            patch(
                "engine.weekly_preflight.TEST_INPUT",
                input_directory,
            ),
            patch(
                "engine.weekly_preflight.TEST_OUTPUT",
                output_directory,
            ),
        ):
            return self.controller.run_preflight(
                reference_date=reference_date,
                test_mode=True,
            )

    def test_invalid_reference_date_is_blocked(self) -> None:
        """
        A reference date that is not Monday must fail.
        """
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            input_directory = root / "input"
            output_directory = root / "output"

            input_directory.mkdir()
            output_directory.mkdir()

            result = self.run_isolated_preflight(
                input_directory,
                output_directory,
                reference_date="8/4/2026",
            )

        self.assertFalse(result.success)
        self.assertEqual(
            result.status,
            "FAILED",
        )
        self.assertTrue(
            any(
                "must be a Monday" in issue
                for issue in result.issues
            )
        )

    def test_missing_input_directory_is_blocked(self) -> None:
        """
        A missing input directory must fail safely.
        """
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            input_directory = root / "does_not_exist"
            output_directory = root / "output"

            output_directory.mkdir()

            result = self.run_isolated_preflight(
                input_directory,
                output_directory,
            )

        self.assertFalse(result.success)
        self.assertEqual(
            result.status,
            "FAILED",
        )
        self.assertTrue(
            any(
                "Input directory does not exist" in issue
                for issue in result.issues
            )
        )

    def test_missing_argentina_is_blocked(self) -> None:
        """
        Brazil and Mexico are present, but Argentina is missing.
        """
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            input_directory = root / "input"
            output_directory = root / "output"

            input_directory.mkdir()
            output_directory.mkdir()

            copy_fixture(
                "Brazil",
                input_directory,
            )
            copy_fixture(
                "Mexico",
                input_directory,
            )

            result = self.run_isolated_preflight(
                input_directory,
                output_directory,
            )

        self.assertFalse(result.success)
        self.assertEqual(
            result.status,
            "BLOCKED",
        )
        self.assertTrue(
            any(
                "Missing required source: Argentina upcoming"
                in issue
                for issue in result.issues
            )
        )

    def test_missing_brazil_is_blocked(self) -> None:
        """
        Argentina and Mexico are present, but Brazil is missing.
        """
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            input_directory = root / "input"
            output_directory = root / "output"

            input_directory.mkdir()
            output_directory.mkdir()

            copy_fixture(
                "Argentina",
                input_directory,
            )
            copy_fixture(
                "Mexico",
                input_directory,
            )

            result = self.run_isolated_preflight(
                input_directory,
                output_directory,
            )

        self.assertFalse(result.success)
        self.assertEqual(
            result.status,
            "BLOCKED",
        )
        self.assertTrue(
            any(
                "Missing required source: Brazil upcoming"
                in issue
                for issue in result.issues
            )
        )

    def test_missing_mexico_is_blocked(self) -> None:
        """
        Argentina and Brazil are present, but Mexico is missing.
        """
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            input_directory = root / "input"
            output_directory = root / "output"

            input_directory.mkdir()
            output_directory.mkdir()

            copy_fixture(
                "Argentina",
                input_directory,
            )
            copy_fixture(
                "Brazil",
                input_directory,
            )

            result = self.run_isolated_preflight(
                input_directory,
                output_directory,
            )

        self.assertFalse(result.success)
        self.assertEqual(
            result.status,
            "BLOCKED",
        )
        self.assertTrue(
            any(
                "Missing required source: Mexico upcoming"
                in issue
                for issue in result.issues
            )
        )

    def test_duplicate_source_is_blocked(self) -> None:
        """
        Two Mexico reports must be treated as a duplicate source.
        """
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            input_directory = root / "input"
            output_directory = root / "output"

            input_directory.mkdir()
            output_directory.mkdir()

            copy_fixture(
                "Argentina",
                input_directory,
            )
            copy_fixture(
                "Brazil",
                input_directory,
            )
            copy_fixture(
                "Mexico",
                input_directory,
            )
            copy_fixture(
                "Mexico",
                input_directory,
                filename="DUPLICATE_Mexico.eml",
            )

            result = self.run_isolated_preflight(
                input_directory,
                output_directory,
            )

        self.assertFalse(result.success)
        self.assertEqual(
            result.status,
            "BLOCKED",
        )
        self.assertTrue(
            any(
                "Duplicate source: Mexico upcoming"
                in issue
                for issue in result.issues
            )
        )

    def test_existing_weekly_run_is_blocked(self) -> None:
        """
        An existing weekly output folder must prevent overwrite.
        """
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            input_directory = root / "input"
            output_directory = root / "output"

            input_directory.mkdir()
            output_directory.mkdir()

            copy_fixture(
                "Argentina",
                input_directory,
            )
            copy_fixture(
                "Brazil",
                input_directory,
            )
            copy_fixture(
                "Mexico",
                input_directory,
            )

            reference_date = parse_reference_date(
                "8/3/2026"
            )
            window_start, window_end = (
                calculate_weekly_window(
                    reference_date
                )
            )
            weekly_run_id = build_weekly_run_id(
                window_start,
                window_end,
            )

            (
                output_directory
                / weekly_run_id
            ).mkdir()

            result = self.run_isolated_preflight(
                input_directory,
                output_directory,
            )

        self.assertFalse(result.success)
        self.assertEqual(
            result.status,
            "BLOCKED",
        )
        self.assertTrue(
            any(
                "A weekly run already exists" in issue
                for issue in result.issues
            )
        )

    def test_unknown_report_is_blocked(self) -> None:
        """
        A detected report that is not configured in any
        enabled source group must block the weekly run.
        """
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            input_directory = root / "input"
            output_directory = root / "output"

            input_directory.mkdir()
            output_directory.mkdir()

            detected_contexts = [
                SimpleNamespace(
                    source_file="Argentina.eml",
                    source_path=str(
                        input_directory / "Argentina.eml"
                    ),
                    subject=(
                        "Report results "
                        "(Argentina Upcoming Deliveries/NPS)"
                    ),
                    sender_email="test@example.com",
                    received_at="2026-08-03T09:00:00",
                    country="Argentina",
                    report_type="upcoming",
                    detection_status="DETECTED",
                    detection_issues=[],
                ),
                SimpleNamespace(
                    source_file="Brazil.eml",
                    source_path=str(
                        input_directory / "Brazil.eml"
                    ),
                    subject=(
                        "Report results "
                        "(Brazil Upcoming Deliveries/NPS)"
                    ),
                    sender_email="test@example.com",
                    received_at="2026-08-03T09:01:00",
                    country="Brazil",
                    report_type="upcoming",
                    detection_status="DETECTED",
                    detection_issues=[],
                ),
                SimpleNamespace(
                    source_file="Mexico.eml",
                    source_path=str(
                        input_directory / "Mexico.eml"
                    ),
                    subject=(
                        "Report results "
                        "(Mexico Upcoming Deliveries/NPS)"
                    ),
                    sender_email="test@example.com",
                    received_at="2026-08-03T09:02:00",
                    country="Mexico",
                    report_type="upcoming",
                    detection_status="DETECTED",
                    detection_issues=[],
                ),
                SimpleNamespace(
                    source_file="Chile.eml",
                    source_path=str(
                        input_directory / "Chile.eml"
                    ),
                    subject=(
                        "Report results "
                        "(Chile Upcoming Deliveries/NPS)"
                    ),
                    sender_email="test@example.com",
                    received_at="2026-08-03T09:03:00",
                    country="Chile",
                    report_type="upcoming",
                    detection_status="DETECTED",
                    detection_issues=[],
                ),
            ]

            with patch(
                "engine.source_inventory."
                "detect_pending_reports",
                return_value=detected_contexts,
            ):
                result = self.run_isolated_preflight(
                    input_directory,
                    output_directory,
                )

        self.assertFalse(result.success)
        self.assertEqual(
            result.status,
            "BLOCKED",
        )

        self.assertTrue(
            any(
                (
                    "Unknown or unconfigured reports "
                    "detected: 1"
                ) in issue
                for issue in result.issues
            )
        )

        inventory = result.data.get(
            "inventory",
            {},
        )

        self.assertEqual(
            inventory.get(
                "unconfigured_files"
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2,
    )