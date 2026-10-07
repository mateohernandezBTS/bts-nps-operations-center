from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent
PROJECT_DIR = TESTS_DIR.parent

sys.path.insert(
    0,
    str(PROJECT_DIR),
)


from engine.stages.email_parser import (
    parse_eml_report,
)
from engine.stages.normalize import (
    normalize_records,
)


INPUT_FILE = (
    PROJECT_DIR
    / "input"
    / "pending"
    / "brazil_upcoming_test.eml"
)


def main() -> None:
    print("=" * 80)
    print("PRUEBA DE NORMALIZACIÓN UNIVERSAL NPS")
    print("=" * 80)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "No se encontró el correo pendiente:\n"
            f"{INPUT_FILE}"
        )

    raw_records = parse_eml_report(
        INPUT_FILE
    )

    (
        normalized_records,
        validation_results,
    ) = normalize_records(
        raw_records
    )

    valid_records = [
        record
        for record in normalized_records
        if (
            record["validation_status"]
            == "VALID"
        )
    ]

    review_records = [
        record
        for record in normalized_records
        if (
            record["validation_status"]
            == "REVIEW"
        )
    ]

    ignore_true = sum(
        record["ignore_reporting"] is True
        for record in normalized_records
    )

    ignore_false = sum(
        record["ignore_reporting"] is False
        for record in normalized_records
    )

    print(f"Registros crudos: {len(raw_records)}")
    print(
        "Registros normalizados: "
        f"{len(normalized_records)}"
    )
    print(
        f"Registros válidos: "
        f"{len(valid_records)}"
    )
    print(
        f"Registros para revisar: "
        f"{len(review_records)}"
    )

    print()
    print(
        "Ignore Reporting = True: "
        f"{ignore_true}"
    )
    print(
        "Ignore Reporting = False: "
        f"{ignore_false}"
    )

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
            f"Ignore Reporting: "
            f"{record['ignore_reporting']} | "
            f"{record['validation_status']}"
        )

    print()
    print("=" * 80)

    if (
        len(normalized_records) == 83
        and len(valid_records) == 83
        and not validation_results
    ):
        print(
            "VALIDACIÓN CORRECTA: "
            "los 83 registros fueron "
            "normalizados correctamente."
        )
    else:
        print(
            "REVISIÓN NECESARIA: "
            "la normalización modular "
            "presentó diferencias."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()