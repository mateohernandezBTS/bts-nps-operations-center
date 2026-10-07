from email import policy
from email.parser import BytesParser
from pathlib import Path
import sys

from bs4 import BeautifulSoup


SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent
PROJECT_DIR = TESTS_DIR.parent

sys.path.insert(0, str(PROJECT_DIR))


INPUT_FILE = (
    PROJECT_DIR
    / "input"
    / "pending"
    / "Report results (Mexico Upcoming Deliveries_NPS).eml"
)


def clean_text(value) -> str:
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def extract_html(eml_path: Path) -> str:
    with eml_path.open("rb") as file:
        message = BytesParser(
            policy=policy.default
        ).parse(file)

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
        raise ValueError("No se encontró HTML en el correo.")

    return max(html_parts, key=len)


def main() -> None:
    print("=" * 80)
    print("INSPECTOR DE COLUMNAS SALESFORCE")
    print("=" * 80)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo:\n{INPUT_FILE}"
        )

    html = extract_html(INPUT_FILE)
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find(
        "table",
        class_=lambda value: value and "reportTable" in value,
    )

    if table is None:
        raise ValueError("No se encontró la tabla principal.")

    header_rows = table.find_all("tr")

    print()
    print("ENCABEZADOS DETECTADOS")
    print("-" * 80)

    for row_index, row in enumerate(header_rows[:5], start=1):
        cells = row.find_all(["th", "td"], recursive=False)

        if not cells:
            continue

        print(f"Fila HTML {row_index}: {len(cells)} celdas")

        for index, cell in enumerate(cells, start=1):
            print(
                f"  {index:>2}. "
                f"{clean_text(cell.get_text(' ', strip=True))}"
            )

        print()

    data_row = table.find(
        "tr",
        class_=lambda value: value and "dataRow" in value,
    )

    if data_row is None:
        raise ValueError("No se encontró ninguna fila de datos.")

    data_cells = data_row.find_all("td", recursive=False)

    print()
    print("PRIMERA FILA DE DATOS")
    print("-" * 80)
    print(f"Cantidad de celdas TD: {len(data_cells)}")

    for index, cell in enumerate(data_cells, start=1):
        text = clean_text(
            cell.get_text(" ", strip=True)
        )

        link = cell.find("a", href=True)
        href = clean_text(
            link.get("href", "")
        ) if link else ""

        print(f"{index:>2}. Texto: {text}")

        if href:
            print(f"    Link: {href}")

    print()
    print("=" * 80)
    print("INSPECCIÓN FINALIZADA")
    print("=" * 80)


if __name__ == "__main__":
    main()