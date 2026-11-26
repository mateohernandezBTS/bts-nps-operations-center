"""Facilitators who need a personalised e-mail (special cases).

Their surveys are created as usual; the run only flags them. The real list contains
people's names, so it lives in ``config/v2/watchlist.json`` inside the installed skill
and is git-ignored; the repository ships a synthetic template
(``watchlist.example.json``). A missing file is reported, never treated as "no special
cases".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from engine.paths import config_path
from nps_v2.domain import ProjectSnapshot
from nps_v2.selection import normalize_text

DEFAULT_WATCHLIST_PATH_PARTS = ("v2", "watchlist.json")


class WatchlistError(ValueError):
    """The watch-list file exists but is invalid."""


@dataclass(frozen=True, slots=True)
class Watchlist:
    names: tuple[str, ...]

    def matches(self, project: ProjectSnapshot) -> tuple[str, ...]:
        staffing = normalize_text(project.all_staffings)
        return tuple(name for name in self.names if normalize_text(name) in staffing)


def load_watchlist(path: Path | None = None) -> Watchlist | None:
    """The configured watch-list, or ``None`` when no file is installed."""
    watchlist_path = path or config_path(*DEFAULT_WATCHLIST_PATH_PARTS)
    if not watchlist_path.exists():
        return None
    try:
        raw = json.loads(watchlist_path.read_text(encoding="utf-8"))
        names = raw["facilitators"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise WatchlistError(
            f"Cannot read watch-list {watchlist_path}: {error}"
        ) from error
    if not isinstance(names, list) or not all(
        isinstance(n, str) and n.strip() for n in names
    ):
        raise WatchlistError("'facilitators' must be a list of non-empty names")
    return Watchlist(names=tuple(" ".join(n.split()) for n in names))
