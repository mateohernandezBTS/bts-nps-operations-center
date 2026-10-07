from email import policy
from email.parser import BytesParser
from pathlib import Path
from bs4 import BeautifulSoup


# Ubicación del script actual:
# NPS Automation/tests/scripts/read_eml.py
SCRIPT_DIR = Path(__file__).resolve().parent

# Carpeta tests
TESTS_DIR = SCRIPT_DIR.parent

# Archivo de correo de prueba
EML_FILE = TESTS_DIR / "input" / "brazil_upcoming_test.eml"


def extract_html_from_eml(eml_path: Path) -> str:
    """Extrae el contenido HTML principal de un archivo .eml."""

    with eml_path.open("rb") as file:
        message = BytesParser(policy=policy.default).parse(file)

    html_parts = []

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()

            if content_type == "text/html" and disposition != "attachment":
                html_parts.append(part.get_content())
    elif message.get_content_type() == "text/html":
        html_parts.append(message.get_content())

    if not html_parts:
        raise ValueError("No se encontró contenido HTML dentro del correo.")

    # Generalmente la parte HTML más larga contiene el reporte completo.
    return max(html_parts, key=len)


def find_salesforce_report_table(html_content: str):
    """Busca la tabla principal del reporte de Salesforce."""

    soup = BeautifulSoup(html_content, "html.parser")

    table = soup.find("table", class_=lambda value: value and "reportTable" in value)

    if table is None:
        raise ValueError("No se encontró la tabla principal del reporte.")

    return table


def main():
    print("=" * 60)
    print("LECTOR DE CORREOS NPS")
    print("=" * 60)

    if not EML_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de prueba:\n{EML_FILE}"
        )

    print(f"Archivo encontrado: {EML_FILE.name}")

    html_content = extract_html_from_eml(EML_FILE)

    print(f"HTML extraído correctamente.")
    print(f"Tamaño del HTML: {len(html_content):,} caracteres")

    report_table = find_salesforce_report_table(html_content)

    all_rows = report_table.find_all("tr")
    data_rows = report_table.find_all(
        "tr",
        class_=lambda value: value and "dataRow" in value
    )

    print("Tabla principal encontrada.")
    print(f"Filas HTML totales: {len(all_rows)}")
    print(f"Filas de datos detectadas: {len(data_rows)}")

    print("=" * 60)
    print("PRUEBA FINALIZADA CORRECTAMENTE")
    print("=" * 60)


if __name__ == "__main__":
    main()