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
from engine.stages.worklist import (
    format_salesforce_date,
    generate_worklist,
)


INPUT_FILE = (
    PROJECT_DIR
    / "input"
    / "pending"
    / "brazil_upcoming_test.eml"
)


REFERENCE_MONDAY = "7/27/2026"


def main() -> None:
    print("=" * 80)
    print("PRUEBA DE WORKLIST UNIVERSAL NPS")
    print("=" * 80)

    raw_records = parse_eml_report(
        INPUT_FILE
    )

    (
        normalized_records,
        validation_results,
    ) = normalize_records(
        raw_records
    )

    business_results = (
        apply_business_rules(
            normalized_records
        )
    )

    worklist_result = generate_worklist(
        eligible_records=business_results[
            "eligible"
        ],
        reference_monday=REFERENCE_MONDAY,
    )

    worklist = worklist_result[
        "worklist"
    ]

    ready = worklist_result[
        "ready"
    ]

    review = worklist_result[
        "review"
    ]

    outside_window = worklist_result[
        "outside_window"
    ]

    print(
        "Elegibles recibidos: "
        f"{len(business_results['eligible'])}"
    )

    print(
        "Ventana semanal: "
        f"{format_salesforce_date(worklist_result['window_start'])} "
        "hasta "
        f"{format_salesforce_date(worklist_result['window_end'])}"
    )

    print(
        f"Dentro de ventana: "
        f"{len(worklist)}"
    )

    print(
        f"Fuera de ventana: "
        f"{len(outside_window)}"
    )

    print(
        f"READY: "
        f"{len(ready)}"
    )

    print(
        f"REVIEW: "
        f"{len(review)}"
    )

    print()
    print("VISTA PREVIA")
    print("-" * 80)

    for index, record in enumerate(
        worklist,
        start=1,
    ):
        facilitator = (
            record["Facilitator"]
            or "[VACÍO]"
        )

        print(
            f"{index}. "
            f"{record['Date']} | "
            f"{record['Session']} | "
            f"{facilitator} | "
            f"{record['Output Status']}"
        )

    print()
    print("=" * 80)

    expected_result = (
        len(business_results["eligible"])
        == 38
        and len(worklist) == 9
        and len(outside_window) == 29
        and len(ready) == 9
        and len(review) == 0
        and not validation_results
    )

    if expected_result:
        print(
            "VALIDACIÓN CORRECTA: "
            "la worklist universal reprodujo "
            "la salida semanal esperada."
        )
    else:
        print(
            "REVISIÓN NECESARIA: "
            "la worklist modular presentó diferencias."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()