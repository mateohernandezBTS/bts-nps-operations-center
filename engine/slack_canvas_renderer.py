from __future__ import annotations

import csv
import hashlib
import html
import json
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


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


COUNTRY_ORDER = {
    "ARGENTINA": 1,
    "BRAZIL / NEXO": 2,
    "MEXICO": 3,
}


SPECIAL_EMAIL_NAMES = (
    "mariano sioli",
    "mariano scioli",
    "maider",
)


def clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value).split()
    ).strip()


def normalize_for_matching(
    value: Any,
) -> str:
    text = clean_text(
        value
    ).casefold()

    normalized = unicodedata.normalize(
        "NFKD",
        text,
    )

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(
            character
        )
    )


def load_csv_records(
    file_path: Path,
) -> list[dict[str, str]]:
    if not file_path.exists():
        raise FileNotFoundError(
            "Worklist file does not exist: "
            f"{file_path}"
        )

    with file_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def get_billing_office(
    record: dict[str, str],
) -> str:
    possible_columns = (
        "Billing Office",
        "Billing_Office",
        "billing_office",
        "BillingOffice",
        "Office",
        "office",
        "Source Office",
        "source_office",
    )

    for column in possible_columns:
        value = clean_text(
            record.get(
                column,
                "",
            )
        )

        if value:
            return value

    country = clean_text(
        record.get(
            "Country",
            "",
        )
    )

    if country:
        return country

    return "[OFFICE NOT PROVIDED]"


def get_country_group(
    record: dict[str, str],
) -> str:
    country = normalize_for_matching(
        record.get(
            "Country",
            "",
        )
    )

    office = normalize_for_matching(
        get_billing_office(
            record
        )
    )

    if (
        country in {
            "brazil",
            "brasil",
            "nexo",
        }
        or office in {
            "brazil",
            "brasil",
            "nexo",
        }
    ):
        return "BRAZIL / NEXO"

    if country == "argentina":
        return "ARGENTINA"

    if country == "mexico":
        return "MEXICO"

    original_country = clean_text(
        record.get(
            "Country",
            "",
        )
    )

    if original_country:
        return original_country.upper()

    return "[COUNTRY NOT PROVIDED]"


def normalize_office_label(
    office: str,
) -> str:
    normalized = normalize_for_matching(
        office
    )

    if normalized in {
        "brazil",
        "brasil",
    }:
        return "Brazil"

    if normalized == "nexo":
        return "Nexo"

    if normalized == "mexico":
        return "Mexico"

    if normalized == "argentina":
        return "Argentina"

    return clean_text(
        office
    ) or "[OFFICE NOT PROVIDED]"


def group_records(
    records: list[dict[str, str]],
) -> dict[
    str,
    dict[
        str,
        dict[
            str,
            list[dict[str, str]],
        ],
    ],
]:
    grouped = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(list)
        )
    )

    for record in records:
        country_group = get_country_group(
            record
        )

        office = normalize_office_label(
            get_billing_office(
                record
            )
        )

        client = clean_text(
            record.get(
                "Client",
                "",
            )
        ) or "[CLIENT NOT PROVIDED]"

        grouped[
            country_group
        ][
            office
        ][
            client
        ].append(
            record
        )

    return {
        country_group: {
            office: dict(
                clients
            )
            for office, clients
            in offices.items()
        }
        for country_group, offices
        in grouped.items()
    }


def count_client_records(
    records: list[dict[str, str]],
) -> int:
    return len(
        records
    )


def count_office_records(
    clients: dict[
        str,
        list[dict[str, str]],
    ],
) -> int:
    return sum(
        len(records)
        for records in clients.values()
    )


def count_country_records(
    offices: dict[
        str,
        dict[
            str,
            list[dict[str, str]],
        ],
    ],
) -> int:
    return sum(
        count_office_records(
            clients
        )
        for clients in offices.values()
    )


def build_summary_data(
    grouped: dict[
        str,
        dict[
            str,
            dict[
                str,
                list[dict[str, str]],
            ],
        ],
    ],
) -> dict[str, Any]:
    country_totals = {}
    office_totals = {}

    for country_group, offices in grouped.items():
        country_totals[
            country_group
        ] = count_country_records(
            offices
        )

        for office, clients in offices.items():
            office_totals[
                office
            ] = count_office_records(
                clients
            )

    total_records = sum(
        country_totals.values()
    )

    total_clients = sum(
        len(clients)
        for offices in grouped.values()
        for clients in offices.values()
    )

    special_email_records = sum(
        1
        for offices in grouped.values()
        for clients in offices.values()
        for records in clients.values()
        for record in records
        if requires_separate_email(
            record
        )
    )

    return {
        "country_totals": country_totals,
        "office_totals": office_totals,
        "total_records": total_records,
        "total_clients": total_clients,
        "special_email_records": (
            special_email_records
        ),
    }


def render_link(
    label: str,
    url: Any,
) -> str:
    clean_url = clean_text(
        url
    )

    if not clean_url:
        return ""

    return (
        f'<a href="{html.escape(clean_url, quote=True)}">'
        f"{html.escape(label)}"
        "</a>"
    )


def render_cell(
    record: dict[str, str],
    column: str,
) -> str:
    value = clean_text(
        record.get(
            column,
            "",
        )
    )

    if column == "Link for Results":
        return render_link(
            "Home",
            value,
        )

    if column == "Link NPS Survey":
        return render_link(
            "NPS",
            value,
        )

    if column == "Link Insights Facilitators":
        return render_link(
            "Facilitators",
            value,
        )

    return html.escape(
        value
    )


def requires_separate_email(
    record: dict[str, str],
) -> bool:
    facilitator = normalize_for_matching(
        record.get(
            "Facilitator",
            "",
        )
    )

    return any(
        special_name in facilitator
        for special_name in SPECIAL_EMAIL_NAMES
    )


def get_record_sort_key(
    record: dict[str, str],
) -> tuple[
    datetime,
    str,
]:
    date_text = clean_text(
        record.get(
            "Date",
            "",
        )
    )

    try:
        parsed_date = datetime.strptime(
            date_text,
            "%m/%d/%Y",
        )
    except ValueError:
        parsed_date = datetime.max

    session = normalize_for_matching(
        record.get(
            "Session",
            "",
        )
    )

    return (
        parsed_date,
        session,
    )



def build_client_table_id(
    client: str,
) -> str:
    digest = hashlib.sha1(
        client.encode(
            "utf-8"
        )
    ).hexdigest()[:12]

    return (
        f"client-table-{digest}"
    )


def render_client_table(
    client: str,
    records: list[dict[str, str]],
) -> str:
    header_cells = "".join(
        f"<th>{html.escape(column)}</th>"
        for column in SLACK_COLUMNS
    )

    sorted_records = sorted(
        records,
        key=get_record_sort_key,
    )

    body_rows = []

    for record in sorted_records:
        special_email = requires_separate_email(
            record
        )

        cells = "".join(
            (
                "<td>"
                + render_cell(
                    record,
                    column,
                )
                + "</td>"
            )
            for column in SLACK_COLUMNS
        )

        if special_email:
            body_rows.append(
                f"""
<tr class="separate-email-warning">
    <td colspan="{len(SLACK_COLUMNS)}">
        ⚠ ENVÍO POR MAIL POR SEPARADO:
        este NPS incluye a Mariano o Maider.
    </td>
</tr>
<tr class="separate-email-row">
    {cells}
</tr>
"""
            )
        else:
            body_rows.append(
                f"""
<tr>
    {cells}
</tr>
"""
            )

    client_count = count_client_records(
        records
    )

    table_id = build_client_table_id(
        client
    )

    return f"""
<section class="client-block">
    <div class="client-header">
        <h3>
            {html.escape(client)}
            <span class="count-badge">
                {client_count}
            </span>
        </h3>

        <button
            class="copy-slack-button"
            type="button"
            onclick="copyTableForSlack('{table_id}', this)"
        >
            Copy for Slack
        </button>
    </div>

    <table id="{table_id}">
        <thead>
            <tr>{header_cells}</tr>
        </thead>
        <tbody>
            {''.join(body_rows)}
        </tbody>
    </table>
</section>
"""


