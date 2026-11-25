"""Country registry: markets, Salesforce values, surveys and languages.

Everything that differs between markets lives in ``config/v2/countries.json``. Loading
fails closed: any inconsistency raises :class:`RegistryError` instead of producing a
partial registry.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.paths import config_path
from nps_v2.domain import DomainError, SalesforceId

DEFAULT_REGISTRY_PATH_PARTS = ("v2", "countries.json")


class RegistryError(ValueError):
    """The country registry configuration is invalid."""


@dataclass(frozen=True, slots=True)
class SurveyRef:
    key: str
    survey_id: SalesforceId
    name: str


@dataclass(frozen=True, slots=True)
class Country:
    code: str
    name: str
    billing_country_values: tuple[str, ...]
    language: str
    nps_survey: SurveyRef
    facilitators_survey: SurveyRef
    slack_section: str


@dataclass(frozen=True, slots=True)
class CountryRegistry:
    version: str
    countries: tuple[Country, ...]
    facilitator_family: frozenset[SalesforceId]

    def by_code(self, code: str) -> Country:
        wanted = code.strip().upper()
        for country in self.countries:
            if country.code == wanted:
                return country
        known = ", ".join(c.code for c in self.countries)
        raise RegistryError(f"Unknown country code {code!r} (known: {known})")

    def country_for_billing(self, billing_country: str) -> Country | None:
        """Return the market of a ``Billing_Country__c`` value, or ``None``."""
        wanted = billing_country.strip().casefold()
        for country in self.countries:
            if wanted in (v.casefold() for v in country.billing_country_values):
                return country
        return None

    def billing_values(self, codes: Iterable[str] = ()) -> tuple[str, ...]:
        """Billing values for the given country codes (all countries when empty)."""
        selected = [self.by_code(c) for c in codes] or list(self.countries)
        return tuple(v for country in selected for v in country.billing_country_values)

    def is_facilitator_survey(self, survey_id: SalesforceId | None) -> bool:
        return survey_id is not None and survey_id in self.facilitator_family


def load_registry(path: Path | None = None) -> CountryRegistry:
    """Load and validate the registry (default: ``config/v2/countries.json``)."""
    registry_path = path or config_path(*DEFAULT_REGISTRY_PATH_PARTS)
    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RegistryError(f"Cannot read registry {registry_path}: {error}") from error
    return parse_registry(raw)


def parse_registry(raw: Mapping[str, Any]) -> CountryRegistry:
    """Validate a registry document already parsed from JSON."""
    if not isinstance(raw, Mapping):
        raise RegistryError("Registry root must be an object")

    languages = frozenset(_string_list(raw, "supported_languages"))
    surveys = _parse_surveys(_required(raw, "surveys", Mapping))
    family = _parse_family(_required(raw, "facilitator_survey_family", list))

    raw_countries = _required(raw, "countries", list)
    if not raw_countries:
        raise RegistryError("Registry must define at least one country")

    countries = tuple(
        _parse_country(item, surveys, languages, family) for item in raw_countries
    )
    _ensure_unique(countries)

    return CountryRegistry(
        version=str(_required(raw, "version", str)),
        countries=countries,
        facilitator_family=family,
    )


def _parse_surveys(raw: Mapping[str, Any]) -> dict[str, SurveyRef]:
    if not raw:
        raise RegistryError("Registry must define surveys")
    return {
        key: SurveyRef(
            key=key,
            survey_id=_salesforce_id(_required(item, "id", str), f"surveys.{key}"),
            name=_required(item, "name", str),
        )
        for key, item in raw.items()
    }


def _parse_family(raw: list[Any]) -> frozenset[SalesforceId]:
    if not raw:
        raise RegistryError("facilitator_survey_family must not be empty")
    return frozenset(
        _salesforce_id(_required(item, "id", str), "facilitator_survey_family")
        for item in raw
    )


def _parse_country(
    raw: Any,
    surveys: Mapping[str, SurveyRef],
    languages: frozenset[str],
    family: frozenset[SalesforceId],
) -> Country:
    if not isinstance(raw, Mapping):
        raise RegistryError("Each country must be an object")
    code = _required(raw, "code", str).strip().upper()
    where = f"country {code or '?'}"

    language = _required(raw, "language", str)
    if language not in languages:
        raise RegistryError(f"{where}: unsupported language {language!r}")

    facilitators = _survey(surveys, _required(raw, "facilitators_survey", str), where)
    if facilitators.survey_id not in family:
        raise RegistryError(
            f"{where}: facilitators survey {facilitators.key!r} "
            "is not in facilitator_survey_family"
        )
    nps = _survey(surveys, _required(raw, "nps_survey", str), where)
    if nps.survey_id in family:
        raise RegistryError(f"{where}: NPS survey {nps.key!r} is a facilitator survey")

    billing_values = tuple(
        v.strip() for v in _string_list(raw, "billing_country_values")
    )
    if not billing_values or any(not v for v in billing_values):
        raise RegistryError(f"{where}: billing_country_values must be non-empty")

    return Country(
        code=code,
        name=_required(raw, "name", str),
        billing_country_values=billing_values,
        language=language,
        nps_survey=nps,
        facilitators_survey=facilitators,
        slack_section=_required(raw, "slack_section", str),
    )


def _ensure_unique(countries: tuple[Country, ...]) -> None:
    seen_codes: set[str] = set()
    seen_values: dict[str, str] = {}
    for country in countries:
        if not country.code:
            raise RegistryError("Country code must not be empty")
        if country.code in seen_codes:
            raise RegistryError(f"Duplicate country code {country.code!r}")
        seen_codes.add(country.code)
        for value in country.billing_country_values:
            owner = seen_values.setdefault(value.casefold(), country.code)
            if owner != country.code:
                raise RegistryError(
                    f"Billing value {value!r} belongs to both "
                    f"{owner} and {country.code}"
                )


def _survey(surveys: Mapping[str, SurveyRef], key: str, where: str) -> SurveyRef:
    try:
        return surveys[key]
    except KeyError:
        raise RegistryError(f"{where}: unknown survey key {key!r}") from None


def _salesforce_id(value: str, where: str) -> SalesforceId:
    try:
        return SalesforceId(value)
    except DomainError as error:
        raise RegistryError(f"{where}: {error}") from error


def _string_list(raw: Mapping[str, Any], key: str) -> list[str]:
    values = _required(raw, key, list)
    if not all(isinstance(v, str) for v in values):
        raise RegistryError(f"{key!r} must contain only strings")
    return values


def _required(raw: Mapping[str, Any], key: str, expected: type) -> Any:
    if not isinstance(raw, Mapping):
        raise RegistryError(f"Expected an object containing {key!r}")
    if key not in raw:
        raise RegistryError(f"Missing required key {key!r}")
    value = raw[key]
    if not isinstance(value, expected) or (
        isinstance(value, str) and not value.strip()
    ):
        raise RegistryError(f"Key {key!r} must be a non-empty {expected.__name__}")
    return value
