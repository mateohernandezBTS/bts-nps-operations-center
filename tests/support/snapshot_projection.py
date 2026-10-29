"""Narrow runtime-token projection shared by JSON, CSV and workbook artifacts."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

TIMESTAMP_FIELDS = frozenset(
    {
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
        "generated_at",
        "processing_started_at",
        "processing_finished_at",
        "failed_at",
        "aggregated_at",
        "inventoried_at",
    }
)
PATH_FIELDS = frozenset(
    {
        "source_path",
        "original_path",
        "processing_path",
        "processed_path",
        "run_directory",
        "output_directory",
        "scanned_directory",
        "input_directory",
        "output_root",
        "expected_run_directory",
        "execution_summary_path",
        "worklist_path",
        "slack_ready_path",
        "business_review_path",
        "summary_path",
        "csv_path",
        "markdown_path",
        "manual_review_csv_path",
        "manifest_path",
        "selam_consolidated_worklist_path",
        "selam_consolidation_issues_path",
        "selam_manual_review_path",
        "selam_manual_review_issues_path",
        "excel",
        "slack_canvas",
        "csv",
        "manual_review",
        "summary",
        "manifest",
    }
)
ID_FIELDS = frozenset(
    {
        "execution_id",
        "Source Execution ID",
        "original_execution_id",
        "duplicate_execution_id",
    }
)
RUNTIME_TIME = "<RUNTIME_TIMESTAMP>"
EXECUTION_PATTERN = re.compile(r"\d{8}_\d{6}_[0-9a-f]{6}")


def json_text(value: Any) -> str:
    """Keep list order, nulls and missing keys distinct in stable UTF-8 JSON."""
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def read_csv(path: Path) -> dict[str, Any]:
    """Preserve header order even for empty outputs."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return {"headers": reader.fieldnames or [], "records": list(reader)}


class Projection:
    """Normalize only registered IDs, named timestamp fields and contained paths."""

    def __init__(self, root: Path, executions: dict[str, str]) -> None:
        self.root = root.resolve()
        self.executions = executions
        if len(set(executions.values())) != len(executions):
            raise AssertionError("Two execution IDs collapse to one token")
        for execution in executions:
            if not EXECUTION_PATTERN.fullmatch(execution):
                raise AssertionError(f"Invalid execution ID: {execution}")

    def path(self, value: str) -> str:
        """Relativize an absolute operational path after checking containment."""
        if not value:
            return value
        resolved = Path(value).resolve()
        if not Path(value).is_absolute() or not resolved.is_relative_to(self.root):
            raise AssertionError(f"Unregistered operational root: {value}")
        relative = resolved.relative_to(self.root).as_posix()
        parts = [self.executions.get(part, part) for part in relative.split("/")]
        return "<TEST_ROOT>" + ("/" + "/".join(parts) if relative != "." else "")

    def timestamp(self, value: str) -> str:
        """Validate a runtime ISO timestamp before replacing it."""
        if not value:
            return value
        if not re.fullmatch(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:[+-]\d\d:\d\d)?", value
        ):
            raise AssertionError(f"Invalid runtime timestamp: {value}")
        datetime.fromisoformat(value)
        return RUNTIME_TIME

    def diagnostic(self, value: str) -> str:
        """Keep only the final exception type and message, never traceback frames."""
        lines = value.rstrip().splitlines()
        final = lines[-1] if lines else ""
        if not re.fullmatch(r"[A-Za-z_][\w.]*:.*", final):
            raise AssertionError("Traceback must end with exception type and message")
        return final

    def value(self, value: Any, key: str = "") -> Any:
        """Walk without sorting arrays or dropping any field."""
        if isinstance(value, dict):
            for start, finish in (
                ("started_at", "finished_at"),
                ("created_at", "updated_at"),
                ("processing_started_at", "processing_finished_at"),
            ):
                if value.get(start) and value.get(finish):
                    a = datetime.fromisoformat(value[start]).replace(tzinfo=None)
                    b = datetime.fromisoformat(value[finish]).replace(tzinfo=None)
                    if a > b:
                        raise AssertionError(f"Reversed lifecycle: {start}/{finish}")
            return {k: self.value(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [self.value(v, key) for v in value]
        if not isinstance(value, str):
            return value
        if key in TIMESTAMP_FIELDS:
            return self.timestamp(value)
        if key in ID_FIELDS:
            if value not in self.executions:
                raise AssertionError(f"Unknown execution ID: {value}")
            return self.executions[value]
        if key in PATH_FIELDS:
            return self.path(value)
        if key == "traceback":
            return self.diagnostic(value)
        if key in {"project_url", "Project URL"}:
            return value
        if Path(value).is_absolute():
            raise AssertionError(
                f"Absolute path in non-allowlisted field {key}: {value}"
            )
        return value

    def workbook(self, path: Path) -> list[dict[str, Any]]:
        """Read formulas, hyperlinks and sheet structure; omit ZIP/doc metadata only."""
        workbook = load_workbook(path, data_only=False)
        try:
            sheets = []
            for sheet in workbook:
                cells = []
                for row in sheet:
                    for cell in row:
                        if cell.value is None and cell.hyperlink is None:
                            continue
                        key = ""
                        if (
                            sheet.title == "Manifest"
                            and cell.column == 2
                            and cell.row >= 4
                        ):
                            key = str(sheet.cell(cell.row, 1).value).rsplit(".", 1)[-1]
                        value = cell.value
                        if (
                            sheet.title == "Issues"
                            and cell.column == 2
                            and cell.row >= 4
                            and isinstance(value, str)
                        ):
                            value = json.dumps(
                                self.value(json.loads(value)), ensure_ascii=False
                            )
                        elif isinstance(value, str):
                            value = self.value(value, key)
                        target = cell.hyperlink.target if cell.hyperlink else None
                        cells.append(
                            {
                                "coordinate": cell.coordinate,
                                "value": value,
                                "type": cell.data_type,
                                "hyperlink": target,
                            }
                        )
                sheets.append(
                    {
                        "name": sheet.title,
                        "dimensions": sheet.calculate_dimension(),
                        "merged_ranges": [str(r) for r in sheet.merged_cells.ranges],
                        "freeze_panes": sheet.freeze_panes,
                        "cells": cells,
                    }
                )
            return sheets
        finally:
            workbook.close()
