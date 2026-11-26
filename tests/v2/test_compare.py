"""Parallel run comparison with the desktop selam_worklist.csv."""

from __future__ import annotations

import csv
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

from nps_v2.cli import EXIT_ERROR, main
from nps_v2.compare import CompareError, compare, read_desktop_ready, render_comparison
from tests.v2.synthetic import scenario

COLUMNS = ["Client", "Country", "Session", "Project ID", "Output Status"]


def write_desktop(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def desktop_row(project_id: str, session: str, status: str = "READY") -> dict[str, str]:
    return {
        "Client": "Synthetic Client",
        "Country": "Argentina",
        "Session": session,
        "Project ID": project_id,
        "Output Status": status,
    }


class CompareTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        self.report = scenario().report
        ready = [*self.report["pending"], *self.report["complete"]]
        self.ready_ids = [row["project_id"] for row in ready]

    def test_identical_lists(self) -> None:
        desktop = write_desktop(
            self.directory / "selam_worklist.csv",
            [desktop_row(pid[:15], f"S{n}") for n, pid in enumerate(self.ready_ids)],
        )
        result = compare(self.report, read_desktop_ready(desktop))
        self.assertEqual(
            (result.matching, result.unexplained), (len(self.ready_ids), 0)
        )
        self.assertEqual((result.only_desktop, result.only_v2), ((), ()))

    def test_differences_are_classified(self) -> None:
        excluded_id = self.report["excluded"][0]["project_id"]
        rows = [desktop_row(pid, "S") for pid in self.ready_ids[1:]]
        rows += [
            desktop_row(excluded_id, "Excluded in V2"),
            desktop_row("a0gAA0000000999AAA", "Deleted later"),
            desktop_row("a0gAA0000000998AAA", "Review row", status="REVIEW"),
        ]
        desktop = write_desktop(self.directory / "selam_worklist.csv", rows)
        result = compare(self.report, read_desktop_ready(desktop))

        self.assertEqual(result.matching, len(self.ready_ids) - 1)
        explanations = {d.session: d.explanation for d in result.only_desktop}
        self.assertTrue(
            explanations["Excluded in V2"].startswith(
                "V2: excluido por reglas: Status Prelim"
            )
        )
        self.assertIn("No está en Salesforce", explanations["Deleted later"])
        self.assertNotIn("Review row", explanations)
        (only_v2,) = result.only_v2
        self.assertEqual(only_v2.explanation, "")
        self.assertEqual(result.unexplained, 1)

        markdown = render_comparison(
            result, run_id="V2-X", desktop_name="selam_worklist.csv"
        )
        self.assertIn("| Coinciden | 3 |", markdown)
        self.assertIn("A revisar", markdown)

    def test_invalid_desktop_files(self) -> None:
        no_id = self.directory / "no_id.csv"
        no_id.write_text("Client,Session\nA,B\n", encoding="utf-8")
        bad_id = write_desktop(self.directory / "bad.csv", [desktop_row("nope", "S")])
        for path in (no_id, bad_id, self.directory / "missing.csv"):
            with self.subTest(path=path.name):
                with self.assertRaises(CompareError):
                    read_desktop_ready(path)


class CompareCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        self.run_dir = self.directory / "run"
        self.run_dir.mkdir()

    def cli(self, *argv: str) -> tuple[int, dict[str, Any]]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(list(argv))
        return code, json.loads(buffer.getvalue())

    def test_writes_outputs(self) -> None:
        report = scenario().report
        (self.run_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
        desktop = write_desktop(self.directory / "selam_worklist.csv", [])
        code, out = self.cli(
            "compare", "--run", str(self.run_dir), "--desktop", str(desktop)
        )
        self.assertEqual(code, 0, out)
        self.assertEqual(
            out["only_v2"], len(report["pending"]) + len(report["complete"])
        )
        self.assertTrue((self.run_dir / "compare.md").exists())
        self.assertTrue((self.run_dir / "compare.json").exists())

    def test_requires_a_report(self) -> None:
        code, out = self.cli(
            "compare",
            "--run",
            str(self.run_dir),
            "--desktop",
            str(self.directory / "x.csv"),
        )
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("run 'upcoming' first", out["message"])


if __name__ == "__main__":
    unittest.main()
