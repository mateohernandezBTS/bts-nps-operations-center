"""Synthetic inputs for pure-stage characterization, without lifecycle I/O."""

from __future__ import annotations

from typing import Any

from engine.stages.business_rules import apply_business_rules
from engine.stages.email_parser import parse_eml_report
from engine.stages.normalize import normalize_records
from engine.stages.worklist import generate_worklist
from tests.support.fixture_generator import load_inputs
from tests.support.fixture_paths import fixture_path


def parsed_rows(fixture_id: str) -> dict[str, dict[str, Any]]:
    """Associate parsed rows with explicit catalog IDs in source order."""
    spec = next(s for s in load_inputs().catalog["fixtures"] if s["id"] == fixture_id)
    return dict(
        zip(spec["rows"], parse_eml_report(fixture_path(fixture_id)), strict=True)
    )


def declarations() -> dict[str, Any]:
    """Return versioned independent expectations."""
    return load_inputs().rows["rows"]


def classification_rows() -> dict[str, dict[str, Any]]:
    """Read classification fixtures with their declared row IDs."""
    return {
        key: row
        for country, suffix in (
            ("Argentina", "rules"),
            ("Brazil", "normalization"),
            ("Mexico", "worklist_review"),
        )
        for key, row in parsed_rows(f"classification_{country}_{suffix}").items()
    }


def worklist(fixture_id: str) -> dict[str, Any]:
    """Run real stages with the fixed reference Monday."""
    normalized, _ = normalize_records(list(parsed_rows(fixture_id).values()))
    return generate_worklist(
        apply_business_rules(normalized)["eligible"], reference_monday="8/3/2026"
    )
