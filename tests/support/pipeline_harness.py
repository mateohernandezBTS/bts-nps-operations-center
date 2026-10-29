"""Real synthetic pipeline runs with isolated lifecycle and session collaborators."""

from __future__ import annotations

import io
import json
import re
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stdout
from dataclasses import asdict
from pathlib import Path
from typing import Any

from engine.application_controller import NPSApplicationController
from engine.process_report import process_report_file
from engine.session_manager import SessionManager
from engine.stages.business_rules import apply_business_rules
from engine.stages.email_parser import parse_eml_report
from engine.stages.normalize import normalize_records
from engine.stages.worklist import generate_worklist
from tests.support.fixture_generator import load_inputs
from tests.support.fixture_paths import copy_fixture, fixture_path
from tests.support.snapshot_projection import Projection, json_text, read_csv
from tests.support.weekly_cases import IsolatedWeeklyCase, read_json

WEEKLY_SCENARIOS = (
    "complete_weekly",
    "review_and_boundaries",
    "cross_source_duplicates",
    "partial_failure",
    "missing_argentina",
    "missing_brazil",
    "missing_mexico",
    "duplicate_source",
)
MALFORMED_SCENARIOS = tuple(
    spec["id"]
    for spec in load_inputs().catalog["fixtures"]
    if spec["family"] == "malformed"
)
SCENARIOS = (*WEEKLY_SCENARIOS, "parser_equivalence", *MALFORMED_SCENARIOS)
STAGE_JSON = (
    "raw",
    "normalized",
    "validation_issues",
    "classified",
    "worklist",
    "execution_summary",
    "report_context",
    "execution_manifest",
    "error_details",
)


@contextmanager
def isolated_case() -> Iterator[IsolatedWeeklyCase]:
    """Reuse the approved stdlib temporary-root and environment isolation seams."""
    case = IsolatedWeeklyCase()
    try:
        case.setUp()
        yield case
        case.tearDown()
    finally:
        case.doCleanups()


def validate_declarations(
    fixture_id: str,
    raw: list[dict[str, Any]],
    normalized: list[dict[str, Any]],
    classified: list[dict[str, Any]],
) -> None:
    """Check artifacts against literal catalog facts, independent of snapshots."""
    inputs = load_inputs()
    spec = next(s for s in inputs.catalog["fixtures"] if s["id"] == fixture_id)
    for row_id, source, norm, decision in zip(
        spec["rows"], raw, normalized, classified, strict=True
    ):
        declaration = inputs.rows["rows"][row_id]
        expected = declaration["expected"]
        # The parser removes HTML whitespace; named grouped-office variants override it.
        for field in ("client_name", "project_name"):
            if source[field] != " ".join(declaration["values"][field].split()):
                raise AssertionError((row_id, field, source[field]))
        for field in ("status", "ignore_reporting", "validation_status"):
            if norm[field] != expected[field]:
                raise AssertionError((row_id, field, norm[field], expected[field]))
        if norm["validation_issues"] != " | ".join(expected["validation_issues"]):
            raise AssertionError((row_id, "validation_issues"))
        if decision["decision"] != expected["decision"]:
            raise AssertionError((row_id, decision["decision"], expected["decision"]))
        if decision["decision_codes"].split(" | ") != expected["decision_codes"]:
            raise AssertionError((row_id, "decision_codes"))


def stage_artifacts(directory: Path, fixture_id: str) -> dict[str, Any]:
    """Read persisted stage artifacts without re-running production transformations."""
    data = {
        name: read_json(directory / (name + ".json"))
        for name in STAGE_JSON
        if (directory / (name + ".json")).is_file()
    }
    if "classified" in data:
        validate_declarations(
            fixture_id, data["raw"], data["normalized"], data["classified"]
        )
        data["classification_partitions"] = {
            name: [r for r in data["classified"] if r["decision"] == decision]
            for name, decision in (
                ("eligible", "ELIGIBLE"),
                ("excluded", "EXCLUDED"),
                ("review", "REVIEW"),
            )
        }
        data["worklist_review"] = [
            r for r in data["worklist"] if r["Output Status"] == "REVIEW"
        ]
    data["csv"] = {p.name: read_csv(p) for p in sorted(directory.glob("*.csv"))}
    if "raw" in data:
        for name in ("raw", "normalized", "classified", "worklist"):
            expected = [
                {k: "" if v is None else str(v) for k, v in row.items()}
                for row in data[name]
            ]
            if data["csv"][name + ".csv"]["records"] != expected:
                raise AssertionError(f"CSV/JSON mismatch: {fixture_id}/{name}")
        data["outside_window"] = data["csv"]["outside_weekly_window.csv"]["records"]
        for name, filename in (
            ("eligible", "eligible.csv"),
            ("excluded", "excluded.csv"),
            ("review", "business_review.csv"),
        ):
            expected = [
                {k: "" if v is None else str(v) for k, v in row.items()}
                for row in data["classification_partitions"][name]
            ]
            if data["csv"][filename]["records"] != expected:
                raise AssertionError(f"Partition CSV mismatch: {fixture_id}/{name}")
    if (directory / "slack_ready.md").is_file():
        data["slack_ready"] = (directory / "slack_ready.md").read_text(encoding="utf-8")
    return data


