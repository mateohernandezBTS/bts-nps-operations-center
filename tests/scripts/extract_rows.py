from csv import DictWriter
from email import policy
from email.parser import BytesParser
from html import unescape
import json
from pathlib import Path

from bs4 import BeautifulSoup


SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent

EML_FILE = TESTS_DIR / "input" / "brazil_upcoming_test.eml"
OUTPUT_DIR = TESTS_DIR / "output"

CSV_FILE = OUTPUT_DIR / "brazil_upcoming_raw.csv"
JSON_FILE = OUTPUT_DIR / "brazil_upcoming_raw.json"


OUTPUT_COLUMNS = [
    "billing_office",
    "start_date",
    "client_name",
    "project_name",
    "project_url",
    "project_sub_type",
    "status",
    "end_date",
    "all_staffings",
    "evaluation_programme",
    "nps",
    "evaluation_avg_facilitator",
    "ignore_reporting",
    "survey_invitation",
    "survey_invitation_link",
]


def clean_text(value: str) -> str:
    """Limpia saltos de línea, espacios duplicados y entidades HTML."""
    if not value:
        return ""

    value = unescape(value)
    return " ".join(value.split()).strip()


def extract_html_from_eml(eml_path: Path) -> str:
    """Extrae la parte HTML principal de un archivo .eml."""
    with eml_path.open("rb") as file:
        message = BytesParser(policy=policy.default).parse(file)

    html_parts = []

    if message.is_multipart():
        for part in message.walk():
            if (
                part.get_content_type() == "text/html"
                and part.get_content_disposition() != "attachment"
            ):
                html_parts.append(part.get_content())

    elif message.get_content_type() == "text/html":
        html_parts.append(message.get_content())

    if not html_parts:
        raise ValueError("No se encontró contenido HTML dentro del correo.")

    return max(html_parts, key=len)


def find_report_table(html_content: str):
    """Encuentra la tabla principal del reporte de Salesforce."""
    soup = BeautifulSoup(html_content, "html.parser")

    table = soup.find(
        "table",
        class_=lambda value: value and "reportTable" in value,
    )

    if table is None:
        raise ValueError("No se encontró la tabla principal del reporte.")

    return table


def extract_link(cell) -> str:
    """Devuelve el href del primer enlace encontrado en una celda."""
    if cell is None:
        return ""

    link = cell.find("a", href=True)

    if link is None:
        return ""

    return clean_text(link.get("href", ""))


def extract_records(report_table) -> list[dict]:
    """Convierte cada fila dataRow del reporte en un diccionario."""
    records = []
    current_billing_office = ""

    data_rows = report_table.find_all(
        "tr",
        class_=lambda value: value and "dataRow" in value,
    )

    for row_number, row in enumerate(data_rows, start=1):
        direct_cells = row.find_all(["th", "td"], recursive=False)

        grouping_cell = row.find(
            "th",
            class_=lambda value: value and "groupingCell" in value,
            recursive=False,
        )

        if grouping_cell is not None:
            # El contenido visible comienza con el nombre de la oficina
            # y puede incluir después "(44 records)".
            grouping_lines = list(grouping_cell.stripped_strings)

            if grouping_lines:
                current_billing_office = clean_text(grouping_lines[0])

        data_cells = [
            cell for cell in direct_cells if cell.name == "td"
        ]

        if len(data_cells) != 13:
            raise ValueError(
                f"La fila {row_number} tiene {len(data_cells)} celdas de datos; "
                "se esperaban 13."
            )

        project_cell = data_cells[2]
        survey_link_cell = data_cells[12]

        record = {
            "billing_office": current_billing_office,
            "start_date": clean_text(data_cells[0].get_text(" ", strip=True)),
            "client_name": clean_text(data_cells[1].get_text(" ", strip=True)),
            "project_name": clean_text(project_cell.get_text(" ", strip=True)),
            "project_url": extract_link(project_cell),
            "project_sub_type": clean_text(
                data_cells[3].get_text(" ", strip=True)
            ),
            "status": clean_text(data_cells[4].get_text(" ", strip=True)),
            "end_date": clean_text(data_cells[5].get_text(" ", strip=True)),
            "all_staffings": clean_text(
                data_cells[6].get_text(" ", strip=True)
            ),
            "evaluation_programme": clean_text(
                data_cells[7].get_text(" ", strip=True)
            ),
            "nps": clean_text(data_cells[8].get_text(" ", strip=True)),
            "evaluation_avg_facilitator": clean_text(
                data_cells[9].get_text(" ", strip=True)
            ),
            "ignore_reporting": clean_text(
                data_cells[10].get_text(" ", strip=True)
            ),
            "survey_invitation": clean_text(
                data_cells[11].get_text(" ", strip=True)
            ),
            "survey_invitation_link": extract_link(survey_link_cell),
        }

        records.append(record)

    return records


def save_csv(records: list[dict], output_path: Path) -> None:
    """Guarda los registros como CSV compatible con Excel."""
    with output_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def save_json(records: list[dict], output_path: Path) -> None:
    """Guarda los registros como JSON."""
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )


def print_preview(records: list[dict], limit: int = 5) -> None:
    """Muestra una vista previa compacta."""
    print()
    print("VISTA PREVIA")
    print("-" * 80)

    for index, record in enumerate(records[:limit], start=1):
        print(
            f"{index}. "
            f"{record['start_date']} | "
            f"{record['client_name']} | "
            f"{record['project_name']} | "
            f"{record['status']} | "
            f"Ignore Reporting: {record['ignore_reporting']}"
        )


def main() -> None:
    print("=" * 80)
    print("EXTRACTOR DE FILAS NPS")
    print("=" * 80)

    if not EML_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de prueba:\n{EML_FILE}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    html_content = extract_html_from_eml(EML_FILE)
    report_table = find_report_table(html_content)
    records = extract_records(report_table)

    save_csv(records, CSV_FILE)
    save_json(records, JSON_FILE)

    print(f"Archivo leído: {EML_FILE.name}")
    print(f"Registros extraídos: {len(records)}")
    print(f"CSV generado: {CSV_FILE}")
    print(f"JSON generado: {JSON_FILE}")

    print_preview(records)

    print()
    print("=" * 80)

    if len(records) == 83:
        print("VALIDACIÓN CORRECTA: se extrajeron los 83 registros.")
    else:
        print(
            f"REVISIÓN NECESARIA: se extrajeron {len(records)} registros "
            "en lugar de 83."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()