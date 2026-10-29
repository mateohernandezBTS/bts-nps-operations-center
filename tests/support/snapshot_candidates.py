"""Explicit candidate export and provenance; no snapshot approval operation exists."""

from __future__ import annotations

import difflib
import hashlib
import platform
from importlib.metadata import version
from typing import Any

from engine.paths import repository_path
from tests.support.snapshot_projection import json_text

SNAPSHOT_ROOT = repository_path("tests", "snapshots", "phase1", "v1")
CANDIDATE_ROOT = repository_path(".codex-log", "snapshot-candidates", "F1-05A")


def sha256(data: bytes) -> str:
    """Hash exact serialized candidate or input bytes."""
    return hashlib.sha256(data).hexdigest()


def provenance(projections: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Separate asserted behavior inputs from informational implementation hashes."""
    root = repository_path()
    sources = [
        path
        for directory in ("app", "engine", "packaging")
        for path in sorted((root / directory).rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix in (".py", ".json", ".txt")
    ]
    inputs = list(sorted((root / "config").glob("*.json")))
    inputs.extend(
        root / "tests" / "fixtures" / name
        for name in ("catalog.json", "rows.json", "fixture_manifest.json")
    )
    return {
        "schema_version": 2,
        "status": "PENDING",
        "python": platform.python_version(),
        "platform": platform.system(),
        "packages": {
            name: version(name)
            for name in (
                "PySide6",
                "openpyxl",
                "beautifulsoup4",
                "pytest",
                "pytest-cov",
                "coverage",
            )
        },
        "input_sha256": {
            p.relative_to(root).as_posix(): sha256(p.read_bytes()) for p in inputs
        },
        "source_sha256": {
            p.relative_to(root).as_posix(): sha256(p.read_bytes()) for p in sources
        },
        "candidate_sha256": {
            scenario + "/" + name: sha256(text.encode("utf-8"))
            for scenario, files in projections.items()
            for name, text in files.items()
        },
    }


def write_candidates(projections: dict[str, dict[str, str]]) -> None:
    """Export only to the ignored review area after an explicit environment opt-in."""
    for scenario, files in projections.items():
        directory = CANDIDATE_ROOT / scenario
        directory.mkdir(parents=True, exist_ok=True)
        expected = set(files)
        existing = {p.name for p in directory.iterdir()}
        if existing - expected:
            raise AssertionError(
                f"Stale candidate files require review: {existing - expected}"
            )
        for name, text in files.items():
            (directory / name).write_bytes(text.encode("utf-8"))
    (CANDIDATE_ROOT / "provenance.json").write_bytes(
        json_text(provenance(projections)).encode("utf-8")
    )


def compare(expected: dict[str, str], actual: dict[str, str]) -> None:
    """Fail on missing/extra files or any semantic difference, with a useful diff."""
    if expected.keys() != actual.keys():
        raise AssertionError(
            f"Snapshot files differ: {expected.keys() ^ actual.keys()}"
        )
    for name in expected:
        if expected[name] != actual[name]:
            diff = "".join(
                difflib.unified_diff(
                    expected[name].splitlines(keepends=True),
                    actual[name].splitlines(keepends=True),
                    fromfile="candidate/" + name,
                    tofile="actual/" + name,
                )
            )
            raise AssertionError(diff)


def read_snapshot(scenario: str) -> dict[str, str]:
    """Missing candidates fail; reading PENDING data never implies approval."""
    directory = SNAPSHOT_ROOT / scenario
    if not directory.is_dir():
        raise AssertionError(f"Missing snapshot scenario: {directory}")
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(directory.iterdir())}