def office_sort_key(
    office: str,
) -> tuple[
    int,
    str,
]:
    normalized = normalize_for_matching(
        office
    )

    preferred_order = {
        "brazil": 1,
        "brasil": 1,
        "nexo": 2,
        "argentina": 1,
        "mexico": 1,
    }

    return (
        preferred_order.get(
            normalized,
            99,
        ),
        normalized,
    )


def render_office_section(
    office: str,
    clients: dict[
        str,
        list[dict[str, str]],
    ],
) -> str:
    client_sections = "".join(
        render_client_table(
            client,
            clients[client],
        )
        for client in sorted(
            clients,
            key=normalize_for_matching,
        )
    )

    office_count = count_office_records(
        clients
    )

    return f"""
<section class="office-block">
    <h2 class="office-title">
        Office: {html.escape(office)}
        <span class="count-badge">
            {office_count}
        </span>
    </h2>

    {client_sections}
</section>
"""


def render_country_section(
    country_group: str,
    offices: dict[
        str,
        dict[
            str,
            list[dict[str, str]],
        ],
    ],
) -> str:
    office_sections = "".join(
        render_office_section(
            office,
            offices[office],
        )
        for office in sorted(
            offices,
            key=office_sort_key,
        )
    )

    country_count = count_country_records(
        offices
    )

    return f"""
<section class="country-block">
    <h1 class="country-title">
        {html.escape(country_group)}
        <span class="country-count">
            {country_count}
        </span>
    </h1>

    {office_sections}
</section>
"""


def render_summary(
    grouped: dict[
        str,
        dict[
            str,
            dict[
                str,
                list[dict[str, str]],
            ],
        ],
    ],
) -> str:
    summary = build_summary_data(
        grouped
    )

    country_rows = "".join(
        f"""
<tr>
    <td>{html.escape(country)}</td>
    <td>{count}</td>
</tr>
"""
        for country, count in sorted(
            summary[
                "country_totals"
            ].items(),
            key=lambda item: (
                COUNTRY_ORDER.get(
                    item[0],
                    99,
                ),
                normalize_for_matching(
                    item[0]
                ),
            ),
        )
    )

    office_rows = "".join(
        f"""
<tr>
    <td>{html.escape(office)}</td>
    <td>{count}</td>
</tr>
"""
        for office, count in sorted(
            summary[
                "office_totals"
            ].items(),
            key=lambda item: office_sort_key(
                item[0]
            ),
        )
    )

    return f"""
<section class="summary-block">
    <h2>Weekly Summary</h2>

    <div class="summary-metrics">
        <div class="metric-card">
            <span class="metric-label">
                Total READY
            </span>
            <span class="metric-value">
                {summary["total_records"]}
            </span>
        </div>

        <div class="metric-card">
            <span class="metric-label">
                Client blocks
            </span>
            <span class="metric-value">
                {summary["total_clients"]}
            </span>
        </div>

        <div class="metric-card">
            <span class="metric-label">
                Separate emails
            </span>
            <span class="metric-value">
                {summary["special_email_records"]}
            </span>
        </div>
    </div>

    <div class="summary-tables">
        <div>
            <h3>By country group</h3>

            <table class="summary-table">
                <thead>
                    <tr>
                        <th>Country group</th>
                        <th>READY</th>
                    </tr>
                </thead>
                <tbody>
                    {country_rows}
                </tbody>
            </table>
        </div>

        <div>
            <h3>By office</h3>

            <table class="summary-table">
                <thead>
                    <tr>
                        <th>Office</th>
                        <th>READY</th>
                    </tr>
                </thead>
                <tbody>
                    {office_rows}
                </tbody>
            </table>
        </div>
    </div>
</section>
"""

def render_review_warning(
    review_count: int,
) -> str:
    """
    Muestra una advertencia únicamente cuando existen
    registros que requieren revisión manual.
    """
    if review_count <= 0:
        return ""

    record_label = (
        "registro"
        if review_count == 1
        else "registros"
    )

    return f"""

"""

