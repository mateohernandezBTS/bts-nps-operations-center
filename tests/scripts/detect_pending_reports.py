import json
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent
PROJECT_DIR = TESTS_DIR.parent

sys.path.insert(
    0,
    str(PROJECT_DIR),
)

from engine.report_detection import (
    context_to_dict,
    detect_pending_reports,
    load_detection_config,
)


PENDING_DIRECTORY = (
    PROJECT_DIR
    / "input"
    / "pending"
)

OUTPUT_FILE = (
    TESTS_DIR
    / "output"
    / "pending_report_detection.json"
)


def main() -> None:
    print("=" * 80)
    print("DETECCIÓN AUTOMÁTICA DE REPORTES NPS")
    print("=" * 80)

    config = load_detection_config()

    contexts = detect_pending_reports(
        pending_directory=PENDING_DIRECTORY,
        config=config,
    )

    results = [
        context_to_dict(context)
        for context in contexts
    ]

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )

    detected_count = sum(
        context.detection_status == "DETECTED"
        for context in contexts
    )

    review_count = sum(
        context.detection_status == "REVIEW"
        for context in contexts
    )

    print(
        f"Archivos EML encontrados: "
        f"{len(contexts)}"
    )

    print(
        f"Detectados correctamente: "
        f"{detected_count}"
    )

    print(
        f"Para revisar: "
        f"{review_count}"
    )

    print()
    print("RESULTADOS")
    print("-" * 80)

    for index, context in enumerate(
        contexts,
        start=1,
    ):
        print(
            f"{index}. {context.source_file}"
        )

        print(
            f"   Subject: "
            f"{context.subject or '[vacío]'}"
        )

        print(
            f"   Sender: "
            f"{context.sender_email or '[vacío]'}"
        )

        print(
            f"   Country: "
            f"{context.country or '[NO DETECTADO]'}"
        )

        print(
            f"   Report Type: "
            f"{context.report_type or '[NO DETECTADO]'}"
        )

        print(
            f"   Detection Method: "
            f"{context.detection_method or '[NINGUNO]'}"
        )

        print(
            f"   Matched Pattern: "
            f"{context.matched_pattern or '[NINGUNO]'}"
        )

        print(
            f"   Status: "
            f"{context.detection_status}"
        )

        if context.detection_issues:
            print(
                "   Issues: "
                + " | ".join(
                    context.detection_issues
                )
            )

        print()

    print(f"JSON generado: {OUTPUT_FILE}")

    print()
    print("=" * 80)

    if contexts and not review_count:
        print(
            "VALIDACIÓN CORRECTA: "
            "todos los reportes fueron detectados."
        )
    elif not contexts:
        print(
            "SIN ARCHIVOS: no hay reportes "
            "EML en input/pending."
        )
    else:
        print(
            "REVISIÓN NECESARIA: algunos reportes "
            "no pudieron clasificarse con certeza."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()