from collections import defaultdict
from datetime import datetime


SLACK_COLUMNS = [
    "Session",
    "Date",
    "Facilitator",
    "QR-Code",
    "Link NPS Survey",
    "Link Insights Facilitators",
    "Results",
    "Link for Results",
]


def clean_text(value) -> str:
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def parse_salesforce_date(value: str) -> datetime:
    return datetime.strptime(
        clean_text(value),
        "%m/%d/%Y",
    )


def markdown_escape(value: str) -> str:
    return clean_text(value).replace("|", r"\|")


def build_markdown_link(
    url: str,
    display_text: str,
) -> str:
    cleaned_url = clean_text(url)

    if not cleaned_url:
        return ""

    return (
        f"[{markdown_escape(display_text)}]"
        f"({cleaned_url})"
    )


def create_operational_record(
    record: dict,
) -> dict:
    return {
        column: clean_text(
            record.get(column, "")
        )
        for column in SLACK_COLUMNS
    }


def sort_worklist_records(
    records: list[dict],
) -> list[dict]:
    return sorted(
        records,
        key=lambda record: (
            clean_text(
                record.get("Client", "")
            ).casefold(),
            parse_salesforce_date(
                record.get("Date", "")
            ),
            clean_text(
                record.get("Session", "")
            ).casefold(),
        ),
    )


def count_by_client(
    records: list[dict],
) -> dict[str, int]:
    counts = defaultdict(int)

    for record in records:
        client = (
            clean_text(
                record.get("Client", "")
            )
            or "Cliente sin identificar"
        )

        counts[client] += 1

    return dict(counts)


def generate_markdown(
    records: list[dict],
    config: dict,
    country: str,
    window_start: str,
    window_end: str,
) -> str:
    slack_config = config.get(
        "slack_output",
        {},
    )

    empty_display = slack_config.get(
        "empty_display",
        "",
    )

    link_text = clean_text(
        slack_config.get(
            "results_link_text",
            "Home",
        )
    )

    grouped_records = defaultdict(list)

    for record in records:
        client = (
            clean_text(
                record.get("Client", "")
            )
            or "Cliente sin identificar"
        )

        grouped_records[client].append(
            record
        )

    lines = []

    if slack_config.get(
        "include_weekly_heading",
        True,
    ):
        template = slack_config.get(
            "weekly_heading_template",
            (
                "Upcoming NPS | {country} | "
                "{window_start} to {window_end}"
            ),
        )

        heading = template.format(
            country=country,
            window_start=window_start,
            window_end=window_end,
        )

        lines.append(f"# {heading}")
        lines.append("")

    lines.append(
        f"Total de sesiones: {len(records)}"
    )

    lines.append("")

    for client in sorted(
        grouped_records,
        key=str.casefold,
    ):
        client_records = sorted(
            grouped_records[client],
            key=lambda record: (
                parse_salesforce_date(
                    record.get(
                        "Date",
                        "",
                    )
                ),
                clean_text(
                    record.get(
                        "Session",
                        "",
                    )
                ).casefold(),
            ),
        )

        lines.append(
            f"## {markdown_escape(client)}"
        )

        lines.append("")

        lines.append(
            "| Session | Date | Facilitator | QR-Code | "
            "Link NPS Survey | Link Insights Facilitators | "
            "Results | Link for Results |"
        )

        lines.append(
            "|---|---|---|---|---|---|---|---|"
        )

        for record in client_records:
            facilitator = (
                record.get("Facilitator", "")
                or empty_display
            )

            lines.append(
                "| "
                f"{markdown_escape(record.get('Session', ''))} | "
                f"{markdown_escape(record.get('Date', ''))} | "
                f"{markdown_escape(facilitator)} | "
                f"{markdown_escape(record.get('QR-Code', ''))} | "
                f"{markdown_escape(record.get('Link NPS Survey', ''))} | "
                f"{markdown_escape(record.get('Link Insights Facilitators', ''))} | "
                f"{markdown_escape(record.get('Results', ''))} | "
                f"{build_markdown_link(record.get('Link for Results', ''), link_text)} |"
            )

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def generate_slack_output(
    worklist_records: list[dict],
    config: dict,
    country: str,
    window_start: str,
    window_end: str,
) -> dict:
    ready_records = [
        record
        for record in worklist_records
        if record.get("Output Status")
        == "READY"
    ]

    sorted_records = sort_worklist_records(
        ready_records
    )

    markdown = generate_markdown(
        records=sorted_records,
        config=config,
        country=country,
        window_start=window_start,
        window_end=window_end,
    )

    summary = count_by_client(
        sorted_records
    )

    operational_records = [
        create_operational_record(record)
        for record in sorted_records
    ]

    return {
        "records": operational_records,
        "markdown": markdown,
        "summary_by_client": summary,
    }