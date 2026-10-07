from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engine.process_report import (
    process_report_file,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

FIXTURE_DIRECTORY = (
    PROJECT_ROOT
    / "tests"
    / "runtime"
    / "weekly_pipeline"
    / "processed"
)


def find_valid_fixture() -> Path:
    """
    Return one previously processed valid Upcoming EML.
    """
    fixtures = sorted(
        FIXTURE_DIRECTORY.glob("*.eml")
    )

    if not fixtures:
        raise FileNotFoundError(
            "No valid EML fixture was found in: "
            f"{FIXTURE_DIRECTORY}"
        )

    return fixtures[0]


class ProcessingErrorLifecycleTest(unittest.TestCase):
    """
    Validate the real filesystem lifecycle when report
    processing fails after the file enters processing.
    """

    def test_failed_report_is_moved_to_error(self) -> None:
        """
        A valid detected report fails during email parsing.

        The system must:
        - move the source file from pending to processing;
        - move it from processing to error;
        - preserve the failed EML;
        - create error_details.json;
        - mark the execution manifest as FAILED;
        - create a final execution log;
        - propagate the original exception.
        """
        valid_fixture = find_valid_fixture()

        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)

            pending_directory = root / "pending"
            processing_directory = root / "processing"
            processed_directory = root / "processed"
            error_directory = root / "error"
            runs_directory = root / "runs"
            logs_directory = root / "logs"

            pending_directory.mkdir(parents=True)

            source_path = (
                pending_directory
                / valid_fixture.name
            )

            shutil.copy2(
                valid_fixture,
                source_path,
            )

            test_config = {
                "version": "1.0",
                "environment": "TEST",
                "input_lifecycle": {
                    "pending_directory": str(
                        pending_directory
                    ),
                    "processing_directory": str(
                        processing_directory
                    ),
                    "processed_directory": str(
                        processed_directory
                    ),
                    "error_directory": str(
                        error_directory
                    ),
                },
                "output": {
                    "runs_directory": str(
                        runs_directory
                    ),
                },
                "logs": {
                    "directory": str(
                        logs_directory
                    ),
                },
                "retention": {
                    "enabled": False,
                    "processed_days": 30,
                    "error_days": 90,
                    "output_runs_days": 90,
                    "log_days": 90,
                    "dry_run": True,
                },
            }

            controlled_error = (
                "Controlled parser failure for lifecycle test."
            )

            with patch(
                "engine.process_report.parse_eml_report",
                side_effect=ValueError(
                    controlled_error
                ),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    controlled_error,
                ):
                    process_report_file(
                        source_path=source_path,
                        reference_monday="8/3/2026",
                        system_config_override=test_config,
                    )

            # Original pending file must no longer exist.
            self.assertFalse(
                source_path.exists()
            )

            # Processing must be empty after fail_execution.
            processing_files = list(
                processing_directory.glob("*.eml")
            )

            self.assertEqual(
                processing_files,
                [],
            )

            # Processed must remain empty.
            processed_files = list(
                processed_directory.glob("*.eml")
            )

            self.assertEqual(
                processed_files,
                [],
            )

            # Failed EML must be preserved in error.
            error_files = list(
                error_directory.glob("*.eml")
            )

            self.assertEqual(
                len(error_files),
                1,
            )

            self.assertEqual(
                error_files[0].name,
                valid_fixture.name,
            )

            # Exactly one execution directory must exist.
            run_directories = [
                path
                for path in runs_directory.iterdir()
                if path.is_dir()
            ]

            self.assertEqual(
                len(run_directories),
                1,
            )

            run_directory = run_directories[0]

            error_details_path = (
                run_directory
                / "error_details.json"
            )

            execution_manifest_path = (
                run_directory
                / "execution_manifest.json"
            )

            self.assertTrue(
                error_details_path.exists()
            )

            self.assertTrue(
                execution_manifest_path.exists()
            )

            error_details = json.loads(
                error_details_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                error_details["error"],
                controlled_error,
            )

            self.assertIn(
                "traceback",
                error_details,
            )

            self.assertIn(
                "failed_at",
                error_details,
            )

            manifest = json.loads(
                execution_manifest_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                manifest["execution_status"],
                "FAILED",
            )

            self.assertEqual(
                manifest["current_stage"],
                "ERROR",
            )

            self.assertIn(
                controlled_error,
                manifest["issues"],
            )

            self.assertEqual(
                Path(
                    manifest["processing_path"]
                ),
                error_files[0],
            )

            # One final log must also be created.
            log_files = list(
                logs_directory.glob("*.json")
            )

            self.assertEqual(
                len(log_files),
                1,
            )

            log_data = json.loads(
                log_files[0].read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                log_data["execution_status"],
                "FAILED",
            )

            self.assertEqual(
                log_data["current_stage"],
                "ERROR",
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2,
    )