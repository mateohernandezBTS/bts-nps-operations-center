"""Strict reading of connector results for the creation steps.

The connector answers with JSON text in every case seen so far. Writes are read
strictly: an unexpected answer stops the run (``ResponseError``), and ``reconcile``
always verifies what really exists afterwards.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


class ResponseError(ValueError):
    """A connector result does not look as expected; the run must stop."""


def json_object(text: str | None) -> dict[str, Any]:
    if text is None:
        raise ResponseError("The tool call has no result yet")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise ResponseError(f"The result is not JSON: {text[:200]!r}") from error
    if not isinstance(value, dict):
        raise ResponseError(f"The result is not a JSON object: {text[:200]!r}")
    return value


def created_id(text: str | None, prefix: str) -> str:
    """Id of a created record (18 characters, expected key prefix)."""
    if text is None:
        raise ResponseError("The create call has no result yet")
    try:
        value = json_object(text)
    except ResponseError:
        value = None
    if value is not None:
        if value.get("success") is False or value.get("errors"):
            raise ResponseError(f"Salesforce rejected the create: {text[:300]!r}")
        found = {str(value.get(k)) for k in ("id", "Id") if value.get(k)}
    else:
        # Not JSON: accept exactly one 18-character Id with the expected prefix.
        found = set(re.findall(rf"\b{re.escape(prefix)}[A-Za-z0-9]{{15}}\b", text))
    if len(found) != 1:
        raise ResponseError(f"Cannot find the created Id in: {text[:300]!r}")
    record_id = found.pop()
    if not re.fullmatch(rf"{re.escape(prefix)}[A-Za-z0-9]{{15}}", record_id):
        raise ResponseError(
            f"Created Id {record_id!r} is not an 18-character {prefix}… Id"
        )
    return record_id


def update_ok(text: str | None) -> None:
    if text is None:
        raise ResponseError("The update call has no result yet")
    try:
        value = json_object(text)
    except ResponseError:
        lowered = text.casefold()
        if "success" in lowered and "error" not in lowered:
            return
        raise ResponseError(f"Unexpected update result: {text[:300]!r}") from None
    if value.get("success") is False or value.get("errors"):
        raise ResponseError(f"Salesforce rejected the update: {text[:300]!r}")


def query_records(text: str | None) -> list[dict[str, Any]]:
    value = json_object(text)
    records = value.get("records")
    if value.get("done") is not True or not isinstance(records, list):
        raise ResponseError("The query result is incomplete (done is not true)")
    if not all(isinstance(r, dict) for r in records):
        raise ResponseError("The query result has invalid records")
    return list(records)


def describe_problems(
    text: str | None, *, needs: str, fields: Sequence[str]
) -> list[str]:
    """Permission problems for the connector's user; ``needs``: create or update."""
    value = json_object(text)
    name = value.get("name", "object")
    flag = "createable" if needs == "create" else "updateable"
    problems = []
    if value.get(flag) is not True:
        problems.append(f"{name} is not {flag} for this user")
    described = {
        str(f.get("name")): f for f in value.get("fields", []) if isinstance(f, Mapping)
    }
    for field in fields:
        info = described.get(field)
        if info is not None and info.get(flag) is not True:
            problems.append(f"{name}.{field} is not {flag} for this user")
    return problems
