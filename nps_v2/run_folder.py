"""Layout and file I/O of a run folder.

```text
<run>/
  selection.json          what was asked
  queries.json            every query the engine generated (Claude runs them verbatim)
  responses/<name>.json   raw connector responses, saved by Claude
  report.json, preview.md, slack/   outputs
```
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nps_v2.salesforce.queries import Query
from nps_v2.selection import Selection

SELECTION_FILE = "selection.json"
QUERIES_FILE = "queries.json"
RESPONSES_DIRECTORY = "responses"


class RunFolderError(ValueError):
    """The run folder is missing something the current step needs."""


@dataclass(frozen=True, slots=True)
class RunFolder:
    path: Path

    def response_path(self, query: Query) -> Path:
        return self.path / RESPONSES_DIRECTORY / f"{query.name}.json"

    # --- selection -------------------------------------------------------------
    def write_selection(self, selection: Selection) -> None:
        self._write_json(self.path / SELECTION_FILE, selection.to_dict())

    def read_selection(self) -> Selection:
        return Selection.from_dict(self._read_json(self.path / SELECTION_FILE))

    # --- queries ---------------------------------------------------------------
    def write_queries(self, group: str, queries: Sequence[Query]) -> None:
        path = self.path / QUERIES_FILE
        manifest = self._read_json(path) if path.exists() else {}
        manifest[group] = [
            {"name": q.name, "soql": q.soql, "limit": q.limit, "save_as": self._rel(q)}
            for q in queries
        ]
        self._write_json(path, manifest)

    def read_queries(self, group: str) -> list[Query]:
        manifest = self._read_json(self.path / QUERIES_FILE)
        if group not in manifest:
            raise RunFolderError(f"{QUERIES_FILE} has no '{group}' queries yet")
        try:
            return [
                Query(name=item["name"], soql=item["soql"], limit=int(item["limit"]))
                for item in manifest[group]
            ]
        except (KeyError, TypeError, ValueError) as error:
            raise RunFolderError(f"Invalid {QUERIES_FILE}: {error}") from error

    # --- responses -------------------------------------------------------------
    def read_response(self, query: Query) -> Any:
        path = self.response_path(query)
        if not path.exists():
            raise RunFolderError(
                f"Missing response for {query.name}: save the connector output "
                f"of that query to {self._rel(query)}"
            )
        return self._read_json(path)

    # --- helpers ---------------------------------------------------------------
    def _rel(self, query: Query) -> str:
        return f"{RESPONSES_DIRECTORY}/{query.name}.json"

    def _read_json(self, path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise RunFolderError(f"Missing {path.relative_to(self.path)}") from None
        except json.JSONDecodeError as error:
            raise RunFolderError(
                f"{path.relative_to(self.path)} is not JSON: {error}"
            ) from error

    def _write_json(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
