"""Standard-library .xlsx writer."""

from __future__ import annotations

import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from nps_v2.outputs.xlsx import Sheet, column_name, write_xlsx

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


class XlsxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)

    def test_column_names(self) -> None:
        self.assertEqual(
            [column_name(i) for i in (0, 25, 26, 27, 701, 702)],
            ["A", "Z", "AA", "AB", "ZZ", "AAA"],
        )

    def test_workbook_structure_and_values(self) -> None:
        path = write_xlsx(
            self.directory / "log.xlsx",
            [
                Sheet(
                    "Surveys",
                    ("Name", "Count", "Flag"),
                    [("A & <B>", 3, True), ("", None, False)],
                    (20, 8, 8),
                ),
                Sheet("Run", ("Field", "Value"), [("Code", "abc123")]),
            ],
        )
        with zipfile.ZipFile(path) as book:
            names = set(book.namelist())
            self.assertTrue(
                {"[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet2.xml"}
                <= names
            )
            sheet = ElementTree.fromstring(book.read("xl/worksheets/sheet1.xml"))
            workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
        self.assertEqual(
            [s.get("name") for s in workbook.findall("m:sheets/m:sheet", NS)],
            ["Surveys", "Run"],
        )
        cells = {c.get("r"): c for c in sheet.iter(f"{{{NS['m']}}}c")}
        self.assertEqual(cells["A2"].findtext("m:is/m:t", namespaces=NS), "A & <B>")
        self.assertEqual(cells["B2"].findtext("m:v", namespaces=NS), "3")
        self.assertEqual(cells["C2"].get("t"), "b")
        self.assertEqual(cells["A1"].get("s"), "1")  # bold header

    def test_opens_with_openpyxl_when_available(self) -> None:
        try:
            import openpyxl  # type: ignore[import-untyped]
        except ImportError:
            self.skipTest("openpyxl not installed")
        path = write_xlsx(self.directory / "x.xlsx", [Sheet("S", ("a",), [("b",)])])
        book = openpyxl.load_workbook(path)
        self.assertEqual(book["S"]["A2"].value, "b")

    def test_invalid_sheets(self) -> None:
        for sheets in (
            [],
            [Sheet("A", (), []), Sheet("A", (), [])],
            [Sheet("bad/name", (), [])],
        ):
            with self.subTest(sheets=sheets):
                with self.assertRaises(ValueError):
                    write_xlsx(self.directory / "bad.xlsx", sheets)


if __name__ == "__main__":
    unittest.main()
