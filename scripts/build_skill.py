"""Build the installable Claude skill for V2 (Upcoming, read-only).

Usage, from the repository root::

    python -m scripts.build_skill --out dist/skill [--watchlist PATH] [--zip]

The skill folder contains only what the runtime needs: ``SKILL.md``, the ``nps_v2``
package (with its page assets), the certified engine modules it imports and the
configuration it reads. No desktop code, no PySide6/bs4/openpyxl, no Windows paths.

The special-case watch-list holds real names, so it never comes from the
repository: pass ``--watchlist`` with a file kept outside it. Without it the skill
ships no list and every run says so.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "nps-upcoming-selam"

ENGINE_FILES = (
    "engine/__init__.py",
    "engine/paths.py",
    "engine/slack_canvas_renderer.py",
    "engine/stages/__init__.py",
    "engine/stages/business_rules.py",
    "engine/stages/normalize.py",
    "engine/stages/worklist.py",
)
CONFIG_FILES = (
    "config/business_rules.json",
    "config/operational_output.json",
    "config/v2/countries.json",
    "config/v2/report_scope.json",
    "config/v2/rule_labels.json",
    "config/v2/watchlist.example.json",
)
PACKAGE = "nps_v2"
PACKAGE_SUFFIXES = (".py", ".css", ".js")
WATCHLIST_TARGET = "config/v2/watchlist.json"
BUILD_INFO = "BUILD_INFO.json"


class BuildError(RuntimeError):
    """The skill cannot be built safely."""


def source_files(root: Path = REPOSITORY_ROOT) -> list[str]:
    """Repository-relative files that go into the skill (sorted, POSIX paths)."""
    package = sorted(
        path.relative_to(root).as_posix()
        for path in (root / PACKAGE).rglob("*")
        if path.is_file()
        and path.suffix in PACKAGE_SUFFIXES
        and "__pycache__" not in path.parts
    )
    files = ["skill/SKILL.md", *ENGINE_FILES, *CONFIG_FILES, *package]
    missing = [name for name in files if not (root / name).is_file()]
    if missing:
        raise BuildError(f"Missing source files: {', '.join(missing)}")
    return files


def build(
    out: Path,
    *,
    watchlist: Path | None = None,
    root: Path = REPOSITORY_ROOT,
    make_zip: bool = False,
) -> Path:
    """Write the skill into ``out/<SKILL_NAME>`` (replacing it) and return that path."""
    target = out / SKILL_NAME
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    hashes: dict[str, str] = {}
    for name in source_files(root):
        destination = "SKILL.md" if name == "skill/SKILL.md" else name
        _copy(root / name, target / destination)
        hashes[destination] = _sha256(target / destination)

    if watchlist is not None:
        _check_watchlist(watchlist, root)
        _copy(watchlist, target / WATCHLIST_TARGET)
        hashes[WATCHLIST_TARGET] = _sha256(target / WATCHLIST_TARGET)

    info = {
        "skill": SKILL_NAME,
        "nps_v2_version": _version(root),
        "git_commit": _git_commit(root),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "watchlist_installed": watchlist is not None,
        "files": dict(sorted(hashes.items())),
    }
    (target / BUILD_INFO).write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if make_zip:
        archive = out / f"{SKILL_NAME}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(target.rglob("*")):
                if path.is_file():
                    bundle.write(path, path.relative_to(out).as_posix())
    return target


def _inside_repository(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def _check_watchlist(path: Path, root: Path) -> None:
    resolved = path.resolve()
    if _inside_repository(resolved, root):
        raise BuildError("The watch-list must live outside the repository")
    sys.path.insert(0, str(root))
    try:
        from nps_v2.watchlist import WatchlistError, load_watchlist

        try:
            if load_watchlist(resolved) is None:
                raise BuildError(f"Watch-list not found: {path}")
        except WatchlistError as error:
            raise BuildError(str(error)) from error
    finally:
        sys.path.remove(str(root))


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Same bytes whether built on Windows (CRLF checkout) or Linux.
    data = source.read_bytes().replace(b"\r\n", b"\n")
    destination.write_bytes(data)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _version(root: Path) -> str:
    for line in (
        (root / PACKAGE / "__init__.py").read_text(encoding="utf-8").splitlines()
    ):
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip("\"'")
    return "unknown"


def _git_commit(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scripts.build_skill")
    parser.add_argument("--out", required=True, help="output folder (e.g. dist/skill)")
    parser.add_argument("--watchlist", help="special-case list kept outside the repo")
    parser.add_argument("--zip", action="store_true", help="also write <name>.zip")
    args = parser.parse_args(argv)
    try:
        target = build(
            Path(args.out),
            watchlist=Path(args.watchlist) if args.watchlist else None,
            make_zip=args.zip,
        )
    except BuildError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