def collect_executions(case: IsolatedWeeklyCase) -> tuple[dict[str, Any], Projection]:
    """Associate each runtime ID with a catalog source and ordinal before projection."""
    specs = {Path(s["path"]).name: s for s in load_inputs().catalog["fixtures"]}
    artifacts: dict[str, Any] = {}
    identifiers: dict[str, str] = {}
    for directory in sorted((case.root / "runs").glob("*")):
        context = read_json(directory / "execution_manifest.json")
        spec = specs[context["source_file"]]
        token = "upcoming_" + spec["country"].lower() + "_1"
        if token in artifacts or context["execution_id"] != directory.name:
            raise AssertionError("Execution/source association is ambiguous")
        if Path(context["original_path"]).name != Path(spec["path"]).name:
            raise AssertionError("Execution source filename changed")
        case.assert_local(context["original_path"])
        case.assert_local(context["run_directory"])
        case.assert_local(context["processing_path"])
        if (
            Path(context["processing_path"]).read_bytes()
            != fixture_path(spec["id"]).read_bytes()
        ):
            raise AssertionError("Lifecycle changed source bytes")
        if read_json(case.root / "logs" / (directory.name + ".json")) != context:
            raise AssertionError("Execution log/manifest mismatch")
        identifiers[directory.name] = "<EXECUTION:" + token + ">"
        artifacts[token] = stage_artifacts(directory, spec["id"])
    return artifacts, Projection(case.root, identifiers)


def project_executions(
    artifacts: dict[str, Any], projection: Projection
) -> dict[str, str]:
    """Group each semantic surface by stable source, retaining source row order."""
    names = sorted({name for source in artifacts.values() for name in source})
    return {
        name + ".json": json_text(
            projection.value(
                {
                    source: values[name]
                    for source, values in artifacts.items()
                    if name in values
                }
            )
        )
        for name in names
    }


def weekly(case: IsolatedWeeklyCase, scenario: str) -> dict[str, str]:
    """Exercise real controller preflight, pipeline, aggregation and renderers."""
    case.populate(scenario)
    manager = SessionManager(session_file=case.root / "session.json")
    controller = NPSApplicationController(session_manager=manager)
    with redirect_stdout(io.StringIO()):
        result = controller.run_weekly_process("8/3/2026", test_mode=True)
    if result.status == "BLOCKED":
        # Preflight is read-only; persist an independently inventoried manifest.
        from engine.source_inventory import build_source_inventory
        from engine.weekly_manifest import update_weekly_manifest_from_inventory
        from engine.weekly_run import create_weekly_run

        _, path = create_weekly_run("8/3/2026", output_root=case.output)
        update_weekly_manifest_from_inventory(
            path, build_source_inventory(case.pending)
        )
    else:
        if not result.success:
            raise AssertionError(asdict(result))
        path = Path(result.data["processing"]["manifest_path"])
    artifacts, projection = collect_executions(case)
    manifest = read_json(case.assert_local(path))
    for source in manifest["expected_sources"]:
        execution = source.get("execution_result")
        if execution:
            token = projection.executions[execution["execution_id"]]
            expected_token = "<EXECUTION:" + source["source_id"] + "_1>"
            if token != expected_token:
                raise AssertionError("Manifest execution/source association changed")
    files = project_executions(artifacts, projection)
    manifest_name = (
        "test_inventory_manifest.json"
        if result.status == "BLOCKED"
        else "weekly_manifest.json"
    )
    files[manifest_name] = json_text(projection.value(manifest))
    files["preflight.json"] = json_text(projection.value(result.data["preflight"]))
    files["operation.json"] = json_text(
        {
            "success": result.success,
            "status": result.status,
            "issues": result.issues,
        }
    )
    weekly_json = {
        "selam_consolidated": "selam_consolidated_worklist",
        "selam_manual_review": "selam_manual_review",
        "consolidation_issues": "selam_consolidation_issues",
        "manual_review_issues": "selam_manual_review_issues",
        "summary": "selam_weekly_summary",
    }
    for name, filename in weekly_json.items():
        target = path.parent / (filename + ".json")
        if target.is_file():
            files[name + ".json"] = json_text(projection.value(read_json(target)))
    if result.status != "BLOCKED":
        processing = result.data["processing"]
        files["excel_cells.json"] = json_text(
            projection.workbook(case.assert_local(processing["weekly_excel_path"]))
        )
        files["slack.html"] = case.assert_local(
            processing["slack_canvas_path"]
        ).read_text(encoding="utf-8")
        files["slack_ready.md"] = case.assert_local(
            processing["markdown_path"]
        ).read_text(encoding="utf-8")
        files["weekly_csv.json"] = json_text(
            projection.value(
                {p.name: read_csv(p) for p in sorted(path.parent.glob("*.csv"))}
            )
        )
        validate_weekly_outputs(files)
    for name, text in files.items():
        if any(execution in text for execution in projection.executions):
            raise AssertionError(f"Unprojected execution ID in {name}")
    return files