def build_html_document(
    records: list[dict[str, str]],
    *,
    weekly_run_id: str,
    window_start: str,
    window_end: str,
    review_count: int,
) -> str:
    grouped = group_records(
        records
    )

    summary_section = render_summary(
        grouped
    )

    review_warning = render_review_warning(
    review_count
)

    country_sections = "".join(
        render_country_section(
            country_group,
            grouped[country_group],
        )
        for country_group in sorted(
            grouped,
            key=lambda value: (
                COUNTRY_ORDER.get(
                    value,
                    99,
                ),
                normalize_for_matching(
                    value
                ),
            ),
        )
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(weekly_run_id)} - Slack Canvas</title>

<style>
.review-warning {{
    background: #fff3cd;
    border: 2px solid #b58105;
    padding: 16px 18px;
    margin: 24px 0 30px 0;
    line-height: 1.5;
}}

.review-warning-title {{
    color: #7a4f00;
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 8px;
}}

.review-warning p {{
    margin: 7px 0;
}}
body {{
    font-family: Arial, sans-serif;
    margin: 28px;
    color: #222;
}}

h1 {{
    margin-bottom: 6px;
}}

.instructions {{
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    padding: 14px;
    margin: 18px 0 32px 0;
    line-height: 1.5;
}}

.summary-block {{
    background: #fafafa;
    border: 1px solid #d1d5db;
    padding: 20px;
    margin: 24px 0 40px 0;
}}

.summary-block h2 {{
    margin-top: 0;
}}

.summary-metrics {{
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 24px;
}}

.metric-card {{
    min-width: 160px;
    background: #ffffff;
    border: 1px solid #d1d5db;
    padding: 14px;
}}

.metric-label {{
    display: block;
    font-size: 13px;
    margin-bottom: 8px;
}}

.metric-value {{
    display: block;
    font-size: 28px;
    font-weight: bold;
}}

.summary-tables {{
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
}}

.summary-tables > div {{
    flex: 1;
    min-width: 280px;
}}

.summary-table {{
    width: 100%;
}}

.country-block {{
    margin-top: 52px;
    margin-bottom: 70px;
}}

.country-title {{
    border-bottom: 4px solid #222;
    padding-bottom: 10px;
    margin-top: 0;
    margin-bottom: 28px;
    font-size: 30px;
}}

.country-count {{
    display: inline-block;
    font-size: 16px;
    margin-left: 10px;
    padding: 4px 9px;
    border: 1px solid #777;
    vertical-align: middle;
}}

.office-block {{
    margin-bottom: 52px;
}}

.office-title {{
    background: #e5e7eb;
    border-left: 6px solid #4b5563;
    padding: 10px 12px;
    margin-top: 30px;
    margin-bottom: 24px;
}}

.client-block {{
    margin-bottom: 42px;
}}

.client-block h3 {{
    margin-bottom: 10px;
    font-size: 20px;
}}

.count-badge {{
    display: inline-block;
    margin-left: 7px;
    padding: 2px 7px;
    border: 1px solid #999;
    font-size: 13px;
    font-weight: normal;
    vertical-align: middle;
}}

.client-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin-bottom: 10px;
}}

.client-header h3 {{
    margin: 0;
}}

.copy-slack-button {{
    border: 1px solid #d1d5db;
    background: #ffffff;
    padding: 7px 12px;
    cursor: pointer;
    font-weight: bold;
    border-radius: 4px;
}}

.copy-slack-button:hover {{
    background: #f3f4f6;
}}

.copy-slack-button:active {{
    background: #e5e7eb;
}}

.copy-slack-button.copy-success {{
    border-color: #15803d;
}}

.copy-slack-button.copy-failed {{
    border-color: #b91c1c;
}}

table {{
    border-collapse: collapse;
    width: 100%;
}}

th,
td {{
    border: 1px solid #b7b7b7;
    padding: 10px;
    text-align: left;
    vertical-align: top;
}}

th {{
    background: #f2f2f2;
    font-weight: bold;
}}

a {{
    color: #0563c1;
}}

.separate-email-row td {{
    background: #fff3cd;
    font-weight: bold;
}}

.separate-email-warning td {{
    background: #f8d7da;
    border: 2px solid #842029;
    color: #842029;
    font-weight: bold;
    padding: 10px;
}}
</style>

