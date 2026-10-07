from collections import defaultdict
from csv import DictReader, DictWriter
from datetime import datetime, timedelta
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent
PROJECT_DIR = TESTS_DIR.parent

INPUT_CSV = TESTS_DIR / "output" / "brazil_upcoming_worklist.csv"
CONFIG_FILE = PROJECT_DIR / "config" / "operational_output.json"

OUTPUT_DIR = TESTS_DIR / "output"

SLACK_CSV = OUTPUT_DIR / "brazil_upcoming_slack_ready.csv"
SLACK_MARKDOWN = OUTPUT_DIR / "brazil_upcoming_slack_ready.md"


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
    """Limpia espacios y valores nulos."""
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def load_json(path: Path) -> dict:
    """Carga un archivo JSON."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_csv(path: Path) -> list[dict]:
    """Carga el CSV de la worklist semanal."""
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(DictReader(file))


def parse_salesforce_date(value: str) -> datetime:
    """Convierte una fecha M/D/YYYY."""
    return datetime.strptime(
        clean_text(value),
        "%m/%d/%Y",
    )


def format_salesforce_date(value: datetime) -> str:
    """Devuelve una fecha M/D/YYYY."""
    return f"{value.month}/{value.day}/{value.year}"


def calculate_weekly_window(
    config: dict,
) -> tuple[datetime, datetime]:
    """Calcula la ventana semanal configurada."""
    weekly_config = config.get("weekly_window", {})

    reference_monday = parse_salesforce_date(
        weekly_config.get("reference_monday", "")
    )

    window_start = reference_monday + timedelta(
        days=int(
            weekly_config.get("start_offset_days", 1)
        )
    )

    window_end = reference_monday + timedelta(
        days=int(
            weekly_config.get("end_offset_days", 7)
        )
    )

    return window_start, window_end


def markdown_escape(value: str) -> str:
    """
    Protege caracteres que podrían romper una tabla Markdown.

    Los saltos de línea se convierten en espacios y las barras verticales
    se escapan.
    """
    cleaned_value = clean_text(value)

    return cleaned_value.replace("|", r"\|")


def build_markdown_link(
    url: str,
    display_text: str,
) -> str:
    """Genera un enlace Markdown o devuelve vacío."""
    cleaned_url = clean_text(url)

    if not cleaned_url:
        return ""

    return f"[{markdown_escape(display_text)}]({cleaned_url})"


def create_operational_record(
    record: dict,
) -> dict:
    """Conserva únicamente las columnas operativas."""
    return {
        column: clean_text(record.get(column, ""))
        for column in SLACK_COLUMNS
    }


def sort_records(records: list[dict]) -> list[dict]:
    """Ordena por cliente, fecha y sesión."""
    return sorted(
        records,
        key=lambda record: (
            clean_text(record.get("Client", "")).casefold(),
            parse_salesforce_date(record.get("Date", "")),
            clean_text(record.get("Session", "")).casefold(),
        ),
    )


def save_csv(
    records: list[dict],
    output_path: Path,
) -> None:
    """Guarda la salida operativa sin columnas técnicas."""
    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = DictWriter(
            file,
            fieldnames=SLACK_COLUMNS,
            extrasaction="ignore",
        )

        writer.writeheader()

        for record in records:
            writer.writerow(
                create_operational_record(record)
            )


def generate_markdown(
    records: list[dict],
    config: dict,
) -> str:
    """Genera tablas Markdown agrupadas por cliente."""
    slack_config = config.get("slack_output", {})

    group_by = clean_text(
        slack_config.get("group_by", "Client")
    )

    empty_display = slack_config.get(
        "empty_display",
        "",
    )

    link_text = clean_text(
        slack_config.get("results_link_text", "Home")
    )

    grouped_records = defaultdict(list)

    for record in records:
        group_name = clean_text(
            record.get(group_by, "")
        )

        if not group_name:
            group_name = "Cliente sin identificar"

        grouped_records[group_name].append(record)

    markdown_lines = []

    if slack_config.get("include_weekly_heading", True):
        window_start, window_end = calculate_weekly_window(
            config
        )

        heading_template = slack_config.get(
            "weekly_heading_template",
            "Upcoming NPS | Brazil | "
            "{window_start} to {window_end}",
        )

        heading = heading_template.format(
            window_start=format_salesforce_date(
                window_start
            ),
            window_end=format_salesforce_date(
                window_end
            ),
        )

        markdown_lines.append(f"# {heading}")
        markdown_lines.append("")

    markdown_lines.append(
        f"Total de sesiones: {len(records)}"
    )
    markdown_lines.append("")

    for group_name in sorted(
        grouped_records,
        key=str.casefold,
    ):
        group_records = sorted(
            grouped_records[group_name],
            key=lambda record: (
                parse_salesforce_date(
                    record.get("Date", "")
                ),
                clean_text(
                    record.get("Session", "")
                ).casefold(),
            ),
        )

        markdown_lines.append(
            f"## {markdown_escape(group_name)}"
        )

        markdown_lines.append("")

        markdown_lines.append(
            "| Session | Date | Facilitator | QR-Code | "
            "Link NPS Survey | Link Insights Facilitators | "
            "Results | Link for Results |"
        )

        markdown_lines.append(
            "|---|---|---|---|---|---|---|---|"
        )

        for record in group_records:
            values = {
                "Session": markdown_escape(
                    record.get("Session", "")
                    or empty_display
                ),
                "Date": markdown_escape(
                    record.get("Date", "")
                    or empty_display
                ),
                "Facilitator": markdown_escape(
                    record.get("Facilitator", "")
                    or empty_display
                ),
                "QR-Code": markdown_escape(
                    record.get("QR-Code", "")
                    or empty_display
                ),
                "Link NPS Survey": markdown_escape(
                    record.get("Link NPS Survey", "")
                    or empty_display
                ),
                "Link Insights Facilitators": markdown_escape(
                    record.get(
                        "Link Insights Facilitators",
                        "",
                    )
                    or empty_display
                ),
                "Results": markdown_escape(
                    record.get("Results", "")
                    or empty_display
                ),
                "Link for Results": build_markdown_link(
                    url=record.get(
                        "Link for Results",
                        "",
                    ),
                    display_text=link_text,
                ),
            }

            markdown_lines.append(
                "| "
                f"{values['Session']} | "
                f"{values['Date']} | "
                f"{values['Facilitator']} | "
                f"{values['QR-Code']} | "
                f"{values['Link NPS Survey']} | "
                f"{values['Link Insights Facilitators']} | "
                f"{values['Results']} | "
                f"{values['Link for Results']} |"
            )

        markdown_lines.append("")

    return "\n".join(markdown_lines).rstrip() + "\n"


def main() -> None:
    print("=" * 80)
    print("GENERADOR DE SALIDA SLACK NPS")
    print("=" * 80)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"No se encontró la worklist semanal:\n{INPUT_CSV}"
        )

    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró la configuración:\n{CONFIG_FILE}"
        )

    records = load_csv(INPUT_CSV)
    config = load_json(CONFIG_FILE)

    ready_records = [
        record
        for record in records
        if record.get("Output Status") == "READY"
    ]

    sorted_records = sort_records(ready_records)

    save_csv(
        records=sorted_records,
        output_path=SLACK_CSV,
    )

    markdown_content = generate_markdown(
        records=sorted_records,
        config=config,
    )

    SLACK_MARKDOWN.write_text(
        markdown_content,
        encoding="utf-8",
    )

    grouped_clients = {
        clean_text(record.get("Client", ""))
        or "Cliente sin identificar"
        for record in sorted_records
    }

    print(f"Filas recibidas: {len(records)}")
    print(f"Filas READY incluidas: {len(sorted_records)}")
    print(f"Clientes agrupados: {len(grouped_clients)}")

    print()
    print("ARCHIVOS GENERADOS")
    print("-" * 80)
    print(f"CSV listo para Slack: {SLACK_CSV}")
    print(f"Markdown listo para Slack: {SLACK_MARKDOWN}")

    print()
    print("RESUMEN POR CLIENTE")
    print("-" * 80)

    counts = defaultdict(int)

    for record in sorted_records:
        client = (
            clean_text(record.get("Client", ""))
            or "Cliente sin identificar"
        )
        counts[client] += 1

    for client in sorted(counts, key=str.casefold):
        print(f"{counts[client]:>3} | {client}")

    print()
    print("=" * 80)

    if len(sorted_records) == len(records):
        print(
            "VALIDACIÓN CORRECTA: "
            "todas las filas semanales fueron incluidas."
        )
    else:
        print(
            "ATENCIÓN: algunas filas no fueron incluidas "
            "porque no tenían Output Status = READY."
        )

    if sorted_records:
        print(
            "SALIDA GENERADA: CSV y Markdown disponibles."
        )
    else:
        print(
            "SALIDA VACÍA: no había filas READY para esta semana."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()