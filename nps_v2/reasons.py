"""English wording for the certified engine's decisions and issues.

The certified stages (``engine/stages``) write decision reasons and validation issues
in Spanish, and they must not change. V2 shows everything to its users in English:

* decisions of configurable rules are worded from their rule id
  (``config/v2/rule_labels.json``), so a new rule only needs a label there;
* the engine's fixed messages (eligibility, validation and worklist issues) are
  matched against their known wording.

Nothing is ever dropped: a message that matches no known wording is shown exactly as
the engine wrote it, so a future engine change degrades to Spanish text, never to a
missing reason.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from engine.paths import config_path

DEFAULT_LABELS_PATH_PARTS = ("v2", "rule_labels.json")
ISSUE_SEPARATOR = " | "

# (engine wording, English wording). Patterns are anchored; ``{value}`` is copied.
_FIXED_MESSAGES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern), english)
    for pattern, english in (
        (
            r"Status (?P<value>.*) no incluido en los estados elegibles\.?",
            "Status {value} is not an eligible status",
        ),
        (r"Ignore Reporting no es False\.?", "Ignore Reporting is not False"),
        (
            r"El registro tiene observaciones de validación\.?",
            "The record has validation issues",
        ),
        (r"Fecha inválida: (?P<value>.*)", "Invalid date: {value}"),
        (
            r"Valor booleano no reconocido: (?P<value>.*)",
            "Unrecognised true/false value: {value}",
        ),
        (r"Status vacío", "Status is empty"),
        (r"Status no reconocido: (?P<value>.*)", "Unrecognised status: {value}"),
        (
            r"Campo obligatorio vacío: (?P<value>.*)",
            "Required field is empty: {value}",
        ),
        (
            r"No se pudo extraer Project ID desde Project URL",
            "The Project ID could not be read from the Project URL",
        ),
        (r"(?P<value>Session|Date) vacío", "{value} is empty"),
    )
)


class ReasonTextsError(ValueError):
    """The rule label file is missing or invalid."""


@dataclass(frozen=True, slots=True)
class ReasonTexts:
    """Turns engine decisions and issues into English sentences."""

    rule_labels: Mapping[str, str]

    def decision(self, codes: Sequence[str], reasons: Sequence[str]) -> list[str]:
        """English reasons of one decision (codes and reasons come from the engine).

        Rule codes are worded from their label; everything else (eligibility and
        validation messages) from the engine's wording.
        """
        if len(codes) != len(reasons):  # validation issues: one code, many reasons
            return [self.message(reason) for reason in reasons]
        return [
            self.rule_labels.get(code) or self.message(reason)
            for code, reason in zip(codes, reasons, strict=True)
        ]

    def issues(self, joined: str) -> str:
        """English version of an engine issue list joined with `` | ``."""
        parts = [part.strip() for part in joined.split(ISSUE_SEPARATOR)]
        return "; ".join(self.message(part) for part in parts if part)

    @staticmethod
    def message(text: str) -> str:
        """One fixed engine message in English; unknown text is returned unchanged."""
        cleaned = " ".join(text.split())
        for pattern, english in _FIXED_MESSAGES:
            match = pattern.fullmatch(cleaned)
            if match:
                return english.format(**match.groupdict())
        return cleaned


def load_reason_texts(path: Path | None = None) -> ReasonTexts:
    labels_path = path or config_path(*DEFAULT_LABELS_PATH_PARTS)
    try:
        raw = json.loads(labels_path.read_text(encoding="utf-8"))
        labels = raw["rule_labels"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise ReasonTextsError(
            f"Cannot read rule labels {labels_path}: {error}"
        ) from error
    if not isinstance(labels, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and v.strip()
        for k, v in labels.items()
    ):
        raise ReasonTextsError("rule_labels must map rule ids to non-empty text")
    return ReasonTexts(rule_labels=dict(labels))
