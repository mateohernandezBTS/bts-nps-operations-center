"""Source configuration contracts used by the weekly inventory."""

from __future__ import annotations

import unittest

from engine.source_config import (
    get_enabled_sources,
    get_required_sources,
    load_source_configuration,
)


class SourceConfigTest(unittest.TestCase):
    def test_enabled_sources(self) -> None:
        sources = get_enabled_sources("weekly_upcoming")
        self.assertEqual(
            [s["source_id"] for s in sources],
            ["upcoming_argentina", "upcoming_brazil", "upcoming_mexico"],
        )
        self.assertEqual(
            [s["country"] for s in sources], ["Argentina", "Brazil", "Mexico"]
        )
        self.assertTrue(
            all(s["enabled"] and s["report_type"] == "upcoming" for s in sources)
        )
        self.assertEqual(load_source_configuration()["version"], 1)

    def test_required_sources(self) -> None:
        self.assertEqual(
            get_required_sources("weekly_upcoming"),
            get_enabled_sources("weekly_upcoming"),
        )
        self.assertTrue(
            all(s["required"] for s in get_required_sources("weekly_upcoming"))
        )

    def test_historical_group_is_optional(self) -> None:
        sources = get_enabled_sources("last_results")
        self.assertEqual(
            [s["source_id"] for s in sources],
            ["last_results_argentina", "last_results_brazil", "last_results_mexico"],
        )
        self.assertTrue(
            all(
                not s["required"] and s["report_type"] == "last_results"
                for s in sources
            )
        )
        self.assertEqual(get_required_sources("last_results"), [])
        group = load_source_configuration()["source_groups"]["last_results"]
        self.assertTrue(group["allow_partial_run"])
        self.assertFalse(group["required_for_completion"])
