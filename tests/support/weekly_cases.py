"""Fresh TEST roots and real pipeline collaborators for integration cases."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

from engine.source_inventory import SourceInventory, build_source_inventory
from engine.weekly_manifest import update_weekly_manifest_from_inventory
from engine.weekly_orchestrator import process_weekly_run
from engine.weekly_run import create_weekly_run
from tests.support.fixture_generator import load_inputs
from tests.support.fixture_paths import copy_fixture, fixture_path


def read_json(path: Path | str) -> Any:
    """Read a persisted test artifact."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


class IsolatedWeeklyCase(unittest.TestCase):
    """Allocate a fresh stdlib root per case and restore every patched collaborator."""

    def setUp(self) -> None:
        stack = self.enterContext(ExitStack())
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.pending = self.root / "pending"
        self.output = self.root / "weekly"
        self.pending.mkdir()
        self.config = {
            "version": "1.0",
            "environment": "TEST",
            "input_lifecycle": {
                f"{stage}_directory": str(self.root / stage)
                for stage in ("pending", "processing", "processed", "error")
            },
            "output": {"runs_directory": str(self.root / "runs")},
            "logs": {"directory": str(self.root / "logs")},
            "retention": {"enabled": False, "dry_run": True},
        }
        stack.enter_context(
            patch.dict(os.environ, {"BTS_SELAM_DATA_ROOT": str(self.root)})
        )
        # NPS-017: environment changes alone do not replace import-time constants.
        for module in ("engine.weekly_preflight", "engine.process_weekly_run"):
            stack.enter_context(patch(module + ".TEST_INPUT", self.pending))
            stack.enter_context(patch(module + ".TEST_OUTPUT", self.output))
        stack.enter_context(
            patch(
                "engine.process_weekly_run.load_execution_config",
                return_value=self.config,
            )
        )
        self.fixture_bytes: dict[str, bytes] = {}

    def tearDown(self) -> None:
        for fixture_id, content in self.fixture_bytes.items():
            self.assertEqual(fixture_path(fixture_id).read_bytes(), content)
        for path in self.root.rglob("*"):
            self.assert_local(path)

    def assert_local(self, path: Path | str) -> Path:
        """Reject artifacts outside this case's TEST root."""
        resolved = Path(path).resolve()
        self.assertTrue(resolved.is_relative_to(self.root), str(resolved))
        return resolved

    def populate(self, bundle: str, directory: Path | None = None) -> Path:
        """Copy the exact catalog bundle; never move immutable source fixtures."""
        destination = directory or self.pending
        destination.mkdir(parents=True, exist_ok=True)
        for fixture_id in load_inputs().catalog["bundles"][bundle]["fixtures"]:
            self.fixture_bytes[fixture_id] = fixture_path(fixture_id).read_bytes()
            copy_fixture(fixture_id, destination / fixture_path(fixture_id).name)
        return destination

    def inventory(self, bundle: str, directory: Path | None = None) -> SourceInventory:
        """Inventory a fresh copied catalog scenario."""
        return build_source_inventory(
            self.populate(bundle, directory), "weekly_upcoming"
        )

    def prepare(self, bundle: str = "complete_weekly") -> Path:
        """Create and inventory one isolated weekly run."""
        inventory = self.inventory(bundle)
        _, path = create_weekly_run("8/3/2026", output_root=self.output)
        update_weekly_manifest_from_inventory(path, inventory)
        return self.assert_local(path)

    def process(self, path: Path, *, stop_on_error: bool = False) -> dict[str, Any]:
        """Execute real parsing, stages and lifecycle under a test-only override."""
        with redirect_stdout(io.StringIO()):
            result: dict[str, Any] = process_weekly_run(
                path, stop_on_error=stop_on_error, execution_config=self.config
            )
        return result
