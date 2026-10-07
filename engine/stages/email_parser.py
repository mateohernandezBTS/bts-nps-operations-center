from email import policy
from email.parser import BytesParser
from html import unescape
from pathlib import Path
import re
import unicodedata

from bs4 import BeautifulSoup


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


HEADER_MAPPING = {
    "billing office": "billing_office",
    "start date": "start_date",
    "client name": "client_name",
    "project project name": "project_name",
    "project sub type": "project_sub_type",
    "status": "status",
    "end date": "end_date",
    "all staffings": "all_staffings",

    "evaluation programme": "evaluation_programme",
    "evaluation programme sum": "evaluation_programme",

    "nps": "nps",
    "nps sum": "nps",

    "evaluation avg facilitator": "evaluation_avg_facilitator",
    "evaluation avg facilitator sum": "evaluation_avg_facilitator",

    "ignore reporting": "ignore_reporting",
    "ignore reporting sum": "ignore_reporting",

    "survey invitation": "survey_invitation",
    "survey invitation link": "survey_invitation_link",
}


REQUIRED_HEADERS = {
    "billing_office",
    "start_date",
    "client_name",
    "project_name",
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
}


def clean_text(value) -> str:
    """Limpia espacios y entidades HTML."""
    if value is None:
        return ""

    return " ".join(
        unescape(str(value)).split()
    ).strip()


def normalize_header(value: str) -> str:
    """
    Normaliza un encabezado Salesforce.

    Ejemplos:
    Client_Name -> client name
    Project: Project Name -> project project name
    Survey Invitation ↓ -> survey invitation
    """
    text = clean_text(value).casefold()

    normalized = unicodedata.normalize(
        "NFKD",
        text,
    )

    without_accents = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )

    without_symbols = re.sub(
        r"[^a-z0-9]+",
        " ",
        without_accents,
    )

    return " ".join(
        without_symbols.split()
    )


def extract_html_from_eml(
    eml_path: Path,
) -> str:
    """Extrae el bloque HTML principal del correo."""
    with eml_path.open("rb") as file:
        message = BytesParser(
            policy=policy.default
        ).parse(file)

    html_parts = []

    if message.is_multipart():
        for part in message.walk():
            if (
                part.get_content_type() == "text/html"
                and part.get_content_disposition()
                != "attachment"
            ):
                html_parts.append(
                    part.get_content()
                )

    elif message.get_content_type() == "text/html":
        html_parts.append(
            message.get_content()
        )

    if not html_parts:
        raise ValueError(
            "No se encontró contenido HTML dentro del correo."
        )

    return max(
        html_parts,
        key=len,
    )


def find_report_table(
    html_content: str,
):
    """Encuentra la tabla principal del reporte Salesforce."""
    soup = BeautifulSoup(
        html_content,
        "html.parser",
    )

    table = soup.find(
        "table",
        class_=lambda value: (
            value
            and "reportTable" in value
        ),
    )

    if table is None:
        raise ValueError(
            "No se encontró la tabla principal del reporte."
        )

    return table


def extract_link(cell) -> str:
    """Extrae el primer enlace de una celda."""
    if cell is None:
        return ""

    link = cell.find(
        "a",
        href=True,
    )

    if link is None:
        return ""

    return clean_text(
        link.get("href", "")
    )


def find_header_row(
    report_table,
):
    """
    Encuentra la fila de encabezados que contiene
    las columnas Salesforce esperadas.
    """
    for row in report_table.find_all("tr"):
        cells = row.find_all(
            ["th", "td"],
            recursive=False,
        )

        if not cells:
            continue

        normalized_headers = [
            normalize_header(
                cell.get_text(
                    " ",
                    strip=True,
                )
            )
            for cell in cells
        ]

        recognized_count = sum(
            header in HEADER_MAPPING
            for header in normalized_headers
        )

        if recognized_count >= 10:
            return row, cells

    raise ValueError(
        "No se encontró una fila de encabezados reconocible."
    )


def build_header_positions(
    header_cells,
) -> dict[str, int]:
    """Relaciona cada campo interno con su posición real."""
    positions = {}

    for index, cell in enumerate(
        header_cells
    ):
        visible_header = cell.get_text(
            " ",
            strip=True,
        )

        normalized_header = normalize_header(
            visible_header
        )

        internal_name = HEADER_MAPPING.get(
            normalized_header
        )

        if internal_name:
            positions[internal_name] = index

    missing_headers = (
        REQUIRED_HEADERS
        - set(positions)
    )

    if missing_headers:
        raise ValueError(
            "Faltan columnas requeridas en el reporte: "
            + ", ".join(
                sorted(missing_headers)
            )
        )

    return positions


