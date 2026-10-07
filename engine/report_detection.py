from dataclasses import asdict, dataclass
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
import json
from pathlib import Path
import re
import unicodedata

from bs4 import BeautifulSoup

from engine.paths import config_path


CONFIG_FILE = (
    config_path("report_detection.json")
)


@dataclass
class ReportContext:
    source_file: str
    source_path: str
    subject: str
    sender_name: str
    sender_email: str
    received_at: str
    country: str
    report_type: str
    detection_method: str
    matched_pattern: str
    detection_status: str
    detection_issues: list[str]


def clean_text(value) -> str:
    """Limpia espacios y valores nulos."""
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def normalize_for_matching(value) -> str:
    """Normaliza texto para comparaciones."""
    text = clean_text(value).casefold()

    normalized = unicodedata.normalize(
        "NFKD",
        text,
    )

    without_accents = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        without_accents,
    ).strip()


def load_json(path: Path) -> dict:
    """Carga un archivo JSON."""
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def extract_body_text(message) -> str:
    """Extrae texto legible desde el cuerpo del correo."""
    text_parts = []
    html_parts = []

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()

            if disposition == "attachment":
                continue

            if content_type == "text/plain":
                try:
                    text_parts.append(
                        part.get_content()
                    )
                except Exception:
                    continue

            elif content_type == "text/html":
                try:
                    html_parts.append(
                        part.get_content()
                    )
                except Exception:
                    continue

    else:
        content_type = message.get_content_type()

        if content_type == "text/plain":
            text_parts.append(
                message.get_content()
            )

        elif content_type == "text/html":
            html_parts.append(
                message.get_content()
            )

    if text_parts:
        return clean_text(
            " ".join(text_parts)
        )

    if html_parts:
        longest_html = max(
            html_parts,
            key=len,
        )

        soup = BeautifulSoup(
            longest_html,
            "html.parser",
        )

        return clean_text(
            soup.get_text(
                " ",
                strip=True,
            )
        )

    return ""


def read_email_metadata(eml_path: Path) -> dict:
    """Lee encabezados y cuerpo de un archivo EML."""
    with eml_path.open("rb") as file:
        message = BytesParser(
            policy=policy.default
        ).parse(file)

    sender_name, sender_email = parseaddr(
        clean_text(
            message.get("From", "")
        )
    )

    date_header = clean_text(
        message.get("Date", "")
    )

    received_at = ""

    if date_header:
        try:
            parsed_date = parsedate_to_datetime(
                date_header
            )

            received_at = parsed_date.isoformat()

        except (TypeError, ValueError):
            received_at = date_header

    return {
        "subject": clean_text(
            message.get("Subject", "")
        ),
        "sender_name": clean_text(
            sender_name
        ),
        "sender_email": clean_text(
            sender_email
        ).lower(),
        "received_at": received_at,
        "body": extract_body_text(message),
    }


def build_searchable_text(
    eml_path: Path,
    metadata: dict,
    config: dict,
) -> str:
    """Combina las fuentes habilitadas."""
    sources = config.get(
        "detection_sources",
        [
            "subject",
            "body",
            "filename",
        ],
    )

    values = []

    if "subject" in sources:
        values.append(
            metadata.get("subject", "")
        )

    if "body" in sources:
        values.append(
            metadata.get("body", "")
        )

    if "filename" in sources:
        values.append(
            eml_path.stem
        )

    return " | ".join(values)


