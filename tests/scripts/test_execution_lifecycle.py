from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent
PROJECT_DIR = TESTS_DIR.parent

sys.path.insert(
    0,
    str(PROJECT_DIR),
)


from engine.execution_manager import (
    create_execution,
    ensure_directories,
    load_system_config,
    return_to_pending_after_test,
    update_execution,
)


PENDING_FILE = (
    PROJECT_DIR
    / "input"
    / "pending"
    / "brazil_upcoming_test.eml"
)


def main() -> None:
    print("=" * 80)
    print("PRUEBA DEL CICLO DE VIDA NPS")
    print("=" * 80)

    config = load_system_config()

    directories = ensure_directories(
        config
    )

    if not PENDING_FILE.exists():
        raise FileNotFoundError(
            "No se encontró el correo de prueba en pending:\n"
            f"{PENDING_FILE}"
        )

    print(f"Archivo pendiente: {PENDING_FILE.name}")

    context = create_execution(
        source_path=PENDING_FILE,
        config=config,
        directories=directories,
    )

    print()
    print(f"Execution ID: {context.execution_id}")
    print(f"Estado inicial: {context.execution_status}")
    print(f"Archivo en processing: {context.processing_path}")
    print(f"Carpeta de ejecución: {context.run_directory}")

    update_execution(
        context=context,
        stage="REPORT_DETECTION_TEST",
        status="RUNNING",
    )

    processing_path = Path(
        context.processing_path
    )

    if not processing_path.exists():
        raise RuntimeError(
            "El archivo no fue movido correctamente a processing."
        )

    print()
    print("Movimiento a processing: CORRECTO")

    returned_path = return_to_pending_after_test(
        context=context,
        directories=directories,
    )

    print(f"Archivo devuelto a pending: {returned_path}")
    print(f"Estado final: {context.execution_status}")

    manifest_path = (
        Path(context.run_directory)
        / "execution_manifest.json"
    )

    log_path = (
        directories["logs"]
        / f"{context.execution_id}.json"
    )

    print()
    print("ARCHIVOS DE CONTROL")
    print("-" * 80)
    print(f"Manifest: {manifest_path}")
    print(f"Log: {log_path}")

    print()
    print("=" * 80)

    if (
        returned_path.exists()
        and manifest_path.exists()
        and log_path.exists()
        and context.execution_status == "TEST_COMPLETED"
    ):
        print(
            "VALIDACIÓN CORRECTA: "
            "el ciclo de vida de prueba se completó."
        )
    else:
        print(
            "REVISIÓN NECESARIA: "
            "el ciclo de vida no quedó completo."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()