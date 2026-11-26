"""Copies connector responses from the Claude session log into the run folder.

Connector results reach Claude's context, not a file. Instead of asking Claude to
re-type them (error-prone for dozens of records), this reads the session transcript
(``~/.claude/projects/<workspace>/<session>.jsonl``), finds the result of each query
the engine generated (matched by its exact SOQL text) and saves it verbatim.

This depends on the transcript format of the Claude runtime, so it is a convenience,
not a guarantee: control counts still verify every saved response, and Claude can fall
back to saving a response by hand when capture reports it as missing.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nps_v2.run_folder import RunFolder, RunFolderError

QUERY_TOOL_SUFFIX = "salesforce_query"


@dataclass(frozen=True, slots=True)
class CaptureResult:
    captured: tuple[str, ...]
    already_saved: tuple[str, ...]
    missing: tuple[str, ...]


def default_transcript(home: Path | None = None) -> Path:
    """Most recently written session transcript of this machine."""
    root = (home or Path.home()) / ".claude" / "projects"
    candidates = sorted(root.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise RunFolderError(f"No session transcript found under {root}")
    return candidates[-1]


def connector_results(transcript: Path) -> dict[str, Any]:
    """Latest successful result per SOQL text found in the transcript."""
    pending: dict[str, str] = {}
    results: dict[str, Any] = {}
    for entry in _entries(transcript):
        for block in _blocks(entry):
            kind = block.get("type")
            if kind == "tool_use" and str(block.get("name", "")).endswith(
                QUERY_TOOL_SUFFIX
            ):
                query = (block.get("input") or {}).get("query")
                if isinstance(query, str):
                    pending[str(block.get("id"))] = _normalize(query)
            elif kind == "tool_result" and block.get("tool_use_id") in pending:
                soql = pending.pop(str(block["tool_use_id"]))
                if block.get("is_error"):
                    continue
                parsed = _parse(_text(block.get("content")))
                if parsed is not None:
                    results[soql] = parsed
    return results


def capture(folder: RunFolder, group: str, transcript: Path) -> CaptureResult:
    results = connector_results(transcript)
    captured, already, missing = [], [], []
    for query in folder.read_queries(group):
        path = folder.response_path(query)
        if path.exists():
            already.append(query.name)
            continue
        raw = results.get(_normalize(query.soql))
        if raw is None:
            missing.append(query.name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        captured.append(query.name)
    return CaptureResult(tuple(captured), tuple(already), tuple(missing))


def _entries(transcript: Path) -> Iterator[Mapping[str, Any]]:
    try:
        lines = transcript.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RunFolderError(f"Cannot read transcript {transcript}: {error}") from error
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, Mapping):
            yield entry


def _blocks(entry: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    message = entry.get("message")
    content = message.get("content") if isinstance(message, Mapping) else None
    if isinstance(content, list):
        yield from (block for block in content if isinstance(block, Mapping))


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, Mapping) and part.get("type") == "text"
        )
    return ""


def _parse(text: str) -> Any:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, Mapping) and "records" in value else None


def _normalize(soql: str) -> str:
    return " ".join(soql.split())
