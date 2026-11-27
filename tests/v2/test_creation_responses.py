"""Strict reading of connector results for the creation steps."""

from __future__ import annotations

import json
import unittest

from nps_v2.creation.responses import (
    ResponseError,
    created_id,
    describe_problems,
    query_records,
    update_ok,
)

NEW_ID = "0KiAA0000000001AAA"


class CreatedIdTest(unittest.TestCase):
    def test_json_answers(self) -> None:
        for answer in (
            {"id": NEW_ID, "success": True, "errors": []},
            {"Id": NEW_ID},
        ):
            with self.subTest(answer=answer):
                self.assertEqual(created_id(json.dumps(answer), "0Ki"), NEW_ID)

    def test_plain_text_with_exactly_one_id(self) -> None:
        self.assertEqual(created_id(f"Record created: {NEW_ID}", "0Ki"), NEW_ID)

    def test_rejections(self) -> None:
        cases = {
            "rejected": json.dumps({"success": False, "errors": ["X"]}),
            "errors listed": json.dumps({"id": NEW_ID, "errors": ["X"]}),
            "no id": json.dumps({"success": True}),
            "wrong object": json.dumps({"id": "aHqAA0000000001AAA"}),
            "short id": json.dumps({"id": NEW_ID[:15]}),
            "two ids in text": f"{NEW_ID} and 0KiAA0000000002AAA",
            "nothing": "done",
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ResponseError):
                    created_id(text, "0Ki")
        with self.assertRaises(ResponseError):
            created_id(None, "0Ki")


class UpdateAndQueryTest(unittest.TestCase):
    def test_update(self) -> None:
        update_ok(json.dumps({"success": True}))
        update_ok("Record updated successfully")
        for bad in (json.dumps({"success": False}), "Error: invalid field", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ResponseError):
                    update_ok(bad)

    def test_query(self) -> None:
        self.assertEqual(
            query_records(json.dumps({"done": True, "records": [{"Id": "x"}]})),
            [{"Id": "x"}],
        )
        for bad in (
            json.dumps({"done": False, "records": []}),
            json.dumps({"done": True}),
            json.dumps([1]),
            "not json",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ResponseError):
                    query_records(bad)


class DescribeTest(unittest.TestCase):
    def test_permissions(self) -> None:
        ok = {
            "name": "Survey_Set__c",
            "createable": True,
            "fields": [{"name": "Project__c", "createable": True}],
        }
        self.assertEqual(
            describe_problems(json.dumps(ok), needs="create", fields=["Project__c"]),
            [],
        )
        bad = {
            "name": "Survey_Set__c",
            "createable": False,
            "fields": [{"name": "Project__c", "createable": False}],
        }
        problems = describe_problems(
            json.dumps(bad), needs="create", fields=["Project__c", "Other__c"]
        )
        self.assertEqual(len(problems), 2)  # unknown fields are not guessed


if __name__ == "__main__":
    unittest.main()
