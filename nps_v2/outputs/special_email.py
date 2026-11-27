"""Personalised e-mail for special cases (V2-5, first step: copy and paste).

Facilitators on the watch-list get their survey links by e-mail instead of only in the
Slack canvas. This module writes that e-mail: one per facilitator, covering all of their
sessions in the selection, with the same session cards as the Slack payload (title,
date, facilitator, survey links, QR, results). The Slack page offers "Copy subject" and
"Copy e-mail" so the user pastes it into a new Outlook message; nothing is sent or
saved anywhere by the engine.

Language (D-V2-15): the facilitator's office (``User.Department``, e.g.
``MX-Mexico City`` → Mexico → ``es``) when it is a market of the country registry;
otherwise the language of the countries of their sessions (the project's billing
office). Templates exist for ``es``, ``pt-BR`` and ``en-US``; any other language uses
English. The page around the e-mail stays in English (D-V2-8).
"""

from __future__ import annotations

import html
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class Template:
    greeting: str  # {name}
    one: str
    many: str
    closing: str
    label: str


TEMPLATES: Mapping[str, Template] = {
    "es": Template(
        greeting="Hola {name}, ¿cómo estás?",
        one=(
            "Te comparto los links del NPS de tu sesión, con el QR para acceso directo:"
        ),
        many=(
            "Te comparto los links del NPS de tus sesiones, con el QR para acceso "
            "directo:"
        ),
        closing="¡Gracias!",
        label="Spanish",
    ),
    "pt-BR": Template(
        greeting="Olá {name}, tudo bem?",
        one="Seguem os links do NPS da sua sessão, com o QR Code para acesso direto:",
        many=(
            "Seguem os links do NPS das suas sessões, com o QR Code para acesso direto:"
        ),
        closing="Abraço!",
        label="Portuguese",
    ),
    "en-US": Template(
        greeting="Hi {name}, how are you?",
        one="Here are the NPS links for your session, with the QR code for direct "
        "access:",
        many="Here are the NPS links for your sessions, with the QR code for direct "
        "access:",
        closing="Thanks!",
        label="English",
    ),
}
FALLBACK_LANGUAGE = "en-US"


@dataclass(frozen=True, slots=True)
class EmailLanguage:
    code: str  # a key of TEMPLATES
    source: str  # why, for the page (English)


def choose_language(
    office: str,
    session_countries: Sequence[str],
    *,
    language_by_code: Mapping[str, str],
    language_by_country: Mapping[str, str],
) -> EmailLanguage:
    """Office first (``XX-City`` with ``XX`` a registry code), then the sessions'
    countries (most frequent language; ties go to the first session)."""
    office = " ".join(office.split())
    prefix = office.split("-", 1)[0].strip().upper() if "-" in office else ""
    if prefix in language_by_code:
        return EmailLanguage(_template(language_by_code[prefix]), f"office {office}")
    languages = [
        language_by_country[c] for c in session_countries if c in language_by_country
    ]
    if languages:
        counts = Counter(languages)
        best = max(languages, key=lambda lang: counts[lang])  # first among ties
        countries = ", ".join(dict.fromkeys(session_countries))
        why = f"office {office} is outside the markets; " if office else ""
        return EmailLanguage(_template(best), f"{why}session country {countries}")
    return EmailLanguage(FALLBACK_LANGUAGE, "no office or market found")


def languages_for(
    rows: Sequence[Row],
    special_cases: Mapping[str, Sequence[str]],
    offices: Mapping[str, str],
    *,
    language_by_code: Mapping[str, str],
    language_by_country: Mapping[str, str],
) -> dict[str, EmailLanguage]:
    """Language of each facilitator's e-mail. ``offices``: facilitator name (as in
    ``special_cases``) → office; ``rows``: Slack rows (``Country`` is the name)."""
    return {
        name: choose_language(
            offices.get(name, ""),
            [r.get("Country", "") for r in sessions],
            language_by_code=language_by_code,
            language_by_country=language_by_country,
        )
        for name, sessions in by_facilitator(rows, special_cases).items()
    }


def _template(language: str) -> str:
    return language if language in TEMPLATES else FALLBACK_LANGUAGE


def intro(name: str, sessions: int, language: str = "es") -> str:
    """Greeting and one sentence, as safe HTML."""
    template = TEMPLATES[_template(language)]
    sentence = template.one if sessions == 1 else template.many
    greeting = template.greeting.format(name=html.escape(first_name(name)))
    return f"<p>{greeting}</p><p>{html.escape(sentence)}</p>"


def closing(language: str = "es") -> str:
    return f"<p>{html.escape(TEMPLATES[_template(language)].closing)}</p>"


def label(language: str) -> str:
    return TEMPLATES[_template(language)].label
