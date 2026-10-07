from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent
PROJECT_DIR = TESTS_DIR.parent

sys.path.insert(0, str(PROJECT_DIR))


from engine.stages.email_parser import parse_eml_report


INPUT_FILE = (
    PROJECT_DIR
    / "input"
    / "pending"
    / "brazil_upcoming_test.eml"
)


def main() -> None:
    print("=" * 80)
    print("PRUEBA DEL PARSER UNIVERSAL NPS")
    print("=" * 80)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró el correo pendiente:\n{INPUT_FILE}"
        )

    records = parse_eml_report(INPUT_FILE)

    print(f"Archivo leído: {INPUT_FILE.name}")
    print(f"Registros extraídos: {len(records)}")

    print()
    print("VISTA PREVIA")
    print("-" * 80)

    for index, record in enumerate(records[:5], start=1):
        print(
            f"{index}. "
            f"{record['start_date']} | "
            f"{record['client_name']} | "
            f"{record['project_name']} | "
            f"{record['status']}"
        )

    print()
    print("=" * 80)

    if len(records) == 83:
        print(
            "VALIDACIÓN CORRECTA: "
            "el parser universal extrajo los 83 registros."
        )
    else:
        print(
            "REVISIÓN NECESARIA: "
            f"se esperaban 83 registros y se obtuvieron {len(records)}."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()