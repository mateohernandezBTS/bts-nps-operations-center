from csv import DictReader, DictWriter
from datetime import datetime
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent

INPUT_CSV = TESTS_DIR / "output" / "brazil_upcoming_raw.csv"

OUTPUT_DIR = TESTS_DIR / "output"
NORMALIZED_CSV = OUTPUT_DIR / "brazil_upcoming_normalized.csv"
NORMALIZED_JSON = OUTPUT_DIR / "brazil_upcoming_normalized.json"
VALIDATION_JSON = OUTPUT_DIR / "brazil_upcoming_validation.json"


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
    "validation_status",
    "validation_issues",
]


TRUE_VALUES = {
    "✔",
    "✓",
    "true",
    "yes",
    "y",
    "1",
    "x",
}

FALSE_VALUES = {
    "✕",
    "✖",
    "false",
    "no",
    "n",
    "0",
    "",
}


STATUS_MAPPING = {
    "prelim": "Prelim",
    "conf": "Conf",
    "confirmed": "Conf",
    "tent": "Tent",
    "tentative": "Tent",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
}


def clean_text(value: str) -> str:
    """Elimina espacios duplicados y limpia valores vacíos."""
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def normalize_salesforce_date(value: str) -> tuple[str, str | None]:
    """
    Valida una fecha y la devuelve en formato Salesforce M/D/YYYY.

    Ejemplo:
    07/28/2026 -> 7/28/2026
    7/28/2026  -> 7/28/2026
    """
    cleaned_value = clean_text(value)

    if not cleaned_value:
        return "", None

    accepted_formats = [
        "%m/%d/%Y",
        "%m/%d/%y",
    ]

    for date_format in accepted_formats:
        try:
            parsed_date = datetime.strptime(cleaned_value, date_format)

            salesforce_date = (
                f"{parsed_date.month}/"
                f"{parsed_date.day}/"
                f"{parsed_date.year}"
            )

            return salesforce_date, None

        except ValueError:
            continue

    return cleaned_value, f"Fecha inválida: {cleaned_value}"


def normalize_boolean(value: str) -> tuple[bool | None, str | None]:
    """Convierte símbolos y textos del reporte en booleanos."""
    cleaned_value = clean_text(value)
    normalized_value = cleaned_value.lower()

    if normalized_value in TRUE_VALUES:
        return True, None

    if normalized_value in FALSE_VALUES:
        return False, None

    return None, f"Valor booleano no reconocido: {cleaned_value}"


def normalize_status(value: str) -> tuple[str, str | None]:
    """Normaliza los estados conocidos de Salesforce."""
    cleaned_value = clean_text(value)

    if not cleaned_value:
        return "", "Status vacío"

    normalized_value = cleaned_value.lower()

    if normalized_value in STATUS_MAPPING:
        return STATUS_MAPPING[normalized_value], None

    return cleaned_value, f"Status no reconocido: {cleaned_value}"


def normalize_record(
    record: dict,
    row_number: int,
) -> tuple[dict, list[str]]:
    """Normaliza una fila y devuelve los problemas detectados."""
    issues = []

    normalized_record = {
        key: clean_text(value)
        for key, value in record.items()
    }

    start_date, start_date_issue = normalize_salesforce_date(
        normalized_record.get("start_date", "")
    )

    end_date, end_date_issue = normalize_salesforce_date(
        normalized_record.get("end_date", "")
    )

    status, status_issue = normalize_status(
        normalized_record.get("status", "")
    )

    ignore_reporting, ignore_reporting_issue = normalize_boolean(
        normalized_record.get("ignore_reporting", "")
    )

    normalized_record["start_date"] = start_date
    normalized_record["end_date"] = end_date
    normalized_record["status"] = status
    normalized_record["ignore_reporting"] = ignore_reporting

    if start_date_issue:
        issues.append(start_date_issue)

    if end_date_issue:
        issues.append(end_date_issue)

    if status_issue:
        issues.append(status_issue)

    if ignore_reporting_issue:
        issues.append(ignore_reporting_issue)

    required_fields = [
        "start_date",
        "client_name",
        "project_name",
        "status",
    ]

    for field_name in required_fields:
        if normalized_record.get(field_name) in ("", None):
            issues.append(f"Campo obligatorio vacío: {field_name}")

    normalized_record["validation_status"] = (
        "VALID" if not issues else "REVIEW"
    )

    normalized_record["validation_issues"] = " | ".join(issues)

    return normalized_record, issues


def load_records(input_path: Path) -> list[dict]:
    """Carga el CSV crudo generado en el paso anterior."""
    with input_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(DictReader(file))


def save_csv(records: list[dict], output_path: Path) -> None:
    """Guarda los registros normalizados en CSV."""
    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = DictWriter(
            file,
            fieldnames=OUTPUT_COLUMNS,
        )

        writer.writeheader()
        writer.writerows(records)


def save_json(records: list[dict], output_path: Path) -> None:
    """Guarda una lista de registros en JSON."""
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )


def main() -> None:
    print("=" * 80)
    print("NORMALIZACIÓN Y VALIDACIÓN NPS")
    print("=" * 80)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de entrada:\n{INPUT_CSV}"
        )

    records = load_records(INPUT_CSV)

    normalized_records = []
    validation_results = []

    for row_number, record in enumerate(records, start=1):
        normalized_record, issues = normalize_record(
            record,
            row_number,
        )

        normalized_records.append(normalized_record)

        if issues:
            validation_results.append(
                {
                    "row_number": row_number,
                    "client_name": normalized_record.get(
                        "client_name",
                        "",
                    ),
                    "project_name": normalized_record.get(
                        "project_name",
                        "",
                    ),
                    "issues": issues,
                }
            )

    save_csv(normalized_records, NORMALIZED_CSV)
    save_json(normalized_records, NORMALIZED_JSON)
    save_json(validation_results, VALIDATION_JSON)

    valid_records = [
        record
        for record in normalized_records
        if record["validation_status"] == "VALID"
    ]

    review_records = [
        record
        for record in normalized_records
        if record["validation_status"] == "REVIEW"
    ]

    ignore_true = sum(
        record["ignore_reporting"] is True
        for record in normalized_records
    )

    ignore_false = sum(
        record["ignore_reporting"] is False
        for record in normalized_records
    )

    print(f"Registros recibidos: {len(records)}")
    print(f"Registros normalizados: {len(normalized_records)}")
    print(f"Registros válidos: {len(valid_records)}")
    print(f"Registros para revisar: {len(review_records)}")
    print()
    print(f"Ignore Reporting = True: {ignore_true}")
    print(f"Ignore Reporting = False: {ignore_false}")
    print()
    print(f"CSV normalizado: {NORMALIZED_CSV}")
    print(f"JSON normalizado: {NORMALIZED_JSON}")
    print(f"Reporte de validación: {VALIDATION_JSON}")

    print()
    print("VISTA PREVIA")
    print("-" * 80)

    for index, record in enumerate(
        normalized_records[:5],
        start=1,
    ):
        print(
            f"{index}. "
            f"{record['start_date']} | "
            f"{record['client_name']} | "
            f"{record['status']} | "
            f"Ignore Reporting: {record['ignore_reporting']} | "
            f"{record['validation_status']}"
        )

    print()
    print("=" * 80)

    if len(normalized_records) == 83:
        print("VALIDACIÓN DE CANTIDAD CORRECTA: 83 registros conservados.")
    else:
        print(
            "REVISIÓN NECESARIA: "
            f"se esperaban 83 registros y se obtuvieron "
            f"{len(normalized_records)}."
        )

    if not review_records:
        print("VALIDACIÓN DE CAMPOS CORRECTA: no se detectaron problemas.")
    else:
        print(
            f"REVISIÓN DE CAMPOS NECESARIA: "
            f"{len(review_records)} registros tienen observaciones."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()