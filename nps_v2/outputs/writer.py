"""Writes every output of a run into its folder."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nps_v2.domain import SalesforceId
from nps_v2.outputs.preview import render_preview
from nps_v2.outputs.slack import slack_rows, write_slack_table
from nps_v2.pipeline import PipelineResult
from nps_v2.registry import CountryRegistry
from nps_v2.selection import Selection
from nps_v2.surveys.state import ProjectSurveys

REPORT_FILE = "report.json"
PREVIEW_FILE = "preview.md"
SLACK_DIRECTORY = "slack"


@dataclass(frozen=True, slots=True)
class WrittenOutputs:
    report: Path
    preview: Path
    slack_html: Path


def write_outputs(
    run_directory: Path,
    *,
    report: Mapping[str, Any],
    selection: Selection,
    registry: CountryRegistry,
    result: PipelineResult,
    surveys: Mapping[SalesforceId, ProjectSurveys],
) -> WrittenOutputs:
    run_directory.mkdir(parents=True, exist_ok=True)
    report_path = run_directory / REPORT_FILE
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    preview_path = run_directory / PREVIEW_FILE
    preview_path.write_text(render_preview(report), encoding="utf-8")

    run_id = str(report["run_id"])
    slack_html = write_slack_table(
        run_directory / SLACK_DIRECTORY,
        slack_rows(result.ready, surveys, registry, run_id),
        run_id=run_id,
        date_from=selection.date_from,
        date_to=selection.date_to,
        review_count=len(result.review) + len(result.worklist_review),
    )
    return WrittenOutputs(
        report=report_path, preview=preview_path, slack_html=slack_html
    )
