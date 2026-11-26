"""Command line used by the skill. Three steps, each printing JSON for Claude.

1. ``select``   — writes the selection and prints the project queries to run.
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
from typing import Any

from nps_v2.domain import ProjectSnapshot
from nps_v2.pipeline import PipelineError, load_report_scope, run_pipeline
from nps_v2.registry import RegistryError, load_registry
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
)
from nps_v2.surveys.state import SurveyStateError, derive_survey_states
from nps_v2.watchlist import WatchlistError, load_watchlist

EXIT_ERROR = 2
KNOWN_ERRORS = (
    PipelineError,
    ReaderError,
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
    data = [
        (q, folder.read_response(q)) for q in queries if not q.name.endswith("_control")
    ]
    controls = [
        (q, folder.read_response(q)) for q in queries if q.name.endswith("_control")
    ]
    survey_sets = read_survey_sets(data)
    verify_survey_sets(survey_sets, controls)

    result = run_pipeline(projects, selection, registry, load_report_scope())
    surveys = derive_survey_states(projects, survey_sets, registry)
    context = RunContext(
        run_id=args.run_id or folder.path.name,
        generated_at=args.generated_at
        or datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    report = build_report(
        context=context,
        selection=selection,
        registry=registry,
        result=result,
        surveys=surveys,
        watchlist=load_watchlist(Path(args.watchlist) if args.watchlist else None),
    )

    from nps_v2.outputs.writer import write_outputs  # renderer import only when needed

    outputs = write_outputs(
        folder.path,
        report=report,
        selection=selection,
        registry=registry,
        result=result,
        surveys=surveys,
    )
    return {
        "step": "upcoming",
        "summary": report["summary"],
        "watchlist_configured": report["watchlist_configured"],
        "outputs": {
            "report": str(outputs.report),
            "preview": str(outputs.preview),
            "slack_html": str(outputs.slack_html),
        },
    }


# --- helpers -----------------------------------------------------------------------


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
    else:
        raise SelectionError("Choose --week-of, --day or --from/--to")
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