<script>
async function copyTableForSlack(tableId, button) {{
    const table = document.getElementById(tableId);

    if (!table) {{
        return;
    }}

    const htmlContent = table.outerHTML;
    const textContent = table.innerText;
    const originalText = button.textContent.trim();

    try {{
        if (
            navigator.clipboard
            && typeof ClipboardItem !== "undefined"
            && navigator.clipboard.write
        ) {{
            const clipboardItem = new ClipboardItem({{
                "text/html": new Blob(
                    [htmlContent],
                    {{ type: "text/html" }}
                ),
                "text/plain": new Blob(
                    [textContent],
                    {{ type: "text/plain" }}
                )
            }});

            await navigator.clipboard.write(
                [clipboardItem]
            );
        }} else {{
            const selection = window.getSelection();
            const range = document.createRange();

            selection.removeAllRanges();
            range.selectNode(table);
            selection.addRange(range);

            const copied = document.execCommand(
                "copy"
            );

            selection.removeAllRanges();

            if (!copied) {{
                throw new Error(
                    "Browser copy command failed."
                );
            }}
        }}

        button.textContent = "Copied ✓";
        button.classList.remove(
            "copy-failed"
        );
        button.classList.add(
            "copy-success"
        );

        window.setTimeout(() => {{
            button.textContent = originalText;
            button.classList.remove(
                "copy-success"
            );
        }}, 1500);

    }} catch (error) {{
        console.error(
            "Copy for Slack failed:",
            error
        );

        button.textContent = "Copy failed";
        button.classList.remove(
            "copy-success"
        );
        button.classList.add(
            "copy-failed"
        );

        window.setTimeout(() => {{
            button.textContent = originalText;
            button.classList.remove(
                "copy-failed"
            );
        }}, 1500);
    }}
}}
</script>
</head>

<body>

<h1>NPS Weekly Slack Canvas</h1>

<p>
<strong>Weekly Run:</strong>
{html.escape(weekly_run_id)}
</p>

<p>
<strong>Window:</strong>
{html.escape(window_start)}
to
{html.escape(window_end)}
</p>

<div class="instructions">
    <strong>How to use:</strong>
    the content is organized by country, office, and client.
    use <strong>Copy for Slack</strong> next to a client to copy
    only that client's table, then paste it into the corresponding
    Slack Canvas.

    <br><br>

    <strong>Special handling:</strong>
    rows highlighted below include Mariano or Maider and
    must be sent separately by email.
</div>

{review_warning}

{summary_section}

{country_sections}

</body>
</html>
"""


def generate_slack_canvas_html(
    weekly_directory: Path | str,
) -> Path:
    directory = Path(
        weekly_directory
    )

    worklist_path = (
        directory
        / "selam_worklist.csv"
    )

    records = load_csv_records(
        worklist_path
    )

    weekly_run_id = directory.name
    window_start = ""
    window_end = ""
    review_count = 0

    summary_path = (
        directory
        / "selam_weekly_summary.json"
    )

    if summary_path.exists():
        with summary_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            summary = json.load(
                file
            )

        weekly_run_id = clean_text(
            summary.get(
                "weekly_run_id"
            )
        ) or weekly_run_id

        window_start = clean_text(
            summary.get(
                "window_start"
            )
        )

        window_end = clean_text(
            summary.get(
                "window_end"
            )
        )

        review_count_value = (
            summary.get("review_records")
            or summary.get("review_count")
            or summary.get("records_review")
            or summary.get("manual_review_records")
            or 0
        )

        try:
            review_count = int(
                review_count_value
            )
        except (
            TypeError,
            ValueError,
        ):
            review_count = 0

    html_content = build_html_document(
    records,
    weekly_run_id=weekly_run_id,
    window_start=window_start,
    window_end=window_end,
    review_count=review_count,
)

    output_path = (
        directory
        / "selam_slack_canvas.html"
    )

    output_path.write_text(
        html_content,
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    if len(
        sys.argv
    ) < 2:
        raise SystemExit(
            "Usage:\n"
            "py -m engine.slack_canvas_renderer "
            "<weekly_run_directory>"
        )

    weekly_directory = Path(
        sys.argv[1]
    )

    output_path = generate_slack_canvas_html(
        weekly_directory
    )

    print("=" * 80)
    print("SLACK CANVAS HTML")
    print("=" * 80)
    print(
        f"HTML generated: {output_path}"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()