"""Explicit immutable fixture lookup and copy-before-processing support."""

from __future__ import annotations

import shutil
from pathlib import Path

from tests.support.fixture_generator import fixture_root, load_inputs


def fixture_path(fixture_id: str) -> Path:
    """Resolve an explicit catalog ID without globbing ignored operational data."""
    for spec in load_inputs().catalog["fixtures"]:
        if spec["id"] == fixture_id:
            path = fixture_root() / "eml" / spec["path"]
            if not path.resolve().is_relative_to((fixture_root() / "eml").resolve()):
                raise ValueError("Fixture input escapes its versioned root")
            if not path.is_file():
                raise FileNotFoundError(path)
            return path
    raise KeyError(f"Unknown synthetic fixture ID: {fixture_id}")


def copy_fixture(fixture_id: str, destination: Path) -> Path:
    """Copy an input to a fresh destination; never modify or replace versioned data."""
    source = fixture_path(fixture_id)
    target = destination.resolve()
    if target.is_relative_to(fixture_root().resolve()):
        raise ValueError("Cannot copy operational inputs into the fixture source root")
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target
