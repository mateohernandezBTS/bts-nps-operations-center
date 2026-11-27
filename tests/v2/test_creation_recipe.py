"""V2-2 creation recipe: payloads built exactly as the Salesforce screen flow does.

Synthetic ids and hosts only; the shapes mirror the rules verified on real data
(V2-2 plan, section 3).
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote

from engine.paths import config_path
from nps_v2.creation.recipe import (
    CreationConfig,
    RecipeError,
    invitation_fields,
    invitation_name,
    load_creation_config,
    project_fields,
    qr_code_url,
    survey_link,
    survey_set_fields,
)
from nps_v2.domain import SurveyKind

INVITATION_ID = "0KiAA0000000001AAA"
SURVEY_ID = "0KdAA0000000002AAA"
PROJECT_ID = "a0gAA0000000003AAA"
GENERATED_LINK = (
    "https://example.invalid/act/survey/runtimeApp.app?invitationId=0KiAA0000000001"
    "&surveyName=survey_nps&UUID=00000000-0000-0000-0000-000000000001"
)
CONFIG = CreationConfig(
    community_id="0DBAA0000000004AAA",
    invitation_options={
        "OptionsAllowGuestUserResponse": True,
        "OptionsAllowParticipantAccessTheirResponse": False,
        "OptionsCollectAnonymousResponse": False,
    },
    invitation_name_max_length=255,
    ip_address_restricted=False,
    key_prefixes={"SurveyInvitation": "0Ki", "Survey_Set__c": "aHq"},
)


class InvitationTest(unittest.TestCase):
    def test_fields(self) -> None:
        fields = invitation_fields(
            survey_id=SURVEY_ID,
            survey_name="Survey NPS",
            project_name="Synthetic Session | Turma 2",
            config=CONFIG,
        )
        self.assertEqual(
            fields,
            {
                "Name": "Survey NPS for Synthetic Session | Turma 2",
                "SurveyId": SURVEY_ID,
                "CommunityId": "0DBAA0000000004AAA",
                "OptionsAllowGuestUserResponse": True,
                "OptionsAllowParticipantAccessTheirResponse": False,
                "OptionsCollectAnonymousResponse": False,
            },
        )
        self.assertNotIn("OwnerId", fields)  # the owner is whoever creates it

    def test_name_is_cut_to_the_field_length(self) -> None:
        name = invitation_name("Facilitators SP", "x" * 300, 255)
        self.assertEqual(len(name), 255)
        self.assertTrue(name.startswith("Facilitators SP for xxx"))

    def test_names_are_required(self) -> None:
        with self.assertRaises(RecipeError):
            invitation_name(" ", "Session", 255)

    def test_ids_must_be_full(self) -> None:
        for bad in ("0KdAA0000000002", "", "not-an-id-at-all!!", None):
            with self.subTest(bad=bad):
                with self.assertRaises(RecipeError):
                    invitation_fields(
                        survey_id=bad,  # type: ignore[arg-type]
                        survey_name="Survey NPS",
                        project_name="S",
                        config=CONFIG,
                    )


class LinkAndQrTest(unittest.TestCase):
    def test_link_uses_the_full_id_and_the_language(self) -> None:
        link = survey_link(GENERATED_LINK, INVITATION_ID, "pt-BR")
        self.assertEqual(
            link,
            "https://example.invalid/act/survey/runtimeApp.app?invitationId="
            "0KiAA0000000001AAA&surveyName=survey_nps"
            "&UUID=00000000-0000-0000-0000-000000000001&guestUserLang=pt-BR",
        )

    def test_qr_is_the_link_encoded_with_no_safe_characters(self) -> None:
        link = survey_link(GENERATED_LINK, INVITATION_ID, "es")
        qr = qr_code_url(link)
        self.assertTrue(qr.startswith("https%3A%2F%2Fexample.invalid%2Fact%2F"))
        self.assertIn("%3FinvitationId%3D0KiAA0000000001AAA%26surveyName%3D", qr)
        self.assertTrue(qr.endswith("%26guestUserLang%3Des"))
        self.assertEqual(unquote(qr), link)

    def test_unexpected_links_are_rejected(self) -> None:
        cases = {
            "other invitation": GENERATED_LINK.replace("0001&", "0009&"),
            "not https": GENERATED_LINK.replace("https://", "http://"),
            "already has a language": GENERATED_LINK + "&guestUserLang=es",
            "id twice": GENERATED_LINK + "&x=1&invitationId=0KiAA0000000001&y",
        }
        for name, link in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(RecipeError):
                    survey_link(link, INVITATION_ID, "es")
        with self.assertRaises(RecipeError):
            survey_link(GENERATED_LINK, INVITATION_ID, " ")


class SurveySetAndProjectTest(unittest.TestCase):
    def test_survey_set_fields(self) -> None:
        link = survey_link(GENERATED_LINK, INVITATION_ID, "es")
        for kind, nps in ((SurveyKind.NPS, True), (SurveyKind.FACILITATORS, False)):
            with self.subTest(kind=kind):
                fields = survey_set_fields(
                    project_id=PROJECT_ID,
                    survey_id=SURVEY_ID,
                    language="es",
                    kind=kind,
                    invitation_id=INVITATION_ID,
                    link=link,
                    config=CONFIG,
                )
                self.assertEqual(
                    fields,
                    {
                        "Project__c": PROJECT_ID,
                        "Survey__c": SURVEY_ID,
                        "Survey_Language__c": "es",
                        "SurveyNPS__c": nps,
                        "IpAddress_Restricted__c": False,
                        "Survey_Invitation__c": INVITATION_ID,
                        "Survey_Invitation_Link__c": link,
                        "QR_Code_URL__c": qr_code_url(link),
                    },
                )

    def test_project_points_to_the_nps_invitation(self) -> None:
        self.assertEqual(
            project_fields(INVITATION_ID), {"Survey_Invitation__c": INVITATION_ID}
        )


class CreationConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)

    def test_repository_config(self) -> None:
        config = load_creation_config()
        self.assertEqual(len(config.community_id), 18)
        self.assertEqual(
            dict(config.invitation_options),
            {
                "OptionsAllowGuestUserResponse": True,
                "OptionsAllowParticipantAccessTheirResponse": False,
                "OptionsCollectAnonymousResponse": False,
            },
        )
        self.assertEqual(config.invitation_name_max_length, 255)
        self.assertFalse(config.ip_address_restricted)

    def test_invalid_configs(self) -> None:
        good = json.loads(
            config_path("v2", "creation.json").read_text(encoding="utf-8")
        )
        cases = {
            "missing file": None,
            "bad community": {**good, "community_id": "short"},
            "extra option": {
                **good,
                "invitation_options": {**good["invitation_options"], "X": True},
            },
            "non-bool option": {
                **good,
                "invitation_options": {
                    **good["invitation_options"],
                    "OptionsCollectAnonymousResponse": "no",
                },
            },
            "zero length": {**good, "invitation_name_max_length": 0},
            "restricted not bool": {**good, "ip_address_restricted": "false"},
            "bad prefixes": {**good, "key_prefixes": {"SurveyInvitation": "0K"}},
        }
        for name, content in cases.items():
            path = self.directory / f"{name}.json"
            if content is not None:
                path.write_text(json.dumps(content), encoding="utf-8")
            with self.subTest(case=name):
                with self.assertRaises(RecipeError):
                    load_creation_config(path)


if __name__ == "__main__":
    unittest.main()
