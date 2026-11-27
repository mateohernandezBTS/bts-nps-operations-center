"""Personalised e-mail for special cases (V2-5, first step: copy and paste).

Facilitators on the watch-list get their survey links by e-mail instead of only in the
Slack canvas. This module writes that e-mail: one per facilitator, covering all of their
sessions in the selection, with the same session cards as the Slack payload (title,
date, facilitator, survey links, QR, results). The Slack page offers "Copy subject" and
"Copy e-mail" so the user pastes it into a new Outlook message; nothing is sent or
saved anywhere by the engine.

The e-mail is written in Spanish, the language the product owner uses with the
facilitators (D-V2-14, proposed); the page around it stays in English (D-V2-8).
"""

from __future__ import annotations

import html
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, timedelta

Row = Mapping[str, str]

SUBJECT_PREFIX = "NPS week"


def week_monday(day: date) -> date:
    """Monday on or before ``day`` (the report Monday: 30 Nov for 1–7 Dec)."""
    return day - timedelta(days=day.weekday())


def subject(week_start: date | None) -> str:
    """``NPS week dd/mm/yy`` (the product owner's subject), or the prefix alone."""
    if week_start is None:
        return SUBJECT_PREFIX
    return f"{SUBJECT_PREFIX} {week_monday(week_start).strftime('%d/%m/%y')}"


def day_first(records: Sequence[Row]) -> list[dict[str, str]]:
    """Copies of the Slack rows with ``Date`` as dd/mm/yyyy.

    The Slack columns keep the desktop's month-first date (``12/1/2026``), which a
    Spanish reader takes as 12 January; the e-mail uses ``01/12/2026``. A date that is
    not month/day/year is left as it is.
    """
    result = []
    for record in records:
        copy = dict(record)
        parts = copy.get("Date", "").strip().split("/")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            month, day, year = parts
            copy["Date"] = f"{int(day):02d}/{int(month):02d}/{year}"
        result.append(copy)
    return result


def first_name(name: str) -> str:
    parts = name.split()
    return parts[0] if parts else ""


def by_facilitator(
    rows: Sequence[Row], special_cases: Mapping[str, Sequence[str]]
) -> dict[str, list[Row]]:
    """Facilitator name → their special-case sessions (in the given order)."""
    grouped: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        for name in special_cases.get(row.get("Project ID", ""), ()):
            grouped[" ".join(name.split())].append(row)
    return dict(sorted(grouped.items(), key=lambda item: item[0].casefold()))


def intro(name: str, sessions: int) -> str:
    """Greeting and one sentence, as safe HTML."""
    target = "tu sesión" if sessions == 1 else "tus sesiones"
    return (
        f"<p>Hola {html.escape(first_name(name))}, ¿cómo estás?</p>"
        f"<p>Te comparto los links del NPS de {target}, con el QR para acceso "
        "directo:</p>"
    )


CLOSING = "<p>¡Gracias!</p>"