def validate_weekly_outputs(files: dict[str, str]) -> None:
    """Compare CSV rows to consolidated JSON and every exported workbook field."""
    csvs = json.loads(files["weekly_csv.json"])
    if csvs["selam_worklist.csv"]["records"] != json.loads(
        files["selam_consolidated.json"]
    ):
        raise AssertionError("Weekly CSV/consolidated JSON mismatch")
    workbook = json.loads(files["excel_cells.json"])
    for sheet, filename in (
        (workbook[1], "selam_worklist.csv"),
        (workbook[2], "selam_manual_review.csv"),
    ):
        cells = {cell["coordinate"]: cell for cell in sheet["cells"]}
        headers = {
            cell["coordinate"][:-1]: cell["value"]
            for cell in sheet["cells"]
            if re.fullmatch(r"[A-Z]+3", cell["coordinate"])
        }
        for index, row in enumerate(csvs[filename]["records"], 4):
            for column, field in headers.items():
                cell = cells.get(f"{column}{index}")
                value = row.get(field, "")
                if not value:
                    if cell is not None and cell["value"] not in (None, ""):
                        raise AssertionError((sheet["name"], index, field, "empty"))
                elif cell is None or value != (cell["hyperlink"] or str(cell["value"])):
                    raise AssertionError((sheet["name"], index, field, value))


def parser_equivalence() -> dict[str, str]:
    """Project every parser variant through pure stages with literal row checks."""
    artifacts = {}
    for spec in load_inputs().catalog["fixtures"]:
        if spec["family"] != "parser":
            continue
        raw = parse_eml_report(fixture_path(spec["id"]))
        normalized, issues = normalize_records(raw)
        classified = apply_business_rules(normalized)
        validate_declarations(spec["id"], raw, normalized, classified["classified"])
        worklist = generate_worklist(
            classified["eligible"], reference_monday="8/3/2026"
        )
        artifacts[spec["id"]] = {
            "raw": raw,
            "normalized": normalized,
            "validation_issues": issues,
            "classified": classified["classified"],
            "classification_partitions": {
                k: classified[k] for k in ("eligible", "excluded", "review")
            },
            "worklist": worklist["worklist"],
            "worklist_review": worklist["review"],
            "outside_window": worklist["outside_window"],
        }
    names = next(iter(artifacts.values())).keys()
    return {
        name + ".json": json_text({k: v[name] for k, v in artifacts.items()})
        for name in names
    }


def run_scenario(scenario: str) -> dict[str, str]:
    """Return candidate bytes in memory; ordinary runs never write expectations."""
    if scenario == "parser_equivalence":
        return parser_equivalence()
    with isolated_case() as case:
        if scenario in WEEKLY_SCENARIOS:
            result = weekly(case, scenario)
        elif scenario in MALFORMED_SCENARIOS:
            source = copy_fixture(scenario, case.pending / fixture_path(scenario).name)
            spec = next(
                s for s in load_inputs().catalog["fixtures"] if s["id"] == scenario
            )
            with (
                redirect_stdout(io.StringIO()),
                case.assertRaisesRegex(ValueError, spec["expected_parse_error"]),
            ):
                process_report_file(source, "8/3/2026", case.config)
            artifacts, projection = collect_executions(case)
            result = project_executions(artifacts, projection)
            if len(list((case.root / "error").glob("*.eml"))) != 1:
                raise AssertionError("Failed input did not enter error lifecycle")
        else:
            raise ValueError(scenario)
        return {name: text.replace("\r\n", "\n") for name, text in result.items()}
