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


@dataclass(frozen=True, slots=True)
class ToolCall:
    """One connector call found in the transcript, with its result (if any)."""

    name: str
    input: Mapping[str, Any]
    result_text: str | None
    is_error: bool


def tool_calls(transcript: Path) -> list[ToolCall]:
    """Every tool call of the transcript in order, paired with its result."""
    calls: list[ToolCall] = []
    index: dict[str, int] = {}
    for entry in _entries(transcript):
        for block in _blocks(entry):
            kind = block.get("type")
            if kind == "tool_use":
                raw_input = block.get("input")
                index[str(block.get("id"))] = len(calls)
                calls.append(
                    ToolCall(
                        name=str(block.get("name", "")),
                        input=raw_input if isinstance(raw_input, Mapping) else {},
                        result_text=None,
                        is_error=False,
                    )
                )
            elif kind == "tool_result" and str(block.get("tool_use_id")) in index:
                position = index.pop(str(block["tool_use_id"]))
                call = calls[position]
                calls[position] = ToolCall(
                    name=call.name,
                    input=call.input,
                    result_text=_text(block.get("content")),
                    is_error=bool(block.get("is_error")),
                )
    return calls


def connector_results(transcript: Path) -> dict[str, Any]:
    """Latest successful result per SOQL text found in the transcript."""
    results: dict[str, Any] = {}
    for call in tool_calls(transcript):
        if not call.name.endswith(QUERY_TOOL_SUFFIX) or call.is_error:
            continue
        query = call.input.get("query")
        if not isinstance(query, str) or call.result_text is None:
            continue
        parsed = _parse(call.result_text)
        if parsed is not None:
            results[_normalize(query)] = parsed
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