def detect_with_exact_patterns(
    searchable_text: str,
    config: dict,
) -> list[dict]:
    """Busca coincidencias completas país + tipo."""
    normalized_text = normalize_for_matching(
        searchable_text
    )

    matches = []

    for definition in config.get(
        "report_patterns",
        [],
    ):
        for pattern in definition.get(
            "patterns",
            [],
        ):
            normalized_pattern = normalize_for_matching(
                pattern
            )

            if (
                normalized_pattern
                and normalized_pattern in normalized_text
            ):
                matches.append(
                    {
                        "country": definition.get(
                            "country",
                            "",
                        ),
                        "report_type": definition.get(
                            "report_type",
                            "",
                        ),
                        "pattern": pattern,
                    }
                )

    unique_matches = []

    seen = set()

    for match in matches:
        key = (
            match["country"],
            match["report_type"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique_matches.append(match)

    return unique_matches


def find_category_matches(
    searchable_text: str,
    definitions: dict,
) -> list[str]:
    """Busca categorías individuales de fallback."""
    normalized_text = normalize_for_matching(
        searchable_text
    )

    matches = []

    for category, patterns in definitions.items():
        for pattern in patterns:
            normalized_pattern = normalize_for_matching(
                pattern
            )

            if (
                normalized_pattern
                and normalized_pattern in normalized_text
            ):
                matches.append(category)
                break

    return matches


def detect_with_fallback(
    searchable_text: str,
    config: dict,
) -> dict:
    """Detecta país y tipo por separado."""
    fallback = config.get(
        "fallback",
        {},
    )

    if not fallback.get("enabled", True):
        return {
            "country": "",
            "report_type": "",
            "issues": [
                "Fallback desactivado"
            ],
        }

    country_matches = find_category_matches(
        searchable_text=searchable_text,
        definitions=fallback.get(
            "countries",
            {},
        ),
    )

    type_matches = find_category_matches(
        searchable_text=searchable_text,
        definitions=fallback.get(
            "report_types",
            {},
        ),
    )

    issues = []

    if len(country_matches) == 1:
        country = country_matches[0]
    elif not country_matches:
        country = ""
        issues.append(
            "No se pudo detectar país"
        )
    else:
        country = ""
        issues.append(
            "Detección ambigua de país: "
            + ", ".join(country_matches)
        )

    if len(type_matches) == 1:
        report_type = type_matches[0]
    elif not type_matches:
        report_type = ""
        issues.append(
            "No se pudo detectar tipo de reporte"
        )
    else:
        report_type = ""
        issues.append(
            "Detección ambigua de tipo de reporte: "
            + ", ".join(type_matches)
        )

    return {
        "country": country,
        "report_type": report_type,
        "issues": issues,
    }


def validate_sender(
    sender_email: str,
    config: dict,
) -> list[str]:
    """Valida remitente solo cuando esté habilitado."""
    sender_config = config.get(
        "sender_validation",
        {},
    )

    if not sender_config.get(
        "enabled",
        False,
    ):
        return []

    allowed_senders = {
        clean_text(sender).lower()
        for sender in sender_config.get(
            "allowed_senders",
            [],
        )
    }

    if (
        allowed_senders
        and sender_email not in allowed_senders
    ):
        return [
            "Remitente no autorizado: "
            f"{sender_email or '[vacío]'}"
        ]

    return []


def detect_report(
    eml_path: Path,
    config: dict,
) -> ReportContext:
    """Detecta país y tipo de un reporte."""
    issues = []

    metadata = read_email_metadata(
        eml_path
    )

    issues.extend(
        validate_sender(
            sender_email=metadata[
                "sender_email"
            ],
            config=config,
        )
    )

    searchable_text = build_searchable_text(
        eml_path=eml_path,
        metadata=metadata,
        config=config,
    )

    exact_matches = detect_with_exact_patterns(
        searchable_text=searchable_text,
        config=config,
    )

    country = ""
    report_type = ""
    detection_method = ""
    matched_pattern = ""

    if len(exact_matches) == 1:
        exact_match = exact_matches[0]

        country = exact_match["country"]
        report_type = exact_match[
            "report_type"
        ]
        detection_method = "EXACT_PATTERN"
        matched_pattern = exact_match[
            "pattern"
        ]

    elif len(exact_matches) > 1:
        combinations = [
            (
                f"{match['country']} / "
                f"{match['report_type']}"
            )
            for match in exact_matches
        ]

        issues.append(
            "Se detectaron múltiples reportes: "
            + " | ".join(combinations)
        )

    else:
        fallback_result = detect_with_fallback(
            searchable_text=searchable_text,
            config=config,
        )

        country = fallback_result[
            "country"
        ]

        report_type = fallback_result[
            "report_type"
        ]

        issues.extend(
            fallback_result["issues"]
        )

        if country and report_type:
            detection_method = "FALLBACK"

    detection_status = (
        "DETECTED"
        if country
        and report_type
        and not issues
        else "REVIEW"
    )

    return ReportContext(
        source_file=eml_path.name,
        source_path=str(eml_path),
        subject=metadata["subject"],
        sender_name=metadata[
            "sender_name"
        ],
        sender_email=metadata[
            "sender_email"
        ],
        received_at=metadata[
            "received_at"
        ],
        country=country,
        report_type=report_type,
        detection_method=detection_method,
        matched_pattern=matched_pattern,
        detection_status=detection_status,
        detection_issues=issues,
    )


def detect_pending_reports(
    pending_directory: Path,
    config: dict,
) -> list[ReportContext]:
    """Detecta todos los EML pendientes."""
    eml_files = sorted(
        pending_directory.glob("*.eml"),
        key=lambda path: path.name.casefold(),
    )

    return [
        detect_report(
            eml_path=eml_path,
            config=config,
        )
        for eml_path in eml_files
    ]


def load_detection_config() -> dict:
    """Carga la configuración de detección."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            "No se encontró la configuración:\n"
            f"{CONFIG_FILE}"
        )

    return load_json(CONFIG_FILE)


def context_to_dict(
    context: ReportContext,
) -> dict:
    """Convierte ReportContext a diccionario."""
    return asdict(context)
