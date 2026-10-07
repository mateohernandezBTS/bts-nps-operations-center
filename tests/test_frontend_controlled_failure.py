from __future__ import annotations

import sys
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from app.main_window import ApplicationShell
from engine.process_weekly_run import WeeklyEndToEndError


def main() -> int:
    application = QApplication(sys.argv)

    fake_preflight = {
        "environment": "TEST",
        "reference_date": "8/10/2026",
        "window_start": "8/11/2026",
        "window_end": "8/17/2026",
        "weekly_run_id": (
            "NPS_WEEK_2026-08-11_2026-08-17"
        ),
        "source_group": "weekly_upcoming",
        "input_directory": "temporary/input",
        "output_root": "temporary/output",
        "expected_run_directory": (
            "temporary/output/"
            "NPS_WEEK_2026-08-11_2026-08-17"
        ),
        "allow_partial_run": False,
        "status": "READY_TO_PROCESS",
        "issues": [],
        "inventory": {
            "files_scanned": 3,
            "matched_files": 3,
            "known_out_of_scope_files": 0,
            "review_files": 0,
            "unconfigured_files": 0,
            "duplicate_sources": 0,
            "missing_required_sources": 0,
            "sources": [],
            "items": [],
        },
    }

    with (
        patch(
            "engine.application_controller."
            "run_weekly_preflight",
            return_value=fake_preflight,
        ),
        patch(
            "engine.application_controller."
            "execute_weekly_end_to_end",
            side_effect=WeeklyEndToEndError(
                "Controlled weekly processing failure."
            ),
        ),
    ):
        window = ApplicationShell()
        window.show()

        return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())