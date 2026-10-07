from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.paths import config_path

DEFAULT_SCHEDULE_CONFIG_PATH = (
    config_path("weekly_schedule.json")
)

VALID_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


class ScheduleConfigurationError(Exception):
    """Raised when the weekly schedule configuration is invalid."""


def load_weekly_schedule(
    config_path: Path | str = DEFAULT_SCHEDULE_CONFIG_PATH,
) -> dict[str, Any]:
    path = Path(config_path)

    if not path.exists():
        raise ScheduleConfigurationError(
            f"Schedule configuration file not found: {path}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            configuration = json.load(file)
    except json.JSONDecodeError as exc:
        raise ScheduleConfigurationError(
            f"Invalid JSON in weekly schedule configuration: {exc}"
        ) from exc
    except OSError as exc:
        raise ScheduleConfigurationError(
            f"Could not read weekly schedule configuration: {exc}"
        ) from exc

    schedule = configuration.get("weekly_schedule")

    if not isinstance(schedule, dict):
        raise ScheduleConfigurationError(
            "'weekly_schedule' must be a JSON object."
        )

    execution_weekday = schedule.get("execution_weekday")
    start_offset = schedule.get("window_start_offset_days")
    window_length = schedule.get("window_length_days")

    if execution_weekday not in VALID_WEEKDAYS:
        valid_values = ", ".join(VALID_WEEKDAYS)
        raise ScheduleConfigurationError(
            f"Invalid execution_weekday '{execution_weekday}'. "
            f"Valid values: {valid_values}"
        )

    if not isinstance(start_offset, int) or start_offset < 0:
        raise ScheduleConfigurationError(
            "'window_start_offset_days' must be an integer >= 0."
        )

    if not isinstance(window_length, int) or window_length <= 0:
        raise ScheduleConfigurationError(
            "'window_length_days' must be an integer > 0."
        )

    return {
        "execution_weekday": execution_weekday,
        "execution_weekday_number": VALID_WEEKDAYS[execution_weekday],
        "window_start_offset_days": start_offset,
        "window_length_days": window_length,
    }
