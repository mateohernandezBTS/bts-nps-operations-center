"""Minimal .xlsx writer with the standard library (no openpyxl in the skill).

Enough for logs: several sheets, a bold header row, text and number cells, column
widths and a frozen header. Text is written as inline strings, so no shared-string
table is needed. Files open in Excel, LibreOffice and Google Sheets.
"""

from __future__ import annotations

import re
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

Cell = str | int | float | bool | None
_INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_SHEET_NAME = re.compile(r"^[^\\/?*\[\]:]{1,31}$")


@dataclass(frozen=True, slots=True)
class Sheet:
    name: str
    header: Sequence[str]
    rows: Sequence[Sequence[Cell]]
    widths: Sequence[int] = ()


def write_xlsx(path: Path, sheets: Sequence[Sheet]) -> Path:
    if not sheets:
        raise ValueError("A workbook needs at least one sheet")
    names = [s.name for s in sheets]
    if len(set(names)) != len(names) or not all(_SHEET_NAME.match(n) for n in names):
        raise ValueError(f"Invalid or repeated sheet names: {names}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as book:
        book.writestr("[Content_Types].xml", _content_types(len(sheets)))
        book.writestr("_rels/.rels", _ROOT_RELS)
        book.writestr("xl/workbook.xml", _workbook(names))
        book.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheets)))
        book.writestr("xl/styles.xml", _STYLES)
        for number, sheet in enumerate(sheets, start=1):
            book.writestr(f"xl/worksheets/sheet{number}.xml", _sheet(sheet))
    return path


def column_name(index: int) -> str:
    """0 → A, 25 → Z, 26 → AA."""
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _sheet(sheet: Sheet) -> str:
    rows = [_row(1, sheet.header, header=True)]
    rows += [_row(n, row) for n, row in enumerate(sheet.rows, start=2)]
    cols = ""
    if sheet.widths:
        cols = (
            "<cols>"
            + "".join(
                f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
                for i, w in enumerate(sheet.widths, start=1)
            )
            + "</cols>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
        'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        f"{cols}<sheetData>{''.join(rows)}</sheetData></worksheet>"
    )


def _row(number: int, values: Sequence[Cell], *, header: bool = False) -> str:
    cells = "".join(
        _cell(f"{column_name(i)}{number}", value, header)
        for i, value in enumerate(values)
    )
    return f'<row r="{number}">{cells}</row>'


def _cell(ref: str, value: Cell, header: bool) -> str:
    style = ' s="1"' if header else ""
    if value is None or value == "":
        return f'<c r="{ref}"{style}/>'
    if isinstance(value, bool):
        return f'<c r="{ref}"{style} t="b"><v>{int(value)}</v></c>'
    if isinstance(value, int | float):
        return f'<c r="{ref}"{style}><v>{value}</v></c>'
    text = escape(_INVALID_XML.sub("", str(value)))
    return (
        f'<c r="{ref}"{style} t="inlineStr"><is><t xml:space="preserve">{text}</t>'
        "</is></c>"
    )


def _content_types(count: int) -> str:
    sheets = "".join(
        f'<Override PartName="/xl/worksheets/sheet{n}.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for n in range(1, count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
        'package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
        'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.'
        'openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        f"{sheets}</Types>"
    )


def _workbook(names: Sequence[str]) -> str:
    sheets = "".join(
        f'<sheet name="{escape(name, {chr(34): "&quot;"})}" sheetId="{n}" '
        f'r:id="rId{n}"/>'
        for n, name in enumerate(names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets}</sheets></workbook>"
    )


def _workbook_rels(count: int) -> str:
    rels = "".join(
        f'<Relationship Id="rId{n}" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{n}.xml"/>'
        for n in range(1, count + 1)
    )
    styles = (
        f'<Relationship Id="rId{count + 1}" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        f'relationships">{rels}{styles}</Relationships>'
    )


_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
    '2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
)

_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border>'
    "</borders>"
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
    "</cellStyleXfs>"
    '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    "</cellXfs>"
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/>'
    "</cellStyles></styleSheet>"
)
