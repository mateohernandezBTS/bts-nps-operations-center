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
    load_operational_config,
)
from engine.stages.slack_output import (
    generate_slack_output,
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
    print("PRUEBA DE SALIDA SLACK UNIVERSAL NPS")
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

    config = load_operational_config()

    worklist_result = generate_worklist(
        eligible_records=business_results[
            "eligible"
        ],
        config=config,
        reference_monday=REFERENCE_MONDAY,
    )

    window_start = format_salesforce_date(
        worklist_result["window_start"]
    )

    window_end = format_salesforce_date(
        worklist_result["window_end"]
    )

    slack_result = generate_slack_output(
        worklist_records=worklist_result[
            "worklist"
        ],
        config=config,
        country="Brazil",
        window_start=window_start,
        window_end=window_end,
    )

    print(
        f"Filas READY incluidas: "
        f"{len(slack_result['records'])}"
    )

    print(
        f"Clientes agrupados: "
        f"{len(slack_result['summary_by_client'])}"
    )

    print()
    print("RESUMEN POR CLIENTE")
    print("-" * 80)

    for client in sorted(
        slack_result[
            "summary_by_client"
        ],
        key=str.casefold,
    ):
        count = slack_result[
            "summary_by_client"
        ][client]

        print(
            f"{count:>3} | {client}"
        )

    print()
    print("VISTA PREVIA DEL MARKDOWN")
    print("-" * 80)

    markdown_lines = (
        slack_result["markdown"]
        .splitlines()
    )

    for line in markdown_lines[:20]:
        print(line)

    print()
    print("=" * 80)

    expected_result = (
        len(slack_result["records"]) == 9
        and len(
            slack_result[
                "summary_by_client"
            ]
        ) == 6
        and not validation_results
        and (
            "# Upcoming NPS | Brazil | "
            "7/28/2026 to 8/3/2026"
            in slack_result["markdown"]
        )
    )

    if expected_result:
        print(
            "VALIDACIÓN CORRECTA: "
            "la salida Slack universal "
            "reprodujo el resultado esperado."
        )
    else:
        print(
            "REVISIÓN NECESARIA: "
            "la salida Slack modular "
            "presentó diferencias."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()