from collections import Counter
from csv import DictWriter
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import sys
import traceback


PROJECT_DIR = Path(__file__).resolve().parent.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_DIR),
    )


from engine.execution_manager import (
    complete_execution,
    create_execution,
    ensure_directories,
    fail_execution,
    load_system_config,
    update_execution,
)
from engine.report_detection import (
    context_to_dict,
    detect_report,
    load_detection_config,
)
from engine.stages.business_rules import (
    apply_business_rules,
    load_business_rules_config,
)
from engine.stages.email_parser import (
    parse_eml_report,
)
from engine.stages.normalize import (
    normalize_records,
)
from engine.stages.slack_output import (
    SLACK_COLUMNS,
    generate_slack_output,
)
from engine.stages.worklist import (
    format_salesforce_date,
    generate_worklist,
    load_operational_config,
)


def save_json(
    data,
    output_path: Path,
) -> None:
    """Guarda datos como JSON."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def save_csv(
    records: list[dict],
    output_path: Path,
    fieldnames: list[str] | None = None,
) -> None:
    """Guarda una lista de registros en CSV."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if fieldnames is None:
        if records:
            fieldnames = list(
                records[0].keys()
            )
        else:
            fieldnames = []

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        if not fieldnames:
            return

        writer = DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(records)


def find_pending_file(
    pending_directory: Path,
) -> Path:
    """Devuelve el primer correo pendiente."""
    pending_files = sorted(
        pending_directory.glob("*.eml"),
        key=lambda path: (
            path.stat().st_mtime,
            path.name.casefold(),
        ),
    )

    if not pending_files:
        raise FileNotFoundError(
            "No hay archivos .eml en input/pending."
        )

    return pending_files[0]


def build_execution_summary(
    report_context,
    raw_records: list[dict],
    normalized_records: list[dict],
    validation_results: list[dict],
    business_results: dict,
    worklist_result: dict,
    slack_result: dict,
    reference_monday: str,
) -> dict:
    """Crea el resumen final de la ejecución."""
    decision_counts = Counter(
        record["decision_code"]
        for record in business_results[
            "classified"
        ]
    )

    return {
        "report": context_to_dict(
            report_context
        ),
        "reference_monday": reference_monday,
        "window_start": format_salesforce_date(
            worklist_result["window_start"]
        ),
        "window_end": format_salesforce_date(
            worklist_result["window_end"]
        ),
        "counts": {
            "raw_records": len(
                raw_records
            ),
            "normalized_records": len(
                normalized_records
            ),
            "validation_issues": len(
                validation_results
            ),
            "eligible": len(
                business_results["eligible"]
            ),
            "excluded": len(
                business_results["excluded"]
            ),
            "business_review": len(
                business_results["review"]
            ),
            "inside_weekly_window": len(
                worklist_result["worklist"]
            ),
            "outside_weekly_window": len(
                worklist_result[
                    "outside_window"
                ]
            ),
            "worklist_ready": len(
                worklist_result["ready"]
            ),
            "worklist_review": len(
                worklist_result["review"]
            ),
            "slack_rows": len(
                slack_result["records"]
            ),
            "clients": len(
                slack_result[
                    "summary_by_client"
                ]
            ),
        },
        "decision_counts": dict(
            decision_counts
        ),
        "summary_by_client": slack_result[
            "summary_by_client"
        ],
    }


def process_report_file(
    source_path: Path,
    reference_monday: str | None = None,
    system_config_override: dict | None = None,
) -> dict:
    """
    Procesa un archivo EML específico utilizando el pipeline universal.

    El archivo se mueve mediante el ciclo de vida habitual:
    source_path -> processing -> processed/error.
    """
    source_path = Path(source_path)

    system_config = (
        system_config_override
        if system_config_override is not None
        else load_system_config()
    )

    directories = ensure_directories(
        system_config
    )

    context = create_execution(
        source_path=source_path,
        config=system_config,
        directories=directories,
    )

    run_directory = Path(
        context.run_directory
    )

    try:
        print("=" * 80)
        print("PIPELINE UNIVERSAL NPS")
        print("=" * 80)
        print(f"Execution ID: {context.execution_id}")
        print(f"Archivo: {context.source_file}")

        processing_path = Path(
            context.processing_path
        )

        update_execution(
            context=context,
            stage="REPORT_DETECTION",
            status="RUNNING",
        )

        detection_config = (
            load_detection_config()
        )

        report_context = detect_report(
            eml_path=processing_path,
            config=detection_config,
        )

        save_json(
            context_to_dict(
                report_context
            ),
            run_directory
            / "report_context.json",
        )

        if (
            report_context.detection_status
            != "DETECTED"
        ):
            raise ValueError(
                "El reporte no pudo detectarse "
                "con certeza: "
                + " | ".join(
                    report_context.detection_issues
                )
            )

        if (
            report_context.report_type
            != "Upcoming"
        ):
            raise ValueError(
                "Este pipeline MVP procesa únicamente "
                "reportes Upcoming. "
                f"Tipo detectado: "
                f"{report_context.report_type}"
            )

        print(
            "Reporte detectado: "
            f"{report_context.country} / "
            f"{report_context.report_type}"
        )

        update_execution(
            context=context,
            stage="EMAIL_PARSING",
        )

        raw_records = parse_eml_report(
            processing_path
        )

        save_csv(
            raw_records,
            run_directory / "raw.csv",
        )

        save_json(
            raw_records,
            run_directory / "raw.json",
        )

        update_execution(
            context=context,
            stage="NORMALIZATION",
        )

        (
            normalized_records,
            validation_results,
        ) = normalize_records(
            raw_records
        )

        save_csv(
            normalized_records,
            run_directory
            / "normalized.csv",
        )

        save_json(
            normalized_records,
            run_directory
            / "normalized.json",
        )

        save_json(
            validation_results,
            run_directory
            / "validation_issues.json",
        )

        update_execution(
            context=context,
            stage="BUSINESS_RULES",
        )

        business_config = (
            load_business_rules_config()
        )

        business_results = (
            apply_business_rules(
                records=normalized_records,
                config=business_config,
            )
        )

        save_csv(
            business_results[
                "classified"
            ],
            run_directory
            / "classified.csv",
        )

        save_json(
            business_results[
                "classified"
            ],
            run_directory
            / "classified.json",
        )

        save_csv(
            business_results["eligible"],
            run_directory
            / "eligible.csv",
        )

        save_csv(
            business_results["excluded"],
            run_directory
            / "excluded.csv",
        )

        business_review_path = (
        run_directory
            / "business_review.csv"
        )

        save_csv(
        business_results["review"],
        business_review_path,
        )

        update_execution(
            context=context,
            stage="WORKLIST",
        )

        operational_config = (
            load_operational_config()
        )

        if reference_monday is None:
            reference_monday = (
                operational_config.get(
                    "weekly_window",
                    {},
                ).get(
                    "reference_monday",
                    "",
                )
            )

        worklist_result = generate_worklist(
            eligible_records=business_results[
                "eligible"
            ],
            config=operational_config,
            reference_monday=reference_monday,
        )

        save_csv(
            worklist_result["worklist"],
            run_directory
            / "worklist.csv",
        )

        save_json(
            worklist_result["worklist"],
            run_directory
            / "worklist.json",
        )

        save_csv(
            worklist_result["review"],
            run_directory
            / "worklist_review.csv",
        )

        save_csv(
            worklist_result[
                "outside_window"
            ],
            run_directory
            / "outside_weekly_window.csv",
        )

        update_execution(
            context=context,
            stage="SLACK_OUTPUT",
        )

        window_start = (
            format_salesforce_date(
                worklist_result[
                    "window_start"
                ]
            )
        )

        window_end = (
            format_salesforce_date(
                worklist_result[
                    "window_end"
                ]
            )
        )

        slack_result = generate_slack_output(
            worklist_records=worklist_result[
                "worklist"
            ],
            config=operational_config,
            country=report_context.country,
            window_start=window_start,
            window_end=window_end,
        )

        save_csv(
            slack_result["records"],
            run_directory
            / "slack_ready.csv",
            fieldnames=SLACK_COLUMNS,
        )

        (
            run_directory
            / "slack_ready.md"
        ).write_text(
            slack_result["markdown"],
            encoding="utf-8",
        )

        summary = build_execution_summary(
            report_context=report_context,
            raw_records=raw_records,
            normalized_records=normalized_records,
            validation_results=validation_results,
            business_results=business_results,
            worklist_result=worklist_result,
            slack_result=slack_result,
            reference_monday=reference_monday,
        )

        save_json(
            summary,
            run_directory
            / "execution_summary.json",
        )

        update_execution(
            context=context,
            stage="FINALIZATION",
        )

        processed_path = (
            complete_execution(
                context=context,
                directories=directories,
            )
        )

        print()
        print("RESULTADO")
        print("-" * 80)
        print(
            f"Registros crudos: "
            f"{len(raw_records)}"
        )
        print(
            f"Elegibles: "
            f"{len(business_results['eligible'])}"
        )
        print(
            f"Excluidos: "
            f"{len(business_results['excluded'])}"
        )
        print(
            "Dentro de ventana: "
            f"{len(worklist_result['worklist'])}"
        )
        print(
            f"READY: "
            f"{len(worklist_result['ready'])}"
        )
        print(
            f"Clientes: "
            f"{len(slack_result['summary_by_client'])}"
        )

        print()
        print(
            f"Carpeta de ejecución: "
            f"{run_directory}"
        )
        print(
            f"Correo procesado: "
            f"{processed_path}"
        )

        print()
        print("=" * 80)
        print(
            "PIPELINE COMPLETADO CORRECTAMENTE"
        )
        print("=" * 80)

        return {
            "execution_id": context.execution_id,
            "status": "COMPLETED",
            "source_file": context.source_file,
            "country": report_context.country,
            "report_type": report_context.report_type,
            "run_directory": str(run_directory),
            "processed_path": str(processed_path),
            "execution_summary_path": str(
                run_directory
                / "execution_summary.json"
            ),
            "worklist_path": str(
                run_directory
                / "worklist.json"
            ),
            "slack_ready_path": str(
                run_directory
                / "slack_ready.md"
            ),
            "summary": summary,
            "business_review_path": str(
            business_review_path
            ),
        }

    except Exception as error:
        error_details = traceback.format_exc()

        save_json(
            {
                "error": str(error),
                "traceback": error_details,
                "failed_at": datetime.now().isoformat(),
            },
            run_directory
            / "error_details.json",
        )

        error_path = fail_execution(
            context=context,
            directories=directories,
            error_message=str(error),
        )

        print()
        print("=" * 80)
        print("PIPELINE FINALIZADO CON ERROR")
        print("=" * 80)
        print(f"Error: {error}")
        print(
            f"Correo enviado a error: "
            f"{error_path}"
        )
        print(
            f"Detalles: "
            f"{run_directory / 'error_details.json'}"
        )

        raise

def process_one_report(
    reference_monday: str | None = None,
) -> dict:
    """
    Procesa el archivo EML más antiguo de input/pending.

    Este wrapper conserva el comportamiento original del Paso 2.
    """
    system_config = load_system_config()

    directories = ensure_directories(
        system_config
    )

    source_path = find_pending_file(
        directories["pending"]
    )

    return process_report_file(
        source_path=source_path,
        reference_monday=reference_monday,
    )


def main() -> None:
    reference_monday = (
        sys.argv[1]
        if len(sys.argv) > 1
        else None
    )

    process_one_report(
        reference_monday=reference_monday
    )


if __name__ == "__main__":
    main()