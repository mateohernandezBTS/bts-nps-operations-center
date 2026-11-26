"""Anti-corruption layer: Salesforce snapshots → certified engine dialect.

The certified stages (``engine/stages``) were written for rows parsed from Salesforce
report e-mails. This module is the only place that knows that dialect, so the stages
and their golden master stay untouched:

* dates as ``M/D/YYYY``;
* booleans as ``✔`` / ``✕``;
* a project URL from which ``extract_salesforce_id`` reads the Id;
* ``billing_office`` = ``Billing_Country__c``.
"""

from __future__ import annotations

from datetime import date

from nps_v2.domain import ProjectSnapshot

# Same keys, same order as engine.stages.email_parser.OUTPUT_COLUMNS (pinned by a test;
# not imported because the parser depends on bs4, which the skill does not ship).
LEGACY_FIELDS: tuple[str, ...] = (
    "billing_office",
    "start_date",
    "client_name",
    "project_name",
    "project_url",
    "project_sub_type",
    "status",
    "end_date",
    "all_staffings",
    "evaluation_programme",
    "nps",
    "evaluation_avg_facilitator",
    "ignore_reporting",
    "survey_invitation",
    "survey_invitation_link",
)

# Extra key carried through the stages to join results back to the snapshot.
PROJECT_ID_KEY = "v2_project_id"

PROJECT_URL_TEMPLATE = (
    "https://mybts.lightning.force.com/lightning/r/rosscrooke__Project__c/{id}/view"
)
TRUE_SYMBOL = "✔"
FALSE_SYMBOL = "✕"


def legacy_date(value: date | None) -> str:
    return "" if value is None else f"{value.month}/{value.day}/{value.year}"


def project_url(project: ProjectSnapshot) -> str:
    return PROJECT_URL_TEMPLATE.format(id=project.project_id)


def to_legacy_record(project: ProjectSnapshot) -> dict[str, str]:
    """One raw record exactly as the e-mail parser would have produced it."""
    record = {
        "billing_office": project.billing_country,
        "start_date": legacy_date(project.start_date),
        "client_name": project.client_name,
        "project_name": project.name,
        "project_url": project_url(project),
        "project_sub_type": project.sub_type,
        "status": project.status,
        "end_date": legacy_date(project.end_date),
        "all_staffings": project.all_staffings,
        # Report-only measures; not read from Salesforce and unused by the rules.
        "evaluation_programme": "",
        "nps": "",
        "evaluation_avg_facilitator": "",
        "ignore_reporting": TRUE_SYMBOL if project.ignore_reporting else FALSE_SYMBOL,
        "survey_invitation": (
            ""
            if project.survey_invitation_id is None
            else str(project.survey_invitation_id)
        ),
        "survey_invitation_link": "",
    }
    record[PROJECT_ID_KEY] = str(project.project_id)
    return record