def get_row_cell(
    row_cells,
    column_name: str,
    header_positions: dict[str, int],
    current_billing_office: str,
):
    """
    Devuelve una celda según su encabezado.

    Admite:
    - 14 celdas normales;
    - Billing Office como TH;
    - filas que omitan la celda agrupadora y hereden oficina.
    """
    expected_column_count = len(
        header_positions
    )

    column_index = header_positions[
        column_name
    ]

    if len(row_cells) == expected_column_count:
        return row_cells[column_index]

    if (
        len(row_cells)
        == expected_column_count - 1
        and column_name != "billing_office"
    ):
        billing_index = header_positions[
            "billing_office"
        ]

        adjusted_index = column_index

        if column_index > billing_index:
            adjusted_index -= 1

        return row_cells[
            adjusted_index
        ]

    if (
        len(row_cells)
        == expected_column_count - 1
        and column_name == "billing_office"
        and current_billing_office
    ):
        return None

    raise ValueError(
        "La fila tiene una cantidad de celdas no reconocida: "
        f"{len(row_cells)}. "
        f"Se esperaban {expected_column_count} "
        f"o {expected_column_count - 1}."
    )


def extract_records(
    report_table,
) -> list[dict]:
    """Convierte las filas Salesforce en registros estructurados."""
    _, header_cells = find_header_row(
        report_table
    )

    header_positions = (
        build_header_positions(
            header_cells
        )
    )

    expected_column_count = len(
        header_positions
    )

    records = []
    current_billing_office = ""

    data_rows = report_table.find_all(
        "tr",
        class_=lambda value: (
            value
            and "dataRow" in value
        ),
    )

    for row_number, row in enumerate(
        data_rows,
        start=1,
    ):
        row_cells = row.find_all(
            ["th", "td"],
            recursive=False,
        )

        if len(row_cells) not in {
            expected_column_count,
            expected_column_count - 1,
        }:
            raise ValueError(
                f"La fila {row_number} tiene "
                f"{len(row_cells)} celdas; "
                f"se esperaban "
                f"{expected_column_count} "
                f"o {expected_column_count - 1}."
            )

        billing_cell = get_row_cell(
            row_cells=row_cells,
            column_name="billing_office",
            header_positions=header_positions,
            current_billing_office=current_billing_office,
        )

        if billing_cell is not None:
            billing_text = clean_text(
                billing_cell.get_text(
                    " ",
                    strip=True,
                )
            )

            if billing_text:
                current_billing_office = (
                    billing_text
                )

        def cell_for(
            column_name: str,
        ):
            return get_row_cell(
                row_cells=row_cells,
                column_name=column_name,
                header_positions=header_positions,
                current_billing_office=current_billing_office,
            )

        def text_for(
            column_name: str,
        ) -> str:
            cell = cell_for(
                column_name
            )

            if cell is None:
                if (
                    column_name
                    == "billing_office"
                ):
                    return (
                        current_billing_office
                    )

                return ""

            return clean_text(
                cell.get_text(
                    " ",
                    strip=True,
                )
            )

        project_cell = cell_for(
            "project_name"
        )

        survey_invitation_cell = (
            cell_for(
                "survey_invitation"
            )
        )

        survey_link_cell = cell_for(
            "survey_invitation_link"
        )

        # En algunos reportes el enlace está en Survey Invitation
        # y la última columna aparece vacía.
        survey_invitation_link = (
            extract_link(
                survey_link_cell
            )
            or extract_link(
                survey_invitation_cell
            )
        )

        record = {
            "billing_office": (
                current_billing_office
            ),
            "start_date": text_for(
                "start_date"
            ),
            "client_name": text_for(
                "client_name"
            ),
            "project_name": text_for(
                "project_name"
            ),
            "project_url": extract_link(
                project_cell
            ),
            "project_sub_type": text_for(
                "project_sub_type"
            ),
            "status": text_for(
                "status"
            ),
            "end_date": text_for(
                "end_date"
            ),
            "all_staffings": text_for(
                "all_staffings"
            ),
            "evaluation_programme": text_for(
                "evaluation_programme"
            ),
            "nps": text_for(
                "nps"
            ),
            "evaluation_avg_facilitator": text_for(
                "evaluation_avg_facilitator"
            ),
            "ignore_reporting": text_for(
                "ignore_reporting"
            ),
            "survey_invitation": text_for(
                "survey_invitation"
            ),
            "survey_invitation_link": (
                survey_invitation_link
            ),
        }

        records.append(record)

    return records


def parse_eml_report(
    eml_path: Path,
) -> list[dict]:
    """Ejecuta la lectura completa de un reporte EML."""
    html_content = extract_html_from_eml(
        eml_path
    )

    report_table = find_report_table(
        html_content
    )

    return extract_records(
        report_table
    )