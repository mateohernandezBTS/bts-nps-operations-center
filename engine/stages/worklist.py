from datetime import datetime, timedelta
from pathlib import Path
import json
import re
from urllib.parse import unquote, urlparse

from engine.paths import config_path


CONFIG_FILE = (
    config_path("operational_output.json")
)


SALESFORCE_ID_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z0-9]{15}|[A-Za-z0-9]{18})(?![A-Za-z0-9])"
)


def clean_text(value) -> str:
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def load_json(path: Path) -> dict:
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def load_operational_config() -> dict:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            "No se encontró la configuración:\n"
            f"{CONFIG_FILE}"
        )

    return load_json(CONFIG_FILE)


def parse_salesforce_date(value: str) -> datetime:
    cleaned_value = clean_text(value)

    if not cleaned_value:
        raise ValueError("Fecha vacía")

    return datetime.strptime(
        cleaned_value,
        "%m/%d/%Y",
    )


def format_salesforce_date(value: datetime) -> str:
    return (
        f"{value.month}/"
        f"{value.day}/"
        f"{value.year}"
    )


def calculate_weekly_window(
    config: dict,
    reference_monday: str | None = None,
) -> tuple[datetime, datetime]:
    weekly_config = config.get(
        "weekly_window",
        {},
    )

    configured_reference = (
        reference_monday
        or weekly_config.get(
            "reference_monday",
            "",
        )
    )

    monday = parse_salesforce_date(
        configured_reference
    )

    start_offset = int(
        weekly_config.get(
            "start_offset_days",
            1,
        )
    )

    end_offset = int(
        weekly_config.get(
            "end_offset_days",
            7,
        )
    )

    return (
        monday + timedelta(days=start_offset),
        monday + timedelta(days=end_offset),
    )


def filter_weekly_records(
    records: list[dict],
    config: dict,
    reference_monday: str | None = None,
) -> dict:
    weekly_config = config.get(
        "weekly_window",
        {},
    )

    if not weekly_config.get(
        "enabled",
        True,
    ):
        return {
            "in_window": list(records),
            "outside_window": [],
            "window_start": None,
            "window_end": None,
        }

    (
        window_start,
        window_end,
    ) = calculate_weekly_window(
        config=config,
        reference_monday=reference_monday,
    )

    in_window = []
    outside_window = []

    for record in records:
        record_date = parse_salesforce_date(
            record.get(
                "start_date",
                "",
            )
        )

        if (
            window_start
            <= record_date
            <= window_end
        ):
            in_window.append(record)

        else:
            outside_record = dict(record)

            outside_record.update(
                {
                    "window_start": format_salesforce_date(
                        window_start
                    ),
                    "window_end": format_salesforce_date(
                        window_end
                    ),
                    "window_reason": (
                        "Fecha fuera de la ventana semanal"
                    ),
                }
            )

            outside_window.append(
                outside_record
            )

    return {
        "in_window": in_window,
        "outside_window": outside_window,
        "window_start": window_start,
        "window_end": window_end,
    }


def normalize_facilitators(
    value: str,
    config: dict,
) -> str:
    facilitator_config = config.get(
        "facilitators",
        {},
    )

    separator = facilitator_config.get(
        "separator",
        ",",
    )

    empty_values = {
        clean_text(item).casefold()
        for item in facilitator_config.get(
            "empty_values",
            [],
        )
    }

    cleaned_value = clean_text(value)

    if cleaned_value.casefold() in empty_values:
        return ""

    unique_facilitators = []
    seen = set()

    for item in cleaned_value.split(
        separator
    ):
        facilitator = clean_text(item)

        if (
            facilitator.casefold()
            in empty_values
        ):
            continue

        matching_key = (
            facilitator.casefold()
        )

        if matching_key in seen:
            continue

        seen.add(matching_key)

        unique_facilitators.append(
            facilitator
        )

    return separator.join(
        unique_facilitators
    )


def extract_salesforce_id(
    project_url: str,
) -> str:
    cleaned_url = clean_text(
        project_url
    )

    if not cleaned_url:
        return ""

    decoded_url = unquote(
        cleaned_url
    )

    parsed_url = urlparse(
        decoded_url
    )

    path_segments = [
        segment
        for segment in parsed_url.path.split("/")
        if segment
    ]

    for segment in reversed(
        path_segments
    ):
        if re.fullmatch(
            r"[A-Za-z0-9]{15}|[A-Za-z0-9]{18}",
            segment,
        ):
            return segment

    match = SALESFORCE_ID_PATTERN.search(
        decoded_url
    )

    if match:
        return match.group(1)

    return ""


def build_results_link(
    project_id: str,
    config: dict,
) -> str:
    if not project_id:
        return ""

    base_url = clean_text(
        config.get(
            "results",
            {},
        ).get(
            "base_url",
            "",
        )
    )

    return f"{base_url}{project_id}"


def create_worklist_record(
    source_record: dict,
    config: dict,
) -> dict:
    issues = []

    project_url = clean_text(
        source_record.get(
            "project_url",
            "",
        )
    )

    project_id = extract_salesforce_id(
        project_url
    )

    if not project_id:
        issues.append(
            "No se pudo extraer Project ID desde Project URL"
        )

    session = clean_text(
        source_record.get(
            "project_name",
            "",
        )
    )

    date = clean_text(
        source_record.get(
            "start_date",
            "",
        )
    )

    facilitator = normalize_facilitators(
        value=source_record.get(
            "all_staffings",
            "",
        ),
        config=config,
    )

    if not session:
        issues.append(
            "Session vacío"
        )

    if not date:
        issues.append(
            "Date vacío"
        )

    defaults = config.get(
        "defaults",
        {},
    )

    results_config = config.get(
        "results",
        {},
    )

    return {
        "Session": session,
        "Date": date,
        "Facilitator": facilitator,
        "QR-Code": clean_text(
            defaults.get(
                "qr_code",
                "",
            )
        ),
        "Link NPS Survey": clean_text(
            defaults.get(
                "nps_survey_link",
                "",
            )
        ),
        "Link Insights Facilitators": clean_text(
            defaults.get(
                "facilitator_insights_link",
                "",
            )
        ),
        "Results": clean_text(
            results_config.get(
                "default_status",
                "NO",
            )
        ),
        "Link for Results": build_results_link(
            project_id=project_id,
            config=config,
        ),
        "Project ID": project_id,
        "Client": clean_text(
            source_record.get(
                "client_name",
                "",
            )
        ),
        "Project URL": project_url,
        "Output Status": (
            "READY"
            if not issues
            else "REVIEW"
        ),
        "Output Issues": " | ".join(
            issues
        ),
    }


def generate_worklist(
    eligible_records: list[dict],
    config: dict | None = None,
    reference_monday: str | None = None,
) -> dict:
    if config is None:
        config = load_operational_config()

    weekly_result = filter_weekly_records(
        records=eligible_records,
        config=config,
        reference_monday=reference_monday,
    )

    worklist = [
        create_worklist_record(
            source_record=record,
            config=config,
        )
        for record in weekly_result[
            "in_window"
        ]
    ]

    ready = [
        record
        for record in worklist
        if (
            record["Output Status"]
            == "READY"
        )
    ]

    review = [
        record
        for record in worklist
        if (
            record["Output Status"]
            == "REVIEW"
        )
    ]

    return {
        "worklist": worklist,
        "ready": ready,
        "review": review,
        "outside_window": weekly_result[
            "outside_window"
        ],
        "window_start": weekly_result[
            "window_start"
        ],
        "window_end": weekly_result[
            "window_end"
        ],
    }
