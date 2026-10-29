"""POD comparisons are assertions collected by both runners."""

from __future__ import annotations

import unittest

from engine.stages.business_rules import matches_pattern
from tests.support.stage_cases import classification_rows


class PodRuleTest(unittest.TestCase):
    def assert_match(self, row_id: str, expected: bool) -> None:
        value = classification_rows()[row_id]["project_name"]
        self.assertIs(matches_pattern(value, r"\bpod\b", "regex_any"), expected)

    def test_empoderamiento(self) -> None:
        # NPS-005: preserve singular word matching, including plural nonmatch.
        self.assert_match("control_empoderamiento", False)

    def test_singular(self) -> None:
        # NPS-005: preserve singular word matching, including plural nonmatch.
        self.assert_match("rule_pod_project_name_0", True)

    def test_coaching(self) -> None:
        # NPS-005: preserve singular word matching, including plural nonmatch.
        self.assert_match("rule_coaching_project_name_1", True)

    def test_multiple_reasons(self) -> None:
        # NPS-005: preserve singular word matching, including plural nonmatch.
        self.assert_match("multi_exclude_review", True)

    def test_plural(self) -> None:
        # NPS-005: preserve singular word matching, including plural nonmatch.
        self.assert_match("control_plural", False)

    def test_embedded(self) -> None:
        # NPS-005: preserve singular word matching, including plural nonmatch.
        self.assert_match("control_embedded", False)

    def test_accent(self) -> None:
        # NPS-005: preserve singular word matching, including plural nonmatch.
        self.assert_match("control_accent_regex", False)
