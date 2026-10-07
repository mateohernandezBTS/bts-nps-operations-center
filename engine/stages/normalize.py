from datetime import datetime


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


def clean_text(value) -> str:
    """Elimina espacios duplicados y limpia valores nulos."""
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def normalize_salesforce_date(
    value: str,
) -> tuple[str, str | None]:
    """
    Valida y devuelve una fecha en formato Salesforce M/D/YYYY.
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
            parsed_date = datetime.strptime(
                cleaned_value,
                date_format,
            )

            salesforce_date = (
                f"{parsed_date.month}/"
                f"{parsed_date.day}/"
                f"{parsed_date.year}"
            )

            return salesforce_date, None

        except ValueError:
            continue

    return cleaned_value, (
        f"Fecha inválida: {cleaned_value}"
    )


def normalize_boolean(
    value: str,
) -> tuple[bool | None, str | None]:
    """Convierte símbolos y textos en booleanos."""
    cleaned_value = clean_text(value)
    normalized_value = cleaned_value.lower()

    if normalized_value in TRUE_VALUES:
        return True, None

    if normalized_value in FALSE_VALUES:
        return False, None

    return None, (
        "Valor booleano no reconocido: "
        f"{cleaned_value}"
    )


def normalize_status(
    value: str,
) -> tuple[str, str | None]:
    """Normaliza los estados conocidos de Salesforce."""
    cleaned_value = clean_text(value)

    if not cleaned_value:
        return "", "Status vacío"

    normalized_value = cleaned_value.lower()

    if normalized_value in STATUS_MAPPING:
        return (
            STATUS_MAPPING[normalized_value],
            None,
        )

    return cleaned_value, (
        f"Status no reconocido: {cleaned_value}"
    )


def normalize_record(
    record: dict,
    row_number: int,
) -> tuple[dict, list[str]]:
    """Normaliza una fila y devuelve sus observaciones."""
    issues = []

    normalized_record = {
        key: clean_text(value)
        for key, value in record.items()
    }

    start_date, start_date_issue = (
        normalize_salesforce_date(
            normalized_record.get(
                "start_date",
                "",
            )
        )
    )

    end_date, end_date_issue = (
        normalize_salesforce_date(
            normalized_record.get(
                "end_date",
                "",
            )
        )
    )

    status, status_issue = normalize_status(
        normalized_record.get(
            "status",
            "",
        )
    )

    (
        ignore_reporting,
        ignore_reporting_issue,
    ) = normalize_boolean(
        normalized_record.get(
            "ignore_reporting",
            "",
        )
    )

    normalized_record["start_date"] = start_date
    normalized_record["end_date"] = end_date
    normalized_record["status"] = status
    normalized_record[
        "ignore_reporting"
    ] = ignore_reporting

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
        if normalized_record.get(
            field_name
        ) in ("", None):
            issues.append(
                "Campo obligatorio vacío: "
                f"{field_name}"
            )

    normalized_record["validation_status"] = (
        "VALID"
        if not issues
        else "REVIEW"
    )

    normalized_record["validation_issues"] = (
        " | ".join(issues)
    )

    return normalized_record, issues


def normalize_records(
    records: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    Normaliza todos los registros.

    Devuelve:
    - registros normalizados;
    - observaciones de validación.
    """
    normalized_records = []
    validation_results = []

    for row_number, record in enumerate(
        records,
        start=1,
    ):
        normalized_record, issues = (
            normalize_record(
                record=record,
                row_number=row_number,
            )
        )

        normalized_records.append(
            normalized_record
        )

        if issues:
            validation_results.append(
                {
                    "row_number": row_number,
                    "client_name": (
                        normalized_record.get(
                            "client_name",
                            "",
                        )
                    ),
                    "project_name": (
                        normalized_record.get(
                            "project_name",
                            "",
                        )
                    ),
                    "issues": issues,
                }
            )

    return (
        normalized_records,
        validation_results,
    )