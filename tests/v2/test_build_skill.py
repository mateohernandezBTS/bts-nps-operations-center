"""The installable skill: contents, isolation from desktop code and a working CLI."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from scripts.build_skill import (
    BUILD_INFO,
    SKILL_NAME,
    WATCHLIST_TARGET,
    BuildError,
    build,
    main,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DESKTOP_ONLY = ("PySide6", "bs4", "openpyxl", "app", "engine.stages.email_parser")


def run_in_skill(skill: Path, *args: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "PYTHONPATH": str(skill),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return subprocess.run(
        [sys.executable, *args],
        cwd=skill.parent,  # never the repository: imports must come from the skill
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


class BuildSkillTest(unittest.TestCase):
    def setUp(self) -> None:
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        self.skill = build(self.out)

    def files(self) -> set[str]:
        return {
            p.relative_to(self.skill).as_posix()
            for p in self.skill.rglob("*")
            if p.is_file()
        }

    def test_layout(self) -> None:
        files = self.files()
        self.assertEqual(self.skill.name, SKILL_NAME)
        for required in (
            "SKILL.md",
            BUILD_INFO,
            "nps_v2/cli.py",
            "nps_v2/outputs/assets/slack_page.js",
            "nps_v2/outputs/assets/slack_page.css",
            "engine/stages/business_rules.py",
            "engine/slack_canvas_renderer.py",
            "config/business_rules.json",
            "config/v2/countries.json",
        ):
            with self.subTest(file=required):
                self.assertIn(required, files)
        self.assertFalse(
            any(
                f.startswith(("app/", "tests/", "packaging/", "documentation/"))
                for f in files
            )
        )
        self.assertNotIn("engine/stages/email_parser.py", files)
        self.assertNotIn(WATCHLIST_TARGET, files)
        self.assertFalse(any("__pycache__" in f for f in files))

    def test_skill_md_frontmatter(self) -> None:
        text = (self.skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith(f"---\nname: {SKILL_NAME}\ndescription: "))
        description = text.split("description: ", 1)[1].split("\n", 1)[0]
        self.assertLess(len(description), 1024)
        self.assertNotIn("<", description)

    def test_build_info_hashes_every_file(self) -> None:
        info = json.loads((self.skill / BUILD_INFO).read_text(encoding="utf-8"))
        self.assertFalse(info["watchlist_installed"])
        self.assertEqual(set(info["files"]), self.files() - {BUILD_INFO})

    def test_runs_without_desktop_dependencies(self) -> None:
        probe = (
            "import sys, nps_v2.cli, nps_v2.outputs.writer, nps_v2.capture; "
            "print(nps_v2.cli.__file__); "
            f"print(','.join(m for m in {DESKTOP_ONLY!r} if m in sys.modules))"
        )
        result = run_in_skill(self.skill, "-c", probe)
        self.assertEqual(result.returncode, 0, result.stderr)
        location, loaded = result.stdout.splitlines()
        self.assertTrue(Path(location).is_relative_to(self.skill))
        self.assertEqual(loaded, "")

    def test_cli_works_from_the_skill(self) -> None:
        run = self.out / "run"
        result = run_in_skill(
            self.skill,
            "-m",
            "nps_v2",
            "select",
            "--run",
            str(run),
            "--day",
            "2026-11-26",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "ok")
        self.assertTrue((run / "queries.json").exists())

    def test_rebuild_replaces_previous_output(self) -> None:
        (self.skill / "stale.txt").write_text("x", encoding="utf-8")
        rebuilt = build(self.out)
        self.assertFalse((rebuilt / "stale.txt").exists())


class SkillFrontmatterTest(unittest.TestCase):
    """claude.ai rejects an upload whose name or description exceeds its limits."""

    def test_name_and_description_fit_the_upload_limits(self) -> None:
        text = (REPOSITORY_ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(match)
        assert match is not None
        fields = dict(
            line.split(": ", 1) for line in match.group(1).splitlines() if ": " in line
        )
        self.assertEqual(fields["name"], SKILL_NAME)  # must match the zip folder
        self.assertLessEqual(len(fields["name"]), 64)
        self.assertLessEqual(len(fields["description"]), 200)

    def test_outputs_are_delivered_as_files_not_pasted(self) -> None:
        text = (REPOSITORY_ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Never paste the page's HTML", text)


class WatchlistAndZipTest(unittest.TestCase):
    def setUp(self) -> None:
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        self.outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.outside)
        if self.outside.resolve().is_relative_to(REPOSITORY_ROOT):
            # Some sandboxes point TMP/TEMP inside the repository. Then only this temp
            # folder counts as "outside"; every other path, including the repository
            # files used by test_watchlist_inside_the_repository_is_rejected, does not.
            outside = self.outside.resolve()
            patcher = mock.patch(
                "scripts.build_skill._inside_repository",
                side_effect=lambda path, root: not path.is_relative_to(outside),
            )
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_watchlist_from_outside_the_repository_is_installed(self) -> None:
        watchlist = self.outside / "watchlist.json"
        watchlist.write_text('{"facilitators": ["Example Person"]}', encoding="utf-8")
        skill = build(self.out, watchlist=watchlist, make_zip=True)
        self.assertTrue((skill / WATCHLIST_TARGET).exists())
        info = json.loads((skill / BUILD_INFO).read_text(encoding="utf-8"))
        self.assertTrue(info["watchlist_installed"])
        with zipfile.ZipFile(self.out / f"{SKILL_NAME}.zip") as bundle:
            names = bundle.namelist()
        self.assertIn(f"{SKILL_NAME}/SKILL.md", names)
        self.assertIn(f"{SKILL_NAME}/{WATCHLIST_TARGET}", names)

    def test_watchlist_inside_the_repository_is_rejected(self) -> None:
        inside = REPOSITORY_ROOT / "config" / "v2" / "watchlist.example.json"
        with self.assertRaisesRegex(BuildError, "outside the repository"):
            build(self.out, watchlist=inside)

    def test_invalid_watchlist_is_rejected(self) -> None:
        bad = self.outside / "watchlist.json"
        bad.write_text('{"facilitators": [""]}', encoding="utf-8")
        with self.assertRaises(BuildError):
            build(self.out, watchlist=bad)
        self.assertEqual(
            main(["--out", str(self.out), "--watchlist", str(self.outside / "none")]),
            2,
        )


if __name__ == "__main__":
    unittest.main()
