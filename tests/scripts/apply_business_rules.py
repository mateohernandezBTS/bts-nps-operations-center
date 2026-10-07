from csv import DictWriter
import json
from pathlib import Path
import re
import unicodedata


SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent
PROJECT_DIR = TESTS_DIR.parent

INPUT_JSON = TESTS_DIR / "output" / "brazil_upcoming_normalized.json"
CONFIG_FILE = PROJECT_DIR / "config" / "business_rules.json"

OUTPUT_DIR = TESTS_DIR / "output"
CLASSIFIED_CSV = OUTPUT_DIR / "brazil_upcoming_classified.csv"
CLASSIFIED_JSON = OUTPUT_DIR / "brazil_upcoming_classified.json"
ELIGIBLE_CSV = OUTPUT_DIR / "brazil_upcoming_eligible.csv"
EXCLUDED_CSV = OUTPUT_DIR / "brazil_upcoming_excluded.csv"
REVIEW_CSV = OUTPUT_DIR / "brazil_upcoming_review.csv"


ADDITIONAL_COLUMNS = [
    "decision",
    "decision_code",
    "decision_reason",
    "matched_rule",
    "matched_field",
    "matched_pattern",
]


def load_json(path: Path):
    """Carga un archivo JSON."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_for_matching(value) -> str:
    """
    Normaliza texto únicamente para realizar comparaciones.

    No modifica el texto original almacenado en la salida.
    """
    if value is None:
        return ""

    text = " ".join(str(value).split()).casefold()

    normalized = unicodedata.normalize("NFKD", text)

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def matches_pattern(
    field_value: str,
    pattern: str,
    match_type: str,
) -> bool:
    """Evalúa una coincidencia según el tipo configurado."""
    normalized_value = normalize_for_matching(field_value)
    normalized_pattern = normalize_for_matching(pattern)

    if match_type == "contains_any":
        return normalized_pattern in normalized_value

    if match_type == "equals_any":
        return normalized_value == normalized_pattern

    if match_type == "starts_with_any":
        return normalized_value.startswith(normalized_pattern)

    if match_type == "regex_any":
        return bool(
            re.search(
                pattern,
                field_value or "",
                flags=re.IGNORECASE,
            )
        )

    raise ValueError(
        f"Tipo de coincidencia no reconocido: {match_type}"
    )


def find_exclusion(record: dict, rules: list[dict]):
    """Devuelve la primera regla de exclusión que coincida."""
    for rule in rules:
        if not rule.get("enabled", False):
            continue

        rule_id = rule.get("id", "UNNAMED_RULE")
        fields = rule.get("fields", [])
        patterns = rule.get("patterns", [])
        match_type = rule.get("match_type", "contains_any")

        for field_name in fields:
            field_value = record.get(field_name, "")

            for pattern in patterns:
                if matches_pattern(
                    field_value=field_value,
                    pattern=pattern,
                    match_type=match_type,
                ):
                    return {
                        "rule_id": rule_id,
                        "description": rule.get(
                            "description",
                            rule_id,
                        ),
                        "field": field_name,
                        "pattern": pattern,
                    }

    return None


def classify_record(record: dict, config: dict) -> dict:
    """Aplica validación, elegibilidad y exclusiones configurables."""
    classified = dict(record)

    decision_codes = []
    decision_reasons = []
    matched_rules = []
    matched_fields = []
    matched_patterns = []

    # Un registro con problemas técnicos no se descarta.
    # Se envía a revisión manual.
    if record.get("validation_status") != "VALID":
        classified.update(
            {
                "decision": "REVIEW",
                "decision_code": "VALIDATION_ISSUE",
                "decision_reason": record.get(
                    "validation_issues",
                    "El registro tiene observaciones de validación.",
                ),
                "decision_codes": "VALIDATION_ISSUE",
                "decision_reasons": record.get(
                    "validation_issues",
                    "El registro tiene observaciones de validación.",
                ),
                "matched_rules": "",
                "matched_fields": "",
                "matched_patterns": "",
            }
        )

        return classified

    eligibility = config.get("eligibility", {})
    allowed_statuses = eligibility.get("allowed_statuses", [])

    status = record.get("status", "")

    if allowed_statuses and status not in allowed_statuses:
        decision_codes.append("STATUS_NOT_ELIGIBLE")
        decision_reasons.append(
            f"Status {status} no incluido en los estados elegibles."
        )

    require_ignore_false = eligibility.get(
        "require_ignore_reporting_false",
        True,
    )

    if (
        require_ignore_false
        and record.get("ignore_reporting") is not False
    ):
        decision_codes.append("IGNORE_REPORTING")
        decision_reasons.append("Ignore Reporting = True.")

    # A diferencia de la versión anterior, ahora seguimos buscando
    # exclusiones aunque ya exista otro motivo.
    for rule in config.get("exclusion_rules", []):
        if not rule.get("enabled", False):
            continue

        rule_id = rule.get("id", "UNNAMED_RULE")
        fields = rule.get("fields", [])
        patterns = rule.get("patterns", [])
        match_type = rule.get("match_type", "contains_any")

        rule_matched = False

        for field_name in fields:
            field_value = record.get(field_name, "")

            for pattern in patterns:
                if matches_pattern(
                    field_value=field_value,
                    pattern=pattern,
                    match_type=match_type,
                ):
                    if not rule_matched:
                        decision_codes.append(rule_id)
                        decision_reasons.append(
                            rule.get("description", rule_id)
                        )
                        matched_rules.append(rule_id)
                        rule_matched = True

                    matched_fields.append(field_name)
                    matched_patterns.append(pattern)

    if decision_codes:
        decision = "EXCLUDED"
        primary_code = decision_codes[0]
        primary_reason = decision_reasons[0]
    else:
        decision = "ELIGIBLE"
        primary_code = "ALL_RULES_PASSED"
        primary_reason = (
            "El registro cumple todos los criterios configurados."
        )
        decision_codes.append(primary_code)
        decision_reasons.append(primary_reason)

    classified.update(
        {
            "decision": decision,
            "decision_code": primary_code,
            "decision_reason": primary_reason,
            "matched_rule": matched_rules[0] if matched_rules else "",
            "matched_field": matched_fields[0] if matched_fields else "",
            "matched_pattern": matched_patterns[0] if matched_patterns else "",
            "decision_codes": " | ".join(decision_codes),
            "decision_reasons": " | ".join(decision_reasons),
            "matched_rules": " | ".join(matched_rules),
            "matched_fields": " | ".join(matched_fields),
            "matched_patterns": " | ".join(matched_patterns),
        }
    )

    return classified


def save_csv(records: list[dict], output_path: Path) -> None:
    """Guarda registros con encabezados consistentes."""
    if not records:
        output_path.write_text("", encoding="utf-8-sig")
        return

    fieldnames = list(records[0].keys())

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(records)


def save_json(records: list[dict], output_path: Path) -> None:
    """Guarda registros en JSON."""
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )


def print_reason_summary(records: list[dict]) -> None:
    """Muestra un resumen por decisión y motivo."""
    counts = {}

    for record in records:
        key = (
            record["decision"],
            record["decision_code"],
        )

        counts[key] = counts.get(key, 0) + 1

    print()
    print("RESUMEN POR MOTIVO")
    print("-" * 80)

    for key in sorted(counts):
        decision, code = key
        count = counts[key]

        print(
            f"{count:>3} | "
            f"{decision:<8} | "
            f"{code}"
        )


def main() -> None:
    print("=" * 80)
    print("MOTOR DE REGLAS DE NEGOCIO NPS")
    print("=" * 80)

    if not INPUT_JSON.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo normalizado:\n{INPUT_JSON}"
        )

    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró la configuración:\n{CONFIG_FILE}"
        )

    records = load_json(INPUT_JSON)
    config = load_json(CONFIG_FILE)

    classified_records = [
        classify_record(record, config)
        for record in records
    ]

    eligible_records = [
        record
        for record in classified_records
        if record["decision"] == "ELIGIBLE"
    ]

    excluded_records = [
        record
        for record in classified_records
        if record["decision"] == "EXCLUDED"
    ]

    review_records = [
        record
        for record in classified_records
        if record["decision"] == "REVIEW"
    ]

    save_csv(classified_records, CLASSIFIED_CSV)
    save_json(classified_records, CLASSIFIED_JSON)
    save_csv(eligible_records, ELIGIBLE_CSV)
    save_csv(excluded_records, EXCLUDED_CSV)
    save_csv(review_records, REVIEW_CSV)

    print(f"Configuración utilizada: {CONFIG_FILE}")
    print(f"Versión de reglas: {config.get('version', 'sin versión')}")
    print()
    print(f"Registros procesados: {len(classified_records)}")
    print(f"Elegibles: {len(eligible_records)}")
    print(f"Excluidos: {len(excluded_records)}")
    print(f"Para revisar: {len(review_records)}")

    print_reason_summary(classified_records)

    print()
    print("ARCHIVOS GENERADOS")
    print("-" * 80)
    print(f"Clasificación completa: {CLASSIFIED_CSV}")
    print(f"Solo elegibles: {ELIGIBLE_CSV}")
    print(f"Solo excluidos: {EXCLUDED_CSV}")
    print(f"Revisión manual: {REVIEW_CSV}")

    print()
    print("=" * 80)

    if len(classified_records) == len(records):
        print(
            "VALIDACIÓN CORRECTA: todos los registros fueron clasificados."
        )
    else:
        print(
            "ERROR: no todos los registros recibieron una clasificación."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()