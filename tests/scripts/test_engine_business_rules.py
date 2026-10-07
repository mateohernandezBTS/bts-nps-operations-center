from collections import Counter
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
from engine.stages.business_rules import (
    apply_business_rules,
)


INPUT_FILE = (
    PROJECT_DIR
    / "input"
    / "pending"
    / "brazil_upcoming_test.eml"
)


def main() -> None:
    print("=" * 80)
    print("PRUEBA DEL MOTOR UNIVERSAL DE REGLAS NPS")
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

    results = apply_business_rules(
        normalized_records
    )

    classified_records = results[
        "classified"
    ]

    eligible_records = results[
        "eligible"
    ]

    excluded_records = results[
        "excluded"
    ]

    review_records = results[
        "review"
    ]

    print(
        f"Registros procesados: "
        f"{len(classified_records)}"
    )

    print(
        f"Elegibles: "
        f"{len(eligible_records)}"
    )

    print(
        f"Excluidos: "
        f"{len(excluded_records)}"
    )

    print(
        f"Para revisar: "
        f"{len(review_records)}"
    )

    print()
    print("RESUMEN POR MOTIVO PRINCIPAL")
    print("-" * 80)

    counts = Counter(
        record["decision_code"]
        for record in classified_records
    )

    for code, count in sorted(
        counts.items(),
        key=lambda item: (
            item[0]
        ),
    ):
        print(
            f"{count:>3} | {code}"
        )

    print()
    print("EJEMPLOS CON MÚLTIPLES MOTIVOS")
    print("-" * 80)

    multi_reason_records = [
        record
        for record in excluded_records
        if " | " in record[
            "decision_codes"
        ]
    ]

    for record in multi_reason_records[:5]:
        print(
            f"{record['client_name']} | "
            f"{record['project_name']} | "
            f"{record['decision_codes']}"
        )

    print()
    print("=" * 80)

    expected_result = (
        len(classified_records) == 83
        and len(eligible_records) == 38
        and len(excluded_records) == 45
        and len(review_records) == 0
        and not validation_results
    )

    if expected_result:
        print(
            "VALIDACIÓN CORRECTA: "
            "el motor universal reprodujo "
            "la clasificación esperada."
        )
    else:
        print(
            "REVISIÓN NECESARIA: "
            "la clasificación modular "
            "presentó diferencias."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()