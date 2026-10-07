from __future__ import annotations

import json
import traceback as traceback_module
from datetime import datetime
from pathlib import Path
from typing import Any

from engine.paths import data_path, test_data_path


APPLICATION_ERROR_LOG = "application_errors.jsonl"


def operational_log_root(
    environment: str,
) -> Path:
    """Return the persistent operational log root."""
    if environment.strip().upper() == "TEST":
        return test_data_path("logs")

    return data_path("logs")


def persist_application_error(
    *,
    environment: str,
    component: str,
    operation: str,
    error: BaseException,
    traceback_text: str | None = None,
) -> None:
    """
    Append one unexpected application error record.

    Logging is best-effort by design; failures here must not replace the
    original UI/backend error behavior.
    """
    record = {
        "timestamp": _timestamp(),
        "environment": _normalize_environment(environment),
        "component": component,
        "operation": operation,
        "error_type": type(error).__name__,
        "message": str(error),
        "traceback": (
            traceback_text
            if traceback_text is not None
            else "".join(
                traceback_module.format_exception(
                    type(error),
                    error,
                    error.__traceback__,
                )
            )
        ),
    }

    try:
        log_path = (
            operational_log_root(environment)
            / APPLICATION_ERROR_LOG
        )
        log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        with log_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    default=str,
                )
            )
            file.write("\n")
    except Exception:
        return


def persist_preflight_result(
    preflight: dict[str, Any],
) -> None:
    """
    Persist a durable preflight history record.

    The caller supplies the structured backend result; this function does
    not recalculate readiness or business rules.
    """
    environment = _normalize_environment(
        str(
            preflight.get(
                "environment",
                "PRODUCTION",
            )
        )
    )
    timestamp = _timestamp()

    record = {
        "timestamp": timestamp,
        "environment": environment,
        "reference_date": preflight.get("reference_date", ""),
        "status": preflight.get("status", ""),
        "expected_sources": preflight.get("inventory", {}),
        "source_inventory": preflight.get("inventory", {}),
        "issues": preflight.get("issues", []),
        "metrics": _preflight_metrics(preflight),
    }

    safe_name = (
        timestamp.replace(":", "")
        .replace("-", "")
        .replace(".", "")
    )
    status = str(record["status"] or "UNKNOWN").upper()

    try:
        log_directory = (
            operational_log_root(environment)
            / "preflight"
        )
        log_directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        log_path = (
            log_directory
            / f"{safe_name}_{status}.json"
        )
        with log_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                record,
                file,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
    except Exception:
        return


def _preflight_metrics(
    preflight: dict[str, Any],
) -> dict[str, Any]:
    inventory = preflight.get("inventory", {})

    if not isinstance(inventory, dict):
        return {}

    return {
        "files_scanned": inventory.get("files_scanned", 0),
        "matched_files": inventory.get("matched_files", 0),
        "review_files": inventory.get("review_files", 0),
        "unknown_reports": inventory.get(
            "unconfigured_files",
            0,
        ),
        "duplicate_sources": inventory.get(
            "duplicate_sources",
            0,
        ),
        "missing_required_sources": inventory.get(
            "missing_required_sources",
            0,
        ),
    }


def _normalize_environment(
    environment: str,
) -> str:
    return (
        environment
        if environment.strip().upper() == "TEST"
        else "PRODUCTION"
    )


def _timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")
