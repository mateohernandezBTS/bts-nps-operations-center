"""The creation recipe: what V2 writes to create one survey, exactly as the UI does.

Verified by reading on all 48 survey sets of one week (V2-2 plan, section 3):

1. ``SurveyInvitation``: ``Name`` = "<survey> for <project>" (cut to 255 chars),
   ``SurveyId``, ``CommunityId`` and three fixed options; the owner is the creator.
2. Salesforce generates ``InvitationLink`` (with the 15-character invitation id).
3. Link stored on the survey set = that link with the 18-character id, plus
   ``&guestUserLang=<language>``; ``QR_Code_URL__c`` = the link URL-encoded with no
   safe characters.
4. ``Survey_Set__c`` with project, survey, language, NPS flag, invitation, link and QR.
5. NPS only: the project's ``Survey_Invitation__c`` points to the NPS invitation.

Every function here is pure; the payloads are the only thing V2 ever sends.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from engine.paths import config_path
from nps_v2.domain import DomainError, SalesforceId, SurveyKind

INVITATION_OBJECT = "SurveyInvitation"
SURVEY_SET_OBJECT = "Survey_Set__c"
PROJECT_OBJECT = "rosscrooke__Project__c"
DEFAULT_CONFIG_PARTS = ("v2", "creation.json")
_FULL_ID = re.compile(r"^[A-Za-z0-9]{18}$")
_OPTION_FIELDS = (
    "OptionsAllowGuestUserResponse",
    "OptionsAllowParticipantAccessTheirResponse",
    "OptionsCollectAnonymousResponse",
)


class RecipeError(ValueError):
    """A value needed to build a payload is missing or does not look as expected."""


@dataclass(frozen=True, slots=True)
class CreationConfig:
    community_id: str
    invitation_options: Mapping[str, bool]
    invitation_name_max_length: int
    ip_address_restricted: bool
    key_prefixes: Mapping[str, str]  # object -> 3-character Id prefix


def load_creation_config(path: Path | None = None) -> CreationConfig:
    config_file = path or config_path(*DEFAULT_CONFIG_PARTS)
    try:
        raw = json.loads(config_file.read_text(encoding="utf-8"))
        community = raw["community_id"]
        options = raw["invitation_options"]
        max_length = raw["invitation_name_max_length"]
        restricted = raw["ip_address_restricted"]
        prefixes = raw["key_prefixes"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise RecipeError(
            f"Cannot read creation config {config_file}: {error}"
        ) from error
    _full_id(community, "community_id")
    if not isinstance(options, dict) or set(options) != set(_OPTION_FIELDS):
        raise RecipeError(f"invitation_options must define exactly {_OPTION_FIELDS}")
    if not all(isinstance(v, bool) for v in options.values()):
        raise RecipeError("invitation_options values must be true or false")
    if (
        not isinstance(max_length, int)
        or isinstance(max_length, bool)
        or max_length < 1
    ):
        raise RecipeError("invitation_name_max_length must be a positive integer")
    if not isinstance(restricted, bool):
        raise RecipeError("ip_address_restricted must be true or false")
    if (
        not isinstance(prefixes, dict)
        or set(prefixes) != {INVITATION_OBJECT, SURVEY_SET_OBJECT}
        or not all(isinstance(v, str) and len(v) == 3 for v in prefixes.values())
    ):
        raise RecipeError(
            f"key_prefixes must map {INVITATION_OBJECT} and {SURVEY_SET_OBJECT} "
            "to their 3-character Id prefix"
        )
    return CreationConfig(
        community_id=community,
        invitation_options=dict(options),
        invitation_name_max_length=max_length,
        ip_address_restricted=restricted,
        key_prefixes=dict(prefixes),
    )


def invitation_name(survey_name: str, project_name: str, max_length: int) -> str:
    if not survey_name.strip() or not project_name.strip():
        raise RecipeError("Survey and project names are required for the invitation")
    return f"{survey_name} for {project_name}"[:max_length]


def invitation_fields(
    *,
    survey_id: str,
    survey_name: str,
    project_name: str,
    config: CreationConfig,
) -> dict[str, Any]:
    return {
        "Name": invitation_name(
            survey_name, project_name, config.invitation_name_max_length
        ),
        "SurveyId": _full_id(survey_id, "survey id"),
        "CommunityId": config.community_id,
        **config.invitation_options,
    }


def survey_link(invitation_link: str, invitation_id: str, language: str) -> str:
    """The link stored on the survey set (and encoded in the QR)."""
    full_id = _full_id(invitation_id, "invitation id")
    if not language.strip():
        raise RecipeError("The survey language is required")
    if not invitation_link.startswith("https://"):
        raise RecipeError(f"Unexpected invitation link: {invitation_link!r}")
    short = f"invitationId={full_id[:15]}&"
    if invitation_link.count(short) != 1:
        raise RecipeError(
            "The invitation link does not contain the invitation id once: "
            f"{invitation_link!r}"
        )
    if "guestUserLang=" in invitation_link:
        raise RecipeError("The invitation link already has a language")
    long = f"invitationId={full_id}&"
    return invitation_link.replace(short, long) + f"&guestUserLang={language}"


def qr_code_url(link: str) -> str:
    return quote(link, safe="")


def survey_set_fields(
    *,
    project_id: str,
    survey_id: str,
    language: str,
    kind: SurveyKind,
    invitation_id: str,
    link: str,
    config: CreationConfig,
) -> dict[str, Any]:
    return {
        "Project__c": _full_id(project_id, "project id"),
        "Survey__c": _full_id(survey_id, "survey id"),
        "Survey_Language__c": language,
        "SurveyNPS__c": kind is SurveyKind.NPS,
        "IpAddress_Restricted__c": config.ip_address_restricted,
        "Survey_Invitation__c": _full_id(invitation_id, "invitation id"),
        "Survey_Invitation_Link__c": link,
        "QR_Code_URL__c": qr_code_url(link),
    }


def project_fields(invitation_id: str) -> dict[str, Any]:
    """NPS only: the project points to its NPS invitation."""
    return {"Survey_Invitation__c": _full_id(invitation_id, "invitation id")}


def _full_id(value: object, what: str) -> str:
    if not isinstance(value, str) or not _FULL_ID.fullmatch(value):
        raise RecipeError(
            f"The {what} must be an 18-character Salesforce Id: {value!r}"
        )
    try:
        SalesforceId(value)
    except DomainError as error:
        raise RecipeError(str(error)) from error
    return value
