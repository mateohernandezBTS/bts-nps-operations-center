from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.paths import config_path

DEFAULT_CONFIG_PATH = config_path("report_sources.json")


class SourceConfigurationError(Exception):
    """Raised when the report source configuration is invalid."""


def load_source_configuration(
    config_path: Path | str = DEFAULT_CONFIG_PATH,
) -> dict[str, Any]:
    """
    Load and validate the report source configuration.

    Args:
        config_path:
            Path to report_sources.json.

    Returns:
        Validated configuration dictionary.

    Raises:
        SourceConfigurationError:
            If the file does not exist, contains invalid JSON,
            or fails structural validation.
    """
    path = Path(config_path)

    if not path.exists():
        raise SourceConfigurationError(
            f"Source configuration file not found: {path}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            configuration = json.load(file)
    except json.JSONDecodeError as exc:
        raise SourceConfigurationError(
            f"Invalid JSON in source configuration: {exc}"
        ) from exc
    except OSError as exc:
        raise SourceConfigurationError(
            f"Could not read source configuration: {exc}"
        ) from exc

    validate_source_configuration(configuration)

    return configuration


def validate_source_configuration(
    configuration: dict[str, Any],
) -> None:
    """
    Validate the minimum structure and uniqueness rules.
    """
    if not isinstance(configuration, dict):
        raise SourceConfigurationError(
            "The source configuration must be a JSON object."
        )

    source_groups = configuration.get("source_groups")

    if not isinstance(source_groups, dict) or not source_groups:
        raise SourceConfigurationError(
            "'source_groups' must be a non-empty object."
        )

    source_ids: set[str] = set()

    for group_id, group in source_groups.items():
        if not isinstance(group, dict):
            raise SourceConfigurationError(
                f"Source group '{group_id}' must be an object."
            )

        sources = group.get("sources")

        if not isinstance(sources, list):
            raise SourceConfigurationError(
                f"Source group '{group_id}' must contain a sources list."
            )

        for index, source in enumerate(sources, start=1):
            if not isinstance(source, dict):
                raise SourceConfigurationError(
                    f"Source {index} in '{group_id}' must be an object."
                )

            required_fields = {
                "source_id",
                "enabled",
                "country",
                "report_type",
                "required",
            }

            missing_fields = required_fields.difference(source)

            if missing_fields:
                missing = ", ".join(sorted(missing_fields))
                raise SourceConfigurationError(
                    f"Source {index} in '{group_id}' is missing: {missing}"
                )

            source_id = source["source_id"]

            if not isinstance(source_id, str) or not source_id.strip():
                raise SourceConfigurationError(
                    f"Invalid source_id in group '{group_id}'."
                )

            if source_id in source_ids:
                raise SourceConfigurationError(
                    f"Duplicate source_id detected: {source_id}"
                )

            source_ids.add(source_id)


def get_enabled_sources(
    group_id: str,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
) -> list[dict[str, Any]]:
    """
    Return all enabled sources for a source group.
    """
    configuration = load_source_configuration(config_path)
    source_groups = configuration["source_groups"]

    if group_id not in source_groups:
        raise SourceConfigurationError(
            f"Unknown source group: {group_id}"
        )

    group = source_groups[group_id]

    if not group.get("enabled", False):
        return []

    return [
        source
        for source in group["sources"]
        if source.get("enabled", False)
    ]


def get_required_sources(
    group_id: str,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
) -> list[dict[str, Any]]:
    """
    Return enabled sources that are required for completion.
    """
    return [
        source
        for source in get_enabled_sources(group_id, config_path)
        if source.get("required", False)
    ]
