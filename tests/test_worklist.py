"""Weekly boundaries, ID extraction and output readiness."""

from __future__ import annotations

import unittest
from urllib.parse import unquote, urlsplit

from engine.stages.worklist import (
    extract_salesforce_id,
    load_operational_config,
    normalize_facilitators,
)
from tests.support.stage_cases import declarations, worklist


class WorklistTest(unittest.TestCase):
    def test_inclusive_edges(self) -> None:
        result = worklist("classification_Mexico_worklist_review")
        self.assertEqual(
            [
                r["Date"]
                for r in result["worklist"]
                if r["Session"] in ("Fixture Session 085", "Fixture Session 086")
            ],
            ["8/4/2026", "8/10/2026"],
        )
        self.assertEqual(
            [r["start_date"] for r in result["outside_window"]],
            ["8/3/2026", "8/11/2026"],
        )
        for row in result["outside_window"]:
            self.assertEqual(
                (row["window_start"], row["window_end"]), ("8/4/2026", "8/10/2026")
            )
            self.assertEqual(row["window_reason"], "Fecha fuera de la ventana semanal")

    def test_project_id_extraction(self) -> None:
        lengths = set()
        for key, declaration in declarations().items():
            url = declaration["links"]["project_name"]
            with self.subTest(row=key):
                expected = (
                    ""
                    if not url or key == "bad_project_url"
                    else unquote(urlsplit(url).path).split("/")[-1]
                )
                self.assertEqual(extract_salesforce_id(url), expected)
                if expected:
                    lengths.add(len(expected))
        self.assertEqual(lengths, {15, 18})

    def test_facilitator_normalization(self) -> None:
        config = load_operational_config()
        raw = declarations()["facilitators"]["values"]["all_staffings"]
        self.assertEqual(
            normalize_facilitators(raw, config),
            "Fixture Facilitator Lumen,Fixture Facilitator Nova",
        )
        for placeholder in config["facilitators"]["empty_values"]:
            self.assertEqual(normalize_facilitators(placeholder, config), "")

    def test_review_partition_and_columns(self) -> None:
        result = worklist("classification_Mexico_worklist_review")
        self.assertEqual(
            [r["Session"] for r in result["review"]],
            ["Fixture Session 088", "Fixture Session 089"],
        )
        self.assertEqual(len(result["worklist"]), len(result["ready"]) + 2)
        for row in result["review"]:
            self.assertEqual(
                row["Output Issues"], "No se pudo extraer Project ID desde Project URL"
            )
            self.assertEqual(row["Link for Results"], "")
        # NPS-002: invitation columns are currently dropped.
        self.assertEqual(
            list(worklist("parser_Argentina_invitation_both")["ready"][0]),
            [
                "Session",
                "Date",
                "Facilitator",
                "QR-Code",
                "Link NPS Survey",
                "Link Insights Facilitators",
                "Results",
                "Link for Results",
                "Project ID",
                "Client",
                "Project URL",
                "Output Status",
                "Output Issues",
            ],
        )
