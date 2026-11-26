"""Capturing connector responses from a synthetic session transcript."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

from nps_v2.capture import capture, connector_results, default_transcript
from nps_v2.run_folder import RunFolder, RunFolderError
from nps_v2.salesforce.queries import Query

RESPONSE = {"totalSize": 0, "done": True, "records": []}


def tool_use(use_id: str, query: str, name: str = "mcp__BTS__salesforce_query") -> dict:
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": use_id,
                    "name": name,
                    "input": {"query": query},
                }
            ]
        },
    }


def tool_result(
    use_id: str, body: Any, *, is_error: bool = False, as_list: bool = True
) -> dict:
    text = body if isinstance(body, str) else json.dumps(body)
    content: Any = [{"type": "text", "text": text}] if as_list else text
    block = {"type": "tool_result", "tool_use_id": use_id, "content": content}
    if is_error:
        block["is_error"] = True
    return {"type": "user", "message": {"content": [block]}}


class CaptureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        self.folder = RunFolder(self.directory / "run")
        self.folder.write_queries(
            "projects",
            [
                Query(name="projects", soql="SELECT Id FROM X WHERE A = 1", limit=10),
                Query(
                    name="projects_control", soql="SELECT COUNT(Id) n FROM X", limit=10
                ),
            ],
        )

    def transcript(self, *entries: dict) -> Path:
        path = self.directory / "session.jsonl"
        lines = [json.dumps(e) for e in entries] + ["not json"]
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def test_saves_matching_results_verbatim(self) -> None:
        newer = {**RESPONSE, "totalSize": 1, "records": [{"Id": "x"}]}
        path = self.transcript(
            tool_use("1", "SELECT  Id FROM X\nWHERE A = 1"),
            tool_result("1", RESPONSE),
            tool_use("2", "SELECT Id FROM X WHERE A = 1"),
            tool_result("2", newer, as_list=False),
            tool_use("3", "SELECT COUNT(Id) n FROM X"),
            tool_result("3", "INVALID_FIELD: boom", is_error=True),
        )
        result = capture(self.folder, "projects", path)
        self.assertEqual(result.captured, ("projects",))
        self.assertEqual(result.missing, ("projects_control",))
        saved = json.loads(
            (self.folder.path / "responses" / "projects.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(saved, newer)

    def test_existing_responses_are_never_overwritten(self) -> None:
        target = self.folder.path / "responses" / "projects.json"
        target.parent.mkdir(parents=True)
        target.write_text('{"keep": true}', encoding="utf-8")
        path = self.transcript(
            tool_use("1", "SELECT Id FROM X WHERE A = 1"), tool_result("1", RESPONSE)
        )
        result = capture(self.folder, "projects", path)
        self.assertEqual(result.already_saved, ("projects",))
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"keep": True})

    def test_ignores_other_tools_and_non_query_payloads(self) -> None:
        path = self.transcript(
            tool_use("1", "SELECT Id FROM X WHERE A = 1", name="mcp__Other__run"),
            tool_result("1", RESPONSE),
            tool_use("2", "SELECT COUNT(Id) n FROM X"),
            tool_result("2", {"message": "no records key"}),
        )
        self.assertEqual(connector_results(path), {})

    def test_default_transcript_is_the_newest(self) -> None:
        projects = self.directory / ".claude" / "projects" / "workspace"
        projects.mkdir(parents=True)
        old, new = projects / "a.jsonl", projects / "b.jsonl"
        old.write_text("", encoding="utf-8")
        new.write_text("", encoding="utf-8")
        past = time.time() - 60
        os.utime(old, (past, past))
        self.assertEqual(default_transcript(self.directory), new)
        with self.assertRaises(RunFolderError):
            default_transcript(self.directory / "nowhere")


if __name__ == "__main__":
    unittest.main()
