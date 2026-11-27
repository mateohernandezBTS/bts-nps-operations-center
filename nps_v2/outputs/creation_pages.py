"""V2-2 views on the shared UI kit (D-V2-11): the plan to approve and the result.

Both pages group surveys by country and session. They show data only; nothing on them
writes anywhere. The approval happens in the chat with the code shown on the plan page.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from datetime import date

from nps_v2.creation.plan import CreationPlan, SurveyCommand
from nps_v2.creation.reconcile import Outcome, SurveyOutcome, counts
from nps_v2.outputs.ui_kit import (
    Tile,
    attr,
    brandbar,
    kpi_tiles,
    render_document,
    safe_url,
    text,
)
from nps_v2.selection import display_date

KIND_LABEL = {"NPS": "NPS", "FACILITATORS": "Facilitators"}
OUTCOME_CSS = {
    Outcome.CREATED: "ok",
    Outcome.ALREADY_EXISTED: "neutral",
    Outcome.PARTIAL: "warn",
    Outcome.FAILED: "bad",
    Outcome.NOT_RUN: "neutral",
}


def render_plan_page(
    plan: CreationPlan, *, country_names: Mapping[str, str], generated_at: str
) -> str:
    commands = plan.commands
    sessions = _group(commands)
    tiles = kpi_tiles(
        (
            Tile("Sessions", len({c.project_id for c in commands})),
            Tile("Surveys to create", len(commands)),
            Tile("NPS", sum(1 for c in commands if c.kind == "NPS")),
            Tile("Facilitators", sum(1 for c in commands if c.kind == "FACILITATORS")),
            Tile(
                "Personalised e-mail",
                len({c.project_id for c in commands if c.special_case}),
                warn=True,
            ),
        )
    )
    approval = (
        '<ion-card class="approval"><div class="approval-body">'
        '<div><p class="eyebrow">Approval code</p>'
        f'<p class="code">{text(plan.short_hash)}</p></div>'
        "<p>Nothing has been written yet. To create <b>exactly</b> these "
        f"{len(commands)} surveys, reply in the chat with this code. Any change to the "
        "plan produces a new code.</p></div></ion-card>"
    )
    extra = ""
    if plan.excluded_projects:
        extra += _note_card(
            "Sessions you removed from the plan", plan.excluded_projects
        )
    if plan.already_created:
        extra += _note_card(
            "Already in Salesforce at the re-check (left out)", plan.already_created
        )
    body = approval + tiles + _sections(sessions, country_names, _plan_item) + extra
    if not commands:
        body = tiles + '<p class="empty">There are no surveys to create.</p>' + extra
    return render_document(
        title=f"Create surveys · {plan.run_id}",
        header=brandbar(
            "NPS · Create surveys — plan",
            f"{plan.selection_label} · run {plan.run_id} · generated {generated_at}",
        ),
        body=body,
        css=_CSS,
    )


def render_result_page(
    outcomes: Sequence[SurveyOutcome],
    *,
    plan: CreationPlan,
    operator: str,
    run_error: str,
    country_names: Mapping[str, str],
    generated_at: str,
) -> str:
    total = counts(outcomes)
    tiles = kpi_tiles(
        (
            Tile("Created", total[Outcome.CREATED.value]),
            Tile("Already existed", total[Outcome.ALREADY_EXISTED.value]),
            Tile("Partial", total[Outcome.PARTIAL.value], warn=True),
            Tile("Failed", total[Outcome.FAILED.value], warn=True),
            Tile("Not run", total[Outcome.NOT_RUN.value], warn=True),
        )
    )
    banner = (
        f'<div class="banner bad"><b>The run stopped:</b> {text(run_error)}</div>'
        if run_error
        else '<div class="banner ok">Every planned step ran. See each survey below.'
        "</div>"
    )
    meta = (
        f'<p class="meta">Approved plan <b>{text(plan.short_hash)}</b> · created by '
        f"<b>{text(operator or 'unknown')}</b></p>"
    )
    by_command = {o.command.key: o for o in outcomes}
    sessions = _group([o.command for o in outcomes])
    body = (
        banner
        + meta
        + tiles
        + _sections(sessions, country_names, lambda c: _result_item(by_command[c.key]))
    )
    return render_document(
        title=f"Survey creation result · {plan.run_id}",
        header=brandbar(
            "NPS · Create surveys — result",
            f"{plan.selection_label} · run {plan.run_id} · generated {generated_at}",
        ),
        body=body,
        css=_CSS,
    )


# --- building blocks ---------------------------------------------------------------


Grouped = Mapping[str, Mapping[str, Sequence[SurveyCommand]]]


def _group(
    commands: Sequence[SurveyCommand],
) -> dict[str, dict[str, list[SurveyCommand]]]:
    grouped: dict[str, dict[str, list[SurveyCommand]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for command in commands:
        grouped[command.country][command.project_id].append(command)
    return grouped


def _sections(
    grouped: Grouped,
    country_names: Mapping[str, str],
    item: Callable[[SurveyCommand], str],
) -> str:
    """``country_names``: country code → name, in display order."""
    order = {code: index for index, code in enumerate(country_names)}
    html = []
    for country in sorted(grouped, key=lambda c: (order.get(c, len(order)), c)):
        sessions = grouped[country]
        cards = "".join(_session_card(cmds, item) for cmds in _ordered(sessions))
        html.append(
            f'<section class="country"><h2 class="section-title">'
            f"{text(country_names.get(country, country))}"
            f'<ion-badge class="count">{len(sessions)}</ion-badge></h2>'
            f"{cards}</section>"
        )
    return "".join(html)


def _ordered(
    sessions: Mapping[str, Sequence[SurveyCommand]],
) -> list[Sequence[SurveyCommand]]:
    return sorted(
        sessions.values(),
        key=lambda cmds: (cmds[0].start_date, cmds[0].client, cmds[0].project_name),
    )


def _session_card(
    commands: Sequence[SurveyCommand], item: Callable[[SurveyCommand], str]
) -> str:
    first = commands[0]
    notice = (
        '<div class="callout"><b>Personalised e-mail:</b> this session has a '
        "facilitator from the special-case list.</div>"
        if first.special_case
        else ""
    )
    items = "".join(item(c) for c in commands)
    return (
        f'<ion-card class="session-card" data-project="{attr(first.project_id)}">'
        '<div class="card-head"><div>'
        f"<ion-card-title>{text(first.project_name)}</ion-card-title>"
        f"<ion-card-subtitle>{text(first.client)} · "
        f"{text(display_date(date.fromisoformat(first.start_date)))}</ion-card-subtitle>"
        f'</div></div>{notice}<ion-list lines="full">{items}</ion-list></ion-card>'
    )


def _plan_item(command: SurveyCommand) -> str:
    return (
        '<ion-item lines="full" class="survey"><ion-label class="ion-text-wrap">'
        f"<h3>{text(KIND_LABEL.get(command.kind, command.kind))} · "
        f"{text(command.survey_name)}</h3>"
        f"<p>Language {text(command.language)} · invitation "
        f"“{text(command.survey_name)} for {text(command.project_name)}”</p>"
        "</ion-label>"
        '<ion-chip class="pending" outline="true">To create</ion-chip></ion-item>'
    )


def _result_item(outcome: SurveyOutcome) -> str:
    command = outcome.command
    link = safe_url(outcome.link)
    open_link = (
        f'<a href="{attr(link)}" target="_blank" rel="noopener">'
        '<ion-chip class="link" outline="true">Open survey</ion-chip></a>'
        if link and outcome.outcome is Outcome.CREATED
        else ""
    )
    note = f'<p class="note">{text(outcome.note)}</p>' if outcome.note else ""
    return (
        '<ion-item lines="full" class="survey"><ion-label class="ion-text-wrap">'
        f"<h3>{text(KIND_LABEL.get(command.kind, command.kind))} · "
        f"{text(command.survey_name)} ({text(command.language)})</h3>{note}"
        f'<div class="chips">{open_link}</div></ion-label>'
        f'<ion-chip class="{OUTCOME_CSS[outcome.outcome]}" outline="true">'
        f"{text(outcome.outcome.value.capitalize())}</ion-chip></ion-item>"
    )


def _note_card(title: str, values: Sequence[str]) -> str:
    items = "".join(f"<li>{text(v)}</li>" for v in values)
    return (
        f'<ion-card class="note-card"><div class="card-head"><div>'
        f"<ion-card-title>{text(title)}</ion-card-title></div></div>"
        f"<ul>{items}</ul></ion-card>"
    )


_CSS = """
ion-card.approval{border-color:var(--magenta);
box-shadow:0 8px 28px rgba(202,28,104,.12)}
.approval-body{display:flex;gap:24px;align-items:center;padding:18px 22px;
flex-wrap:wrap}
.approval-body p{margin:0;max-width:640px}
.eyebrow{font-size:11.5px;text-transform:uppercase;letter-spacing:.6px;font-weight:700;
color:var(--grey-text)}
.code{font:800 30px/1.1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
color:var(--magenta);letter-spacing:1px}
ion-item.survey{--padding-start:18px;--inner-padding-end:14px;--min-height:64px}
ion-item.survey h3{font-size:14.5px;font-weight:650;margin:0 0 2px}
ion-item.survey p{font-size:12.5px;color:var(--grey-text);margin:0}
ion-item.survey p.note{color:#9b2433}
.chips{display:flex;flex-wrap:wrap;gap:2px;margin:6px 0 0 -4px}
.chips a{text-decoration:none;color:inherit}
ion-chip.pending,ion-chip.link{--color:#CA1C68;color:#CA1C68;
--background:rgba(202,28,104,.06);border-color:rgba(202,28,104,.35)}
ion-chip.ok{--color:#1D7279;color:#1D7279;--background:#EDF7F6;border-color:#BFE0DC}
ion-chip.neutral{--color:#5e6367;color:#5e6367;--background:#F7F8F9;border-color:#D5D9DD}
ion-chip.warn{--color:#9a5b12;color:#9a5b12;--background:#FFF6EA;border-color:#F2D2A6}
ion-chip.bad{--color:#9b2433;color:#9b2433;--background:#FDF0EF;border-color:#F4B1A7}
.banner{padding:12px 16px;border-radius:12px;margin:0 0 12px;font-size:13.5px}
.banner.ok{background:#EDF7F6;color:#1D7279;border:1px solid #BFE0DC}
.banner.bad{background:#FDF0EF;color:#9b2433;border:1px solid #F4B1A7}
.meta{margin:0 0 12px;color:var(--grey-text);font-size:13px}
.note-card ul{margin:0;padding:0 18px 16px 36px;font-size:13px;color:var(--grey-text)}
"""
