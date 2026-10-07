import json
from pathlib import Path
import re
import unicodedata

from engine.paths import config_path


CONFIG_FILE = (
    config_path("business_rules.json")
)


def clean_text(value) -> str:
    """Limpia espacios y valores nulos."""
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def load_json(path: Path) -> dict:
    """Carga un archivo JSON."""
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def load_business_rules_config() -> dict:
    """Carga la configuración externa de reglas."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            "No se encontró la configuración:\n"
            f"{CONFIG_FILE}"
        )

    return load_json(CONFIG_FILE)


def normalize_for_matching(value) -> str:
    """
    Normaliza texto solo para comparaciones.

    No modifica el valor original del registro.
    """
    text = clean_text(value).casefold()

    normalized = unicodedata.normalize(
        "NFKD",
        text,
    )

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
    """Evalúa una coincidencia según la configuración."""
    normalized_value = normalize_for_matching(
        field_value
    )

    normalized_pattern = normalize_for_matching(
        pattern
    )

    if match_type == "contains_any":
        return normalized_pattern in normalized_value

    if match_type == "equals_any":
        return normalized_value == normalized_pattern

    if match_type == "starts_with_any":
        return normalized_value.startswith(
            normalized_pattern
        )

    if match_type == "regex_any":
        return bool(
            re.search(
                pattern,
                field_value or "",
                flags=re.IGNORECASE,
            )
        )

    raise ValueError(
        "Tipo de coincidencia no reconocido: "
        f"{match_type}"
    )


def classify_record(
    record: dict,
    config: dict,
) -> dict:
    """Clasifica un registro con múltiples motivos."""
    classified = dict(record)

    exclude_codes = []
    exclude_reasons = []

    review_codes = []
    review_reasons = []

    matched_rules = []
    matched_fields = []
    matched_patterns = []

    if record.get("validation_status") != "VALID":
        validation_reason = record.get(
            "validation_issues",
            "El registro tiene observaciones de validación.",
        )

        classified.update(
            {
                "decision": "REVIEW",
                "decision_code": "VALIDATION_ISSUE",
                "decision_reason": validation_reason,
                "matched_rule": "",
                "matched_field": "",
                "matched_pattern": "",
                "decision_codes": "VALIDATION_ISSUE",
                "decision_reasons": validation_reason,
                "matched_rules": "",
                "matched_fields": "",
                "matched_patterns": "",
            }
        )

        return classified

    eligibility = config.get(
        "eligibility",
        {},
    )

    allowed_statuses = eligibility.get(
        "allowed_statuses",
        [],
    )

    status = record.get(
        "status",
        "",
    )

    if (
        allowed_statuses
        and status not in allowed_statuses
    ):
        exclude_codes.append(
            "STATUS_NOT_ELIGIBLE"
        )

        exclude_reasons.append(
            f"Status {status} no incluido "
            "en los estados elegibles."
        )

    require_ignore_false = eligibility.get(
        "require_ignore_reporting_false",
        True,
    )

    if (
        require_ignore_false
        and record.get("ignore_reporting")
        is not False
    ):
        exclude_codes.append(
            "IGNORE_REPORTING"
        )

        exclude_reasons.append(
            "Ignore Reporting no es False."
        )

    for rule in config.get(
        "exclusion_rules",
        [],
    ):
        if not rule.get(
            "enabled",
            False,
        ):
            continue

        rule_id = rule.get(
            "id",
            "UNNAMED_RULE",
        )

        rule_action = clean_text(
            rule.get(
                "action",
                "EXCLUDE",
            )
        ).upper()

        fields = rule.get(
            "fields",
            [],
        )

        patterns = rule.get(
            "patterns",
            [],
        )

        match_type = rule.get(
            "match_type",
            "contains_any",
        )

        rule_matched = False

        for field_name in fields:
            field_value = record.get(
                field_name,
                "",
            )

            for pattern in patterns:
                if not matches_pattern(
                    field_value=field_value,
                    pattern=pattern,
                    match_type=match_type,
                ):
                    continue

                if not rule_matched:
                    rule_description = rule.get(
                        "description",
                        rule_id,
                    )

                    if rule_action == "REVIEW":
                        review_codes.append(
                            rule_id
                        )

                        review_reasons.append(
                            rule_description
                        )

                    elif rule_action == "EXCLUDE":
                        exclude_codes.append(
                            rule_id
                        )

                        exclude_reasons.append(
                            rule_description
                        )

                    else:
                        raise ValueError(
                            "Acción de regla no reconocida: "
                            f"{rule_action} en {rule_id}"
                        )

                    matched_rules.append(
                        rule_id
                    )

                    rule_matched = True

                matched_fields.append(
                    field_name
                )

                matched_patterns.append(
                    pattern
                )

    if exclude_codes:
        decision = "EXCLUDED"
        primary_code = exclude_codes[0]
        primary_reason = exclude_reasons[0]

        decision_codes = (
            exclude_codes
            + review_codes
        )

        decision_reasons = (
            exclude_reasons
            + review_reasons
        )

    elif review_codes:
        decision = "REVIEW"
        primary_code = review_codes[0]
        primary_reason = review_reasons[0]

        decision_codes = list(
            review_codes
        )

        decision_reasons = list(
            review_reasons
        )

    else:
        decision = "ELIGIBLE"
        primary_code = "ALL_RULES_PASSED"
        primary_reason = (
            "El registro cumple todos "
            "los criterios configurados."
        )

        decision_codes = [
            primary_code
        ]

        decision_reasons = [
            primary_reason
        ]

    classified.update(
        {
            "decision": decision,
            "decision_code": primary_code,
            "decision_reason": primary_reason,
            "matched_rule": (
                matched_rules[0]
                if matched_rules
                else ""
            ),
            "matched_field": (
                matched_fields[0]
                if matched_fields
                else ""
            ),
            "matched_pattern": (
                matched_patterns[0]
                if matched_patterns
                else ""
            ),
            "decision_codes": " | ".join(
                decision_codes
            ),
            "decision_reasons": " | ".join(
                decision_reasons
            ),
            "matched_rules": " | ".join(
                matched_rules
            ),
            "matched_fields": " | ".join(
                matched_fields
            ),
            "matched_patterns": " | ".join(
                matched_patterns
            ),
        }
    )

    return classified


def apply_business_rules(
    records: list[dict],
    config: dict | None = None,
) -> dict:
    """
    Clasifica todos los registros.

    Devuelve un diccionario con:
    - classified;
    - eligible;
    - excluded;
    - review.
    """
    if config is None:
        config = load_business_rules_config()

    classified_records = [
        classify_record(
            record=record,
            config=config,
        )
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

    return {
        "classified": classified_records,
        "eligible": eligible_records,
        "excluded": excluded_records,
        "review": review_records,
    }
