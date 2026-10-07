from csv import DictReader, DictWriter
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent
PROJECT_DIR = TESTS_DIR.parent

INPUT_CSV = TESTS_DIR / "output" / "brazil_upcoming_eligible.csv"
CONFIG_FILE = PROJECT_DIR / "config" / "operational_output.json"

OUTPUT_DIR = TESTS_DIR / "output"

WORKLIST_CSV = OUTPUT_DIR / "brazil_upcoming_worklist.csv"
WORKLIST_JSON = OUTPUT_DIR / "brazil_upcoming_worklist.json"

WORKLIST_EXCEPTIONS_CSV = (
    OUTPUT_DIR / "brazil_upcoming_worklist_exceptions.csv"
)

OUTSIDE_WINDOW_CSV = (
    OUTPUT_DIR / "brazil_upcoming_outside_weekly_window.csv"
)


WORKLIST_COLUMNS = [
    "Session",
    "Date",
    "Facilitator",
    "QR-Code",
    "Link NPS Survey",
    "Link Insights Facilitators",
    "Results",
    "Link for Results",
    "Project ID",
    "Client",
    "Project URL",
    "Output Status",
    "Output Issues",
]


OUTSIDE_WINDOW_COLUMNS = [
    "start_date",
    "client_name",
    "project_name",
    "all_staffings",
    "status",
    "ignore_reporting",
    "window_start",
    "window_end",
    "window_reason",
]


SALESFORCE_ID_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z0-9]{15}|[A-Za-z0-9]{18})(?![A-Za-z0-9])"
)


def clean_text(value) -> str:
    """Limpia espacios sin alterar el contenido original."""
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def load_json(path: Path) -> dict:
    """Carga un archivo JSON."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_csv(path: Path) -> list[dict]:
    """Carga un CSV compatible con Excel."""
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(DictReader(file))


def parse_salesforce_date(value: str) -> datetime:
    """Convierte una fecha Salesforce M/D/YYYY en datetime."""
    cleaned_value = clean_text(value)

    if not cleaned_value:
        raise ValueError("Fecha vacía")

    return datetime.strptime(cleaned_value, "%m/%d/%Y")


def format_salesforce_date(value: datetime) -> str:
    """Devuelve una fecha en formato Salesforce M/D/YYYY."""
    return f"{value.month}/{value.day}/{value.year}"


def calculate_weekly_window(config: dict) -> tuple[datetime, datetime]:
    """
    Calcula la ventana semanal a partir del lunes de referencia.

    Ejemplo:
    lunes 7/27/2026
    inicio martes 7/28/2026
    fin lunes 8/3/2026
    """
    weekly_config = config.get("weekly_window", {})

    reference_monday = parse_salesforce_date(
        weekly_config.get("reference_monday", "")
    )

    start_offset = int(
        weekly_config.get("start_offset_days", 1)
    )

    end_offset = int(
        weekly_config.get("end_offset_days", 7)
    )

    window_start = reference_monday + timedelta(
        days=start_offset
    )

    window_end = reference_monday + timedelta(
        days=end_offset
    )

    return window_start, window_end


def record_is_in_weekly_window(
    record: dict,
    window_start: datetime,
    window_end: datetime,
) -> bool:
    """Indica si la fecha del registro cae dentro de la ventana."""
    record_date = parse_salesforce_date(
        record.get("start_date", "")
    )

    return window_start <= record_date <= window_end


def normalize_facilitators(
    value: str,
    facilitator_config: dict,
) -> str:
    """
    Limpia valores vacíos y elimina facilitadores duplicados.

    Conserva el orden original y no modifica nombres como PRELIM Selam.
    """
    cleaned_value = clean_text(value)

    separator = facilitator_config.get(
        "separator",
        ",",
    )

    configured_empty_values = facilitator_config.get(
        "empty_values",
        [],
    )

    empty_values = {
        clean_text(item).casefold()
        for item in configured_empty_values
    }

    if cleaned_value.casefold() in empty_values:
        return ""

    parts = cleaned_value.split(separator)

    unique_facilitators = []
    seen = set()

    for part in parts:
        facilitator = clean_text(part)

        if facilitator.casefold() in empty_values:
            continue

        matching_key = facilitator.casefold()

        if matching_key in seen:
            continue

        seen.add(matching_key)
        unique_facilitators.append(facilitator)

    return separator.join(unique_facilitators)


def extract_salesforce_id(project_url: str) -> str:
    """Extrae un ID Salesforce de 15 o 18 caracteres."""
    cleaned_url = clean_text(project_url)

    if not cleaned_url:
        return ""

    decoded_url = unquote(cleaned_url)
    parsed_url = urlparse(decoded_url)

    path_segments = [
        segment
        for segment in parsed_url.path.split("/")
        if segment
    ]

    for segment in reversed(path_segments):
        if re.fullmatch(
            r"[A-Za-z0-9]{15}|[A-Za-z0-9]{18}",
            segment,
        ):
            return segment

    match = SALESFORCE_ID_PATTERN.search(decoded_url)

    if match:
        return match.group(1)

    return ""


def build_results_link(
    project_id: str,
    base_url: str,
) -> str:
    """Genera el enlace de resultados."""
    if not project_id:
        return ""

    return f"{base_url}{project_id}"


def create_worklist_record(
    source_record: dict,
    config: dict,
) -> dict:
    """Convierte un registro elegible en una fila operativa."""
    issues = []

    project_url = clean_text(
        source_record.get("project_url", "")
    )

    project_id = extract_salesforce_id(project_url)

    if not project_id:
        issues.append(
            "No se pudo extraer Project ID desde Project URL"
        )

    session = clean_text(
        source_record.get("project_name", "")
    )

    date = clean_text(
        source_record.get("start_date", "")
    )

    facilitator = normalize_facilitators(
        value=source_record.get("all_staffings", ""),
        facilitator_config=config.get("facilitators", {}),
    )

    if not session:
        issues.append("Session vacío")

    if not date:
        issues.append("Date vacío")

    # Un facilitador vacío está permitido.
    # No genera REVIEW ni observación.

    results_config = config.get("results", {})
    defaults = config.get("defaults", {})

    results_link = build_results_link(
        project_id=project_id,
        base_url=clean_text(
            results_config.get("base_url", "")
        ),
    )

    output_status = "READY" if not issues else "REVIEW"

    return {
        "Session": session,
        "Date": date,
        "Facilitator": facilitator,
        "QR-Code": clean_text(
            defaults.get("qr_code", "")
        ),
        "Link NPS Survey": clean_text(
            defaults.get("nps_survey_link", "")
        ),
        "Link Insights Facilitators": clean_text(
            defaults.get("facilitator_insights_link", "")
        ),
        "Results": clean_text(
            results_config.get("default_status", "NO")
        ),
        "Link for Results": results_link,
        "Project ID": project_id,
        "Client": clean_text(
            source_record.get("client_name", "")
        ),
        "Project URL": project_url,
        "Output Status": output_status,
        "Output Issues": " | ".join(issues),
    }


def create_outside_window_record(
    source_record: dict,
    window_start: datetime,
    window_end: datetime,
) -> dict:
    """Registra una fila que no pertenece a la semana procesada."""
    return {
        "start_date": clean_text(
            source_record.get("start_date", "")
        ),
        "client_name": clean_text(
            source_record.get("client_name", "")
        ),
        "project_name": clean_text(
            source_record.get("project_name", "")
        ),
        "all_staffings": clean_text(
            source_record.get("all_staffings", "")
        ),
        "status": clean_text(
            source_record.get("status", "")
        ),
        "ignore_reporting": clean_text(
            source_record.get("ignore_reporting", "")
        ),
        "window_start": format_salesforce_date(window_start),
        "window_end": format_salesforce_date(window_end),
        "window_reason": "Fecha fuera de la ventana semanal",
    }


def save_csv(
    records: list[dict],
    output_path: Path,
    fieldnames: list[str],
) -> None:
    """Guarda registros en CSV, incluso si la lista está vacía."""
    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(records)


def save_json(
    records: list[dict],
    output_path: Path,
) -> None:
    """Guarda registros en JSON."""
    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )


def main() -> None:
    print("=" * 80)
    print("GENERADOR DE WORKLIST OPERATIVA NPS")
    print("=" * 80)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de elegibles:\n{INPUT_CSV}"
        )

    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró la configuración:\n{CONFIG_FILE}"
        )

    eligible_records = load_csv(INPUT_CSV)
    config = load_json(CONFIG_FILE)

    weekly_config = config.get("weekly_window", {})
    weekly_window_enabled = weekly_config.get(
        "enabled",
        True,
    )

    if weekly_window_enabled:
        window_start, window_end = calculate_weekly_window(
            config
        )

        records_in_window = []
        outside_window_records = []

        for record in eligible_records:
            if record_is_in_weekly_window(
                record=record,
                window_start=window_start,
                window_end=window_end,
            ):
                records_in_window.append(record)
            else:
                outside_window_records.append(
                    create_outside_window_record(
                        source_record=record,
                        window_start=window_start,
                        window_end=window_end,
                    )
                )
    else:
        records_in_window = eligible_records
        outside_window_records = []
        window_start = None
        window_end = None

    worklist_records = [
        create_worklist_record(record, config)
        for record in records_in_window
    ]

    ready_records = [
        record
        for record in worklist_records
        if record["Output Status"] == "READY"
    ]

    review_records = [
        record
        for record in worklist_records
        if record["Output Status"] == "REVIEW"
    ]

    save_csv(
        records=worklist_records,
        output_path=WORKLIST_CSV,
        fieldnames=WORKLIST_COLUMNS,
    )

    save_json(
        records=worklist_records,
        output_path=WORKLIST_JSON,
    )

    save_csv(
        records=review_records,
        output_path=WORKLIST_EXCEPTIONS_CSV,
        fieldnames=WORKLIST_COLUMNS,
    )

    save_csv(
        records=outside_window_records,
        output_path=OUTSIDE_WINDOW_CSV,
        fieldnames=OUTSIDE_WINDOW_COLUMNS,
    )

    print(f"Registros elegibles recibidos: {len(eligible_records)}")

    if weekly_window_enabled:
        print(
            "Ventana semanal: "
            f"{format_salesforce_date(window_start)} "
            f"hasta {format_salesforce_date(window_end)}"
        )

    print(
        f"Registros dentro de la ventana: "
        f"{len(records_in_window)}"
    )

    print(
        f"Registros fuera de la ventana: "
        f"{len(outside_window_records)}"
    )

    print(f"Filas operativas generadas: {len(worklist_records)}")
    print(f"Listas para usar: {len(ready_records)}")
    print(f"Filas para revisar: {len(review_records)}")

    print()
    print("ARCHIVOS GENERADOS")
    print("-" * 80)
    print(f"Worklist CSV: {WORKLIST_CSV}")
    print(f"Worklist JSON: {WORKLIST_JSON}")
    print(f"Excepciones: {WORKLIST_EXCEPTIONS_CSV}")
    print(f"Fuera de ventana: {OUTSIDE_WINDOW_CSV}")

    print()
    print("VISTA PREVIA")
    print("-" * 80)

    for index, record in enumerate(
        worklist_records[:10],
        start=1,
    ):
        facilitator_display = (
            record["Facilitator"]
            if record["Facilitator"]
            else "[VACÍO]"
        )

        print(
            f"{index}. "
            f"{record['Date']} | "
            f"{record['Session']} | "
            f"{facilitator_display} | "
            f"{record['Results']} | "
            f"{record['Output Status']}"
        )

    print()
    print("=" * 80)

    if len(records_in_window) == len(worklist_records):
        print(
            "VALIDACIÓN DE CANTIDAD CORRECTA: "
            "todos los registros de la semana generaron una fila."
        )
    else:
        print(
            "ERROR: la cantidad de filas no coincide "
            "con los registros de la semana."
        )

    if not review_records:
        print(
            "VALIDACIÓN DE SALIDA CORRECTA: "
            "todas las filas semanales están listas."
        )
    else:
        print(
            f"REVISIÓN NECESARIA: "
            f"{len(review_records)} filas tienen observaciones."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()