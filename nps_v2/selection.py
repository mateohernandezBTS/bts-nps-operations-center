"""Flexible selection of the sessions to work on.

A selection is an inclusive date range on the project start date, an optional list of
country codes and optional text filters. Presets:

* **standard week** — the week of a reference Monday: from the Tuesday after it to the
  following Monday, inclusive (any day maps to the Monday of its week);
* **single day** and **explicit range**;
* any selection can be extended or shrunk at either end.

Selections are safe to re-run: what is already created is read from Salesforce, not
from previous runs.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Any

from nps_v2.domain import ProjectSnapshot

MAX_SPAN_DAYS = 92
DATE_DISPLAY = "%d/%m/%Y"


class SelectionError(ValueError):
    """The requested selection is invalid."""


def reference_monday(day: date) -> date:
    """Monday of the week that contains ``day`` (a Monday maps to itself)."""
    return day - timedelta(days=day.weekday())


def standard_week(day: date) -> tuple[date, date]:
    """Standard window for the week of ``day``: Tuesday to next Monday, inclusive."""
    monday = reference_monday(day)
    return monday + timedelta(days=1), monday + timedelta(days=7)


def normalize_text(value: str) -> str:
    """Accent-insensitive, case-insensitive, whitespace-collapsed text."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_marks.casefold().split())


@dataclass(frozen=True, slots=True)
class SearchFilters:
    """Optional "contains" filters, combined with AND. Empty means "no filter"."""

    project: str = ""
    client: str = ""
    facilitator: str = ""
    sub_type: str = ""

    def __post_init__(self) -> None:
        for name in ("project", "client", "facilitator", "sub_type"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise SelectionError(f"Filter {name!r} must be text")
            object.__setattr__(self, name, " ".join(value.split()))

    @property
    def is_empty(self) -> bool:
        return not (self.project or self.client or self.facilitator or self.sub_type)

    def matches(self, project: ProjectSnapshot) -> bool:
        checks = (
            (self.project, project.name),
            (self.client, project.client_name),
            (self.facilitator, project.all_staffings),
            (self.sub_type, project.sub_type),
        )
        return all(
            normalize_text(wanted) in normalize_text(actual)
            for wanted, actual in checks
            if wanted
        )


@dataclass(frozen=True, slots=True)
class Selection:
    """What to work on. Country filtering happens in the generated query."""

    date_from: date
    date_to: date
    label: str
    country_codes: tuple[str, ...] = ()
    filters: SearchFilters = field(default_factory=SearchFilters)

    def __post_init__(self) -> None:
        if self.date_from > self.date_to:
            raise SelectionError(
                f"Start {_show(self.date_from)} is after end {_show(self.date_to)}"
            )
        span = (self.date_to - self.date_from).days + 1
        if span > MAX_SPAN_DAYS:
            raise SelectionError(
                f"Selection spans {span} days; the maximum is {MAX_SPAN_DAYS}"
            )
        codes = tuple(code.strip().upper() for code in self.country_codes)
        if any(not code for code in codes):
            raise SelectionError("Country codes must not be empty")
        if len(set(codes)) != len(codes):
            raise SelectionError(f"Duplicate country codes: {', '.join(codes)}")
        object.__setattr__(self, "country_codes", codes)

    @property
    def days(self) -> int:
        return (self.date_to - self.date_from).days + 1

    def contains(self, day: date) -> bool:
        return self.date_from <= day <= self.date_to

    def extended(self, *, start_days: int = 0, end_days: int = 0) -> Selection:
        """Move the start earlier by ``start_days`` and the end later by ``end_days``.

        Negative values shrink the selection instead.
        """
        if start_days == 0 and end_days == 0:
            return self
        date_from = self.date_from - timedelta(days=start_days)
        date_to = self.date_to + timedelta(days=end_days)
        return replace(
            self,
            date_from=date_from,
            date_to=date_to,
            label=f"{self.label}, ajustada a {_show(date_from)}–{_show(date_to)}",
        )

    def with_filters(
        self,
        *,
        country_codes: tuple[str, ...] | None = None,
        filters: SearchFilters | None = None,
    ) -> Selection:
        return replace(
            self,
            country_codes=self.country_codes
            if country_codes is None
            else country_codes,
            filters=self.filters if filters is None else filters,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "date_from": self.date_from.isoformat(),
            "date_to": self.date_to.isoformat(),
            "label": self.label,
            "country_codes": list(self.country_codes),
            "filters": {
                "project": self.filters.project,
                "client": self.filters.client,
                "facilitator": self.filters.facilitator,
                "sub_type": self.filters.sub_type,
            },
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> Selection:
        try:
            raw_filters = raw.get("filters") or {}
            return cls(
                date_from=date.fromisoformat(raw["date_from"]),
                date_to=date.fromisoformat(raw["date_to"]),
                label=str(raw["label"]),
                country_codes=tuple(raw.get("country_codes") or ()),
                filters=SearchFilters(**raw_filters),
            )
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, SelectionError):
                raise
            raise SelectionError(f"Invalid selection document: {error}") from error


def standard_week_selection(day: date) -> Selection:
    monday = reference_monday(day)
    date_from, date_to = standard_week(day)
    return Selection(
        date_from=date_from,
        date_to=date_to,
        label=(
            f"Semana estándar del lunes {_show(monday)} "
            f"({_show(date_from)}–{_show(date_to)})"
        ),
    )


def day_selection(day: date) -> Selection:
    return Selection(date_from=day, date_to=day, label=f"Día {_show(day)}")


def range_selection(date_from: date, date_to: date) -> Selection:
    return Selection(
        date_from=date_from,
        date_to=date_to,
        label=f"Rango {_show(date_from)}–{_show(date_to)}",
    )


def _show(day: date) -> str:
    return day.strftime(DATE_DISPLAY)
