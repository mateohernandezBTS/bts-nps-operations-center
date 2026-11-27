"""Command line used by the skill. Three steps, each printing JSON for Claude.

1. ``select``   — writes the selection and prints the project queries to run.
   ``capture``     — after running queries, saves their responses from the session
                  transcript, so Claude never re-types connector output.
2. ``surveys``  — reads and verifies the saved project responses, prints the
                  survey-set queries for exactly those projects.
3. ``upcoming`` — reads and verifies everything, runs the certified pipeline and
                  writes report.json, preview.md and the Slack table.

Every failure prints ``{"status": "error", ...}`` and exits with code 2; Claude must
stop and show the message, never work around it.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nps_v2.compare import CompareError
from nps_v2.creation.execution import ExecutionError
from nps_v2.creation.plan import PlanError
from nps_v2.creation.recipe import RecipeError
from nps_v2.creation.responses import ResponseError
from nps_v2.domain import ProjectSnapshot
from nps_v2.pipeline import PipelineError, load_report_scope, run_pipeline
from nps_v2.reasons import ReasonTextsError, load_reason_texts
from nps_v2.registry import CountryRegistry, RegistryError, load_registry
from nps_v2.report import RunContext, build_report
from nps_v2.run_folder import RunFolder, RunFolderError
from nps_v2.salesforce.control import (
    build_project_control_query,
    build_survey_set_control_queries,
    verify_projects,
    verify_survey_sets,
)
from nps_v2.salesforce.queries import (
    Query,
    build_projects_query,
    build_survey_set_queries,
)
from nps_v2.salesforce.readers import ReaderError, read_projects, read_survey_sets
from nps_v2.selection import (
    SearchFilters,
    Selection,
    SelectionError,
    day_selection,
    range_selection,
    standard_week_selection,
    today_in_buenos_aires,
)
from nps_v2.surveys.state import SurveyStateError, derive_survey_states
from nps_v2.watchlist import WatchlistError, load_watchlist

if TYPE_CHECKING:
    from nps_v2.outputs.writer import WrittenOutputs

EXIT_ERROR = 2
KNOWN_ERRORS = (
    CompareError,
    ExecutionError,
    PlanError,
    RecipeError,
    ResponseError,
    PipelineError,
    ReaderError,
    ReasonTextsError,
    RegistryError,
    RunFolderError,
    SelectionError,
    SurveyStateError,
    WatchlistError,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = args.handler(args)
    except KNOWN_ERRORS as error:
        _print(
            {"status": "error", "error": type(error).__name__, "message": str(error)}
        )
        return EXIT_ERROR
    _print({"status": "ok", **payload})
    return 0


# --- commands ----------------------------------------------------------------------


def command_select(args: argparse.Namespace) -> dict[str, Any]:
    registry = load_registry()
    selection = _selection(args)
    for code in selection.country_codes:
        registry.by_code(code)
    folder = RunFolder(Path(args.run))
    queries = [
        build_projects_query(selection, registry),
        build_project_control_query(selection, registry),
    ]
    folder.write_selection(selection)
    folder.write_queries("projects", queries)
    return {
        "step": "select",
        "selection": selection.to_dict(),
        "next": "Run each query and save its full JSON response, then run 'surveys'.",
        "queries": _query_list(folder, queries),
    }


def command_surveys(args: argparse.Namespace) -> dict[str, Any]:
    folder = RunFolder(Path(args.run))
    projects = _verified_projects(folder)
    queries = _survey_set_queries(projects)
    folder.write_queries("survey_sets", queries)
    return {
        "step": "surveys",
        "projects": len(projects),
        "next": (
            "Run each query and save its full JSON response, then run 'upcoming'."
            if queries
            else "No projects in the selection: run 'upcoming' directly."
        ),
        "queries": _query_list(folder, queries),
    }


def command_upcoming(args: argparse.Namespace) -> dict[str, Any]:
    folder = RunFolder(Path(args.run))
    registry = load_registry()
    selection = folder.read_selection()
    projects = _verified_projects(folder)

    queries = folder.read_queries("survey_sets")
    expected = _survey_set_queries(projects)
    if [q.soql for q in queries] != [q.soql for q in expected]:
        raise RunFolderError(
            "Survey-set queries do not match the saved projects; run 'surveys' again"
        )
    report, outputs = build_run_outputs(
        folder,
        projects=projects,
        survey_set_queries=queries,
        target=folder.path,
        context=RunContext(
            run_id=args.run_id or folder.path.name,
            generated_at=args.generated_at or _now(),
        ),
        watchlist_path=Path(args.watchlist) if args.watchlist else None,
        registry=registry,
        selection=selection,
    )
    return {
        "step": "upcoming",
        "summary": report["summary"],
        "watchlist_configured": report["watchlist_configured"],
        "outputs": {
            "report": str(outputs.report),
            "preview": str(outputs.preview),
            "preview_html": str(outputs.preview_html),
            "slack_html": str(outputs.slack_html),
        },
    }


def command_capture(args: argparse.Namespace) -> dict[str, Any]:
    from nps_v2.capture import capture, default_transcript

    folder = RunFolder(Path(args.run))
    transcript = Path(args.transcript) if args.transcript else default_transcript()
    result = capture(folder, args.group, transcript)
    return {
        "step": "capture",
        "group": args.group,
        "captured": list(result.captured),
        "already_saved": list(result.already_saved),
        "missing": list(result.missing),
        "next": (
            "Missing responses must be saved by hand before continuing."
            if result.missing
            else "All responses saved."
        ),
    }


# --- V2-2: create surveys ---------------------------------------------------------


def command_plan(args: argparse.Namespace) -> dict[str, Any]:
    from nps_v2.creation.workflow import CreationFolder, make_plan
    from nps_v2.outputs.creation_pages import render_plan_page

    folder = CreationFolder(RunFolder(Path(args.run)))
    plan = make_plan(folder, args.exclude, args.only)
    page = _write_plan_page(folder, plan, render_plan_page)
    return {
        "step": "plan",
        "surveys_to_create": len(plan.commands),
        "sessions": len({c.project_id for c in plan.commands}),
        "approval_code": plan.short_hash,
        "outputs": {"plan_html": str(page)},
        "next": (
            "Deliver plan_html to the user as a file. Ask the user to approve by "
            "replying with the approval code; then run 'approve --code <code>'."
            if plan.commands
            else "Nothing to create: tell the user and stop."
        ),
    }


def command_approve(args: argparse.Namespace) -> dict[str, Any]:
    from nps_v2.creation.workflow import CreationFolder, approve, now_iso

    folder = CreationFolder(RunFolder(Path(args.run)))
    queries = approve(folder, args.code, now_iso())
    return {
        "step": "approve",
        "approved": folder.read_plan().short_hash,
        "next": (
            "Run the re-check query, then 'capture --group creation_recheck', "
            "then 'execute'."
        ),
        "queries": _query_list(folder.run, queries),
    }


def command_execute(args: argparse.Namespace) -> dict[str, Any]:
    from nps_v2.creation.recipe import load_creation_config
    from nps_v2.creation.workflow import CreationFolder, execute
    from nps_v2.outputs.creation_pages import render_plan_page

    folder = CreationFolder(RunFolder(Path(args.run)))
    outcome = execute(folder, load_creation_config(), load_registry())
    if outcome.changed_plan is not None:
        page = _write_plan_page(folder, outcome.changed_plan, render_plan_page)
        return {
            "step": "execute",
            "plan_changed": True,
            "approval_code": outcome.changed_plan.short_hash,
            "surveys_to_create": len(outcome.changed_plan.commands),
            "outputs": {"plan_html": str(page)},
            "next": (
                "Some planned surveys now exist in Salesforce, so the plan changed and "
                "nothing was written. Deliver the new plan_html and ask for approval "
                "of the new code."
            ),
        }
    return _execution_payload("execute", outcome)


def command_record(args: argparse.Namespace) -> dict[str, Any]:
    from nps_v2.capture import default_transcript
    from nps_v2.creation.recipe import load_creation_config
    from nps_v2.creation.workflow import CreationFolder, now_iso, record

    folder = CreationFolder(RunFolder(Path(args.run)))
    response = (
        Path(args.response_file).read_text(encoding="utf-8")
        if args.response_file
        else None
    )
    transcript = None
    if response is None:
        transcript = Path(args.transcript) if args.transcript else default_transcript()
    outcome = record(
        folder,
        load_creation_config(),
        load_registry(),
        transcript=transcript,
        response_text=response,
        recorded_at=now_iso(),
    )
    return _execution_payload("record", outcome)


def command_reconcile(args: argparse.Namespace) -> dict[str, Any]:
    from nps_v2.creation.outputs import write_creation_outputs
    from nps_v2.creation.reconcile import (
        AFTER_GROUP,
        POINTER_QUERY,
        after_queries,
        counts,
        project_pointers,
        reconcile,
    )
    from nps_v2.creation.workflow import CreationFolder

    run = RunFolder(Path(args.run))
    folder = CreationFolder(run)
    plan = folder.read_plan()
    state = folder.read_state()
    projects = _verified_projects(run)
    queries = after_queries(projects, plan)
    missing = [q for q in queries if not run.response_path(q).exists()]
    if missing:
        run.write_queries(AFTER_GROUP, queries)
        return {
            "step": "reconcile",
            "next": (
                "Run each query, then 'capture --group creation_after', then "
                "'reconcile' again."
            ),
            "queries": _query_list(run, missing),
        }
    registry = load_registry()
    survey_queries = [q for q in queries if q.name != POINTER_QUERY]
    report, outputs = build_run_outputs(
        run,
        projects=projects,
        survey_set_queries=survey_queries,
        target=folder.path / "after",
        context=RunContext(run_id=f"{plan.run_id}-after", generated_at=_now()),
        watchlist_path=None,
        registry=registry,
        selection=run.read_selection(),
    )
    data = [
        (q, run.read_response(q))
        for q in survey_queries
        if not q.name.endswith("_control")
    ]
    pointer = next((q for q in queries if q.name == POINTER_QUERY), None)
    try:
        pointers = project_pointers(run.read_response(pointer)) if pointer else {}
    except (ValueError, KeyError) as error:
        raise RunFolderError(f"Invalid project read-back: {error}") from error
    outcomes = reconcile(plan, state, read_survey_sets(data), pointers)
    approval = (
        json.loads((folder.path / "approval.json").read_text(encoding="utf-8"))
        if (folder.path / "approval.json").exists()
        else {}
    )
    files = write_creation_outputs(
        folder.path,
        outcomes=outcomes,
        plan=plan,
        state=state,
        approved_at=str(approval.get("approved_at", "")),
        reconciled_at=_now(),
        country_names={c.code: c.name for c in registry.countries},
    )
    return {
        "step": "reconcile",
        "run_status": state.status,
        "run_error": state.error,
        "operator": state.operator_name or state.operator_id,
        "counts": counts(outcomes),
        "surveys": [o.to_dict() for o in outcomes],
        "outputs": {
            "result_html": str(files.result_page),
            "creation_log": str(files.log),
            "audit": str(files.audit),
            "slack_html": str(outputs.slack_html),
            "preview": str(outputs.preview),
            "preview_html": str(outputs.preview_html),
        },
        "summary_after": report["summary"],
    }


def _write_plan_page(folder: Any, plan: Any, render: Any) -> Path:
    registry = load_registry()
    page = folder.path / "plan.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        render(
            plan,
            country_names={c.code: c.name for c in registry.countries},
            generated_at=_now(),
        ),
        encoding="utf-8",
    )
    return Path(page)


def _execution_payload(step: str, outcome: Any) -> dict[str, Any]:
    state = outcome.state
    progress = {
        "run_status": state.status,
        "steps_done": state.cursor,
        "steps_total": len(state.steps),
        "error": state.error,
    }
    if outcome.call is not None:
        return {
            "step": step,
            **progress,
            "call": outcome.call.to_dict(),
            "next": (
                f"Run '{outcome.call.tool}' with exactly this input (do not change "
                "anything), then run 'record'. Never run a call twice."
            ),
        }
    return {
        "step": step,
        **progress,
        "next": (
            "The run stopped. Do NOT retry or write anything else: run 'reconcile' "
            "and show the user what happened."
            if state.error
            else "All steps done. Run 'reconcile' to verify and build the outputs."
        ),
    }


def command_compare(args: argparse.Namespace) -> dict[str, Any]:
    from nps_v2.compare import compare, read_desktop_ready, render_comparison
    from nps_v2.outputs.review_pages import render_compare_page

    folder = RunFolder(Path(args.run))
    report_path = folder.path / "report.json"
    if not report_path.exists():
        raise RunFolderError("Missing report.json: run 'upcoming' first")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    desktop = Path(args.desktop)
    comparison = compare(report, read_desktop_ready(desktop))
    (folder.path / "compare.json").write_text(
        json.dumps(comparison.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = folder.path / "compare.md"
    markdown.write_text(
        render_comparison(
            comparison, run_id=str(report["run_id"]), desktop_name=desktop.name
        ),
        encoding="utf-8",
    )
    page = folder.path / "compare.html"
    page.write_text(
        render_compare_page(
            comparison,
            run_id=str(report["run_id"]),
            desktop_name=desktop.name,
            generated_at=_now(),
        ),
        encoding="utf-8",
    )
    return {
        "step": "compare",
        "matching": comparison.matching,
        "only_desktop": len(comparison.only_desktop),
        "only_v2": len(comparison.only_v2),
        "to_review": comparison.unexplained,
        "outputs": {"compare": str(markdown), "compare_html": str(page)},
    }


# --- helpers -----------------------------------------------------------------------


def build_run_outputs(
    folder: RunFolder,
    *,
    projects: Sequence[ProjectSnapshot],
    survey_set_queries: Sequence[Query],
    target: Path,
    context: RunContext,
    watchlist_path: Path | None,
    registry: CountryRegistry,
    selection: Selection,
) -> tuple[dict[str, Any], WrittenOutputs]:
    """Verify the survey-set responses and write report, preview and Slack page."""
    data = [
        (q, folder.read_response(q))
        for q in survey_set_queries
        if not q.name.endswith("_control")
    ]
    controls = [
        (q, folder.read_response(q))
        for q in survey_set_queries
        if q.name.endswith("_control")
    ]
    survey_sets = read_survey_sets(data)
    verify_survey_sets(survey_sets, controls)

    result = run_pipeline(projects, selection, registry, load_report_scope())
    surveys = derive_survey_states(projects, survey_sets, registry)
    report = build_report(
        context=context,
        selection=selection,
        registry=registry,
        result=result,
        surveys=surveys,
        watchlist=load_watchlist(watchlist_path),
        texts=load_reason_texts(),
    )

    from nps_v2.outputs.writer import write_outputs  # renderer import only when needed

    outputs = write_outputs(
        target,
        report=report,
        selection=selection,
        registry=registry,
        result=result,
        surveys=surveys,
    )
    return report, outputs


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _verified_projects(folder: RunFolder) -> list[ProjectSnapshot]:
    data_query, control_query = _project_queries(folder)
    projects = read_projects(folder.read_response(data_query), data_query)
    verify_projects(projects, folder.read_response(control_query), control_query)
    return projects


def _survey_set_queries(projects: Sequence[ProjectSnapshot]) -> list[Query]:
    """Data and control queries, interleaved per chunk."""
    ids = [p.project_id for p in projects]
    pairs = zip(
        build_survey_set_queries(ids),
        build_survey_set_control_queries(ids),
        strict=True,
    )
    return [query for pair in pairs for query in pair]


def _project_queries(folder: RunFolder) -> tuple[Query, Query]:
    queries = {q.name: q for q in folder.read_queries("projects")}
    try:
        return queries["projects"], queries["projects_control"]
    except KeyError as error:
        raise RunFolderError(f"queries.json lacks {error}") from None


def _query_list(folder: RunFolder, queries: Sequence[Query]) -> list[dict[str, str]]:
    return [
        {
            "name": q.name,
            "soql": q.soql,
            "save_as": str(folder.response_path(q).relative_to(folder.path)).replace(
                "\\", "/"
            ),
        }
        for q in queries
    ]


def _selection(args: argparse.Namespace) -> Selection:
    if args.date_to and not args.date_from:
        raise SelectionError("--to requires --from")
    if args.date_from:
        base = range_selection(args.date_from, args.date_to or args.date_from)
    elif args.day:
        base = day_selection(args.day)
    elif args.week_of:
        base = standard_week_selection(args.week_of)
    elif args.this_week:
        base = standard_week_selection(today_in_buenos_aires())
    else:
        raise SelectionError("Choose --this-week, --week-of, --day or --from/--to")
    filters = SearchFilters(
        project=args.project,
        client=args.client,
        facilitator=args.facilitator,
        sub_type=args.sub_type,
    )
    return base.extended(
        start_days=args.extend_start, end_days=args.extend_end
    ).with_filters(country_codes=tuple(args.country), filters=filters)


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected YYYY-MM-DD, got {value!r}"
        ) from None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m nps_v2", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    select = commands.add_parser("select", help="write the selection and print queries")
    select.add_argument("--run", required=True, help="run folder")
    when = select.add_mutually_exclusive_group()
    when.add_argument(
        "--this-week",
        action="store_true",
        help="standard week of today in Buenos Aires (scheduled Monday run)",
    )
    when.add_argument("--week-of", type=_iso_date, help="any day of the reference week")
    when.add_argument("--day", type=_iso_date, help="a single day")
    when.add_argument("--from", dest="date_from", type=_iso_date, help="range start")
    select.add_argument("--to", dest="date_to", type=_iso_date, help="range end")
    select.add_argument(
        "--extend-start", type=int, default=0, help="days earlier (+) or later (-)"
    )
    select.add_argument(
        "--extend-end", type=int, default=0, help="days later (+) or earlier (-)"
    )
    select.add_argument(
        "--country", action="append", default=[], help="AR, BR or MX; repeatable"
    )
    for name in ("project", "client", "facilitator", "sub-type"):
        select.add_argument(f"--{name}", dest=name.replace("-", "_"), default="")
    select.set_defaults(handler=command_select)

    surveys = commands.add_parser(
        "surveys", help="verify projects, print survey-set queries"
    )
    surveys.add_argument("--run", required=True)
    surveys.set_defaults(handler=command_surveys)

    capture = commands.add_parser(
        "capture", help="save connector responses from the session transcript"
    )
    capture.add_argument("--run", required=True)
    capture.add_argument(
        "--group",
        choices=("projects", "survey_sets", "creation_recheck", "creation_after"),
        required=True,
    )
    capture.add_argument(
        "--transcript", default="", help="session .jsonl (default: newest)"
    )
    capture.set_defaults(handler=command_capture)

    plan = commands.add_parser("plan", help="V2-2: plan the surveys to create")
    plan.add_argument("--run", required=True)
    plan.add_argument(
        "--exclude", action="append", default=[], help="project Id to leave out"
    )
    plan.add_argument(
        "--only",
        action="append",
        default=[],
        help="pilot: project Id to keep (all other sessions are left out)",
    )
    plan.set_defaults(handler=command_plan)

    approve_parser = commands.add_parser(
        "approve", help="V2-2: record the user's approval code"
    )
    approve_parser.add_argument("--run", required=True)
    approve_parser.add_argument("--code", required=True)
    approve_parser.set_defaults(handler=command_approve)

    execute_parser = commands.add_parser(
        "execute", help="V2-2: start or continue; prints the next call"
    )
    execute_parser.add_argument("--run", required=True)
    execute_parser.set_defaults(handler=command_execute)

    record_parser = commands.add_parser(
        "record", help="V2-2: save the result of the current call"
    )
    record_parser.add_argument("--run", required=True)
    record_parser.add_argument("--transcript", default="")
    record_parser.add_argument(
        "--response-file", default="", help="the call's result, saved by hand"
    )
    record_parser.set_defaults(handler=command_record)

    reconcile_parser = commands.add_parser(
        "reconcile", help="V2-2: verify in Salesforce and write the outputs"
    )
    reconcile_parser.add_argument("--run", required=True)
    reconcile_parser.set_defaults(handler=command_reconcile)

    compare_parser = commands.add_parser(
        "compare", help="parallel run: compare with the desktop selam_worklist.csv"
    )
    compare_parser.add_argument("--run", required=True)
    compare_parser.add_argument("--desktop", required=True, help="desktop CSV")
    compare_parser.set_defaults(handler=command_compare)

    upcoming = commands.add_parser(
        "upcoming", help="verify everything and write outputs"
    )
    upcoming.add_argument("--run", required=True)
    upcoming.add_argument("--run-id", default="")
    upcoming.add_argument("--generated-at", default="", help="ISO timestamp (tests)")
    upcoming.add_argument(
        "--watchlist",
        default="",
        help="watch-list file (default: config/v2/watchlist.json)",
    )
    upcoming.set_defaults(handler=command_upcoming)
    return parser


def _print(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
