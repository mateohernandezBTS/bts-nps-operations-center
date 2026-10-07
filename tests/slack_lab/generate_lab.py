from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any

from docx import Document
from docx.shared import Inches
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill


PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

LAB_DIR = PROJECT_DIR / "tests" / "slack_lab"

SOURCE_WORKLIST = (
    PROJECT_DIR
    / "tests"
    / "output"
    / "weekly_runs"
    / "NPS_WEEK_2026-08-04_2026-08-10"
    / "selam_worklist.csv"
)

OUTPUT_DIR = LAB_DIR / "generated"

TARGET_CLIENT = "Arzyz"

COLUMNS = [
    "Session",
    "Date",
    "Facilitator",
    "QR-Code",
    "Link NPS Survey",
    "Link Insights Facilitators",
    "Results",
    "Link for Results",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def load_worklist() -> list[dict[str, str]]:
    if not SOURCE_WORKLIST.exists():
        raise FileNotFoundError(
            "No se encontró la worklist de prueba:\n"
            f"{SOURCE_WORKLIST}"
        )

    with SOURCE_WORKLIST.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def choose_sample_record(
    records: list[dict[str, str]],
) -> dict[str, str]:
    for record in records:
        if clean_text(
            record.get("Client")
        ).casefold() == TARGET_CLIENT.casefold():
            return record

    if records:
        return records[0]

    raise ValueError(
        "La worklist no contiene registros."
    )


def operational_record(
    source: dict[str, str],
) -> dict[str, str]:
    return {
        column: clean_text(
            source.get(column)
        )
        for column in COLUMNS
    }


def generate_excel(
    record: dict[str, str],
) -> Path:
    output_path = OUTPUT_DIR / "01_excel_table.xlsx"

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Slack Test"

    worksheet["A1"] = (
        "PRUEBA A — Copiar las celdas A3:H4 "
        "y pegarlas directamente en Slack Canvas"
    )

    worksheet["A1"].font = Font(
        bold=True,
        size=12,
    )

    worksheet.merge_cells(
        start_row=1,
        start_column=1,
        end_row=1,
        end_column=len(COLUMNS),
    )

    for column_number, column_name in enumerate(
        COLUMNS,
        start=1,
    ):
        cell = worksheet.cell(
            row=3,
            column=column_number,
            value=column_name,
        )

        cell.font = Font(
            bold=True,
            color="FFFFFF",
        )

        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="1F4E78",
        )

        cell.alignment = Alignment(
            wrap_text=True,
            horizontal="center",
            vertical="center",
        )

    for column_number, column_name in enumerate(
        COLUMNS,
        start=1,
    ):
        cell = worksheet.cell(
            row=4,
            column=column_number,
        )

        value = record[column_name]

        if (
            column_name == "Link for Results"
            and value
        ):
            cell.value = "Home"
            cell.hyperlink = value
            cell.font = Font(
                color="0563C1",
                underline="single",
            )

        elif (
            column_name == "Link NPS Survey"
            and value
        ):
            cell.value = "NPS"
            cell.hyperlink = value
            cell.font = Font(
                color="0563C1",
                underline="single",
            )

        elif (
            column_name
            == "Link Insights Facilitators"
            and value
        ):
            cell.value = "Facilitators"
            cell.hyperlink = value
            cell.font = Font(
                color="0563C1",
                underline="single",
            )

        else:
            cell.value = value

        cell.alignment = Alignment(
            wrap_text=True,
            vertical="top",
        )

    widths = {
        "A": 45,
        "B": 14,
        "C": 30,
        "D": 16,
        "E": 20,
        "F": 28,
        "G": 12,
        "H": 18,
    }

    for column_letter, width in widths.items():
        worksheet.column_dimensions[
            column_letter
        ].width = width

    worksheet.row_dimensions[3].height = 38
    worksheet.row_dimensions[4].height = 55
    worksheet.sheet_view.showGridLines = False

    workbook.save(output_path)

    return output_path


def generate_word(
    record: dict[str, str],
) -> Path:
    output_path = OUTPUT_DIR / "02_word_table.docx"

    document = Document()

    document.add_heading(
        "PRUEBA B — Tabla Word",
        level=1,
    )

    document.add_paragraph(
        "Seleccionar la tabla completa, copiarla y pegarla "
        "directamente en Slack Canvas."
    )

    table = document.add_table(
        rows=2,
        cols=len(COLUMNS),
    )

    table.style = "Table Grid"

    for index, column_name in enumerate(COLUMNS):
        table.cell(
            0,
            index,
        ).text = column_name

        value = record[column_name]

        if (
            column_name == "Link for Results"
            and value
        ):
            display_value = f"Home\n{value}"

        elif (
            column_name == "Link NPS Survey"
            and value
        ):
            display_value = f"NPS\n{value}"

        elif (
            column_name
            == "Link Insights Facilitators"
            and value
        ):
            display_value = f"Facilitators\n{value}"

        else:
            display_value = value

        table.cell(
            1,
            index,
        ).text = display_value

    for section in document.sections:
        section.left_margin = Inches(0.35)
        section.right_margin = Inches(0.35)

    document.save(output_path)

    return output_path


def generate_html(
    record: dict[str, str],
) -> Path:
    output_path = OUTPUT_DIR / "03_html_table.html"

    header_cells = "".join(
        f"<th>{html.escape(column)}</th>"
        for column in COLUMNS
    )

    row_cells = []

    for column in COLUMNS:
        value = record[column]

        if column == "Link for Results" and value:
            cell_content = (
                f'<a href="{html.escape(value)}">Home</a>'
            )

        elif column == "Link NPS Survey" and value:
            cell_content = (
                f'<a href="{html.escape(value)}">NPS</a>'
            )

        elif (
            column == "Link Insights Facilitators"
            and value
        ):
            cell_content = (
                f'<a href="{html.escape(value)}">'
                "Facilitators"
                "</a>"
            )

        else:
            cell_content = html.escape(value)

        row_cells.append(
            f"<td>{cell_content}</td>"
        )

    html_document = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Slack HTML Table Test</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 24px;
}}
table {{
    border-collapse: collapse;
    width: 100%;
}}
th, td {{
    border: 1px solid #999;
    padding: 10px;
    text-align: left;
    vertical-align: top;
}}
th {{
    background: #1f4e78;
    color: white;
}}
.instructions {{
    margin-bottom: 20px;
    font-weight: bold;
}}
</style>
</head>
<body>
<div class="instructions">
PRUEBA C — Seleccionar únicamente la tabla,
copiarla desde Edge y pegarla en Slack Canvas.
</div>
<table>
<thead>
<tr>{header_cells}</tr>
</thead>
<tbody>
<tr>{"".join(row_cells)}</tr>
</tbody>
</table>
</body>
</html>
"""

    output_path.write_text(
        html_document,
        encoding="utf-8",
    )

    return output_path


def generate_tsv(
    record: dict[str, str],
) -> Path:
    output_path = OUTPUT_DIR / "04_tab_separated.tsv"

    header = "\t".join(COLUMNS)

    row = "\t".join(
        record[column]
        for column in COLUMNS
    )

    output_path.write_text(
        header + "\n" + row + "\n",
        encoding="utf-8",
    )

    return output_path


def escape_rtf_text(
    value: str,
) -> str:
    result = []

    for character in value:
        code = ord(character)

        if character in {"\\", "{", "}"}:
            result.append(
                "\\" + character
            )

        elif code > 127:
            signed_code = (
                code
                if code <= 32767
                else code - 65536
            )

            result.append(
                f"\\u{signed_code}?"
            )

        elif character == "\n":
            result.append(
                "\\line "
            )

        else:
            result.append(
                character
            )

    return "".join(result)


def generate_rtf(
    record: dict[str, str],
) -> Path:
    output_path = OUTPUT_DIR / "05_rich_text.rtf"

    lines = [
        r"{\rtf1\ansi\deff0",
        r"{\fonttbl{\f0 Arial;}}",
        r"\fs20",
        (
            r"\b PRUEBA D - Copiar esta tabla "
            r"desde WordPad o Word y pegarla "
            r"en Slack Canvas.\b0\line\line"
        ),
    ]

    for column in COLUMNS:
        lines.append(
            r"\b "
            + escape_rtf_text(column)
            + r"\b0\tab "
            + escape_rtf_text(record[column])
            + r"\line "
        )

    lines.append("}")

    output_path.write_text(
    "".join(lines),
    encoding="utf-8",
)

    return output_path


def generate_test_manifest(
    record: dict[str, str],
    generated_files: list[Path],
) -> Path:
    output_path = OUTPUT_DIR / "lab_manifest.json"

    manifest = {
        "target_client": TARGET_CLIENT,
        "source_worklist": str(
            SOURCE_WORKLIST
        ),
        "sample_record": record,
        "generated_files": [
            str(path)
            for path in generated_files
        ],
        "tests": [
            {
                "id": "A",
                "method": "Excel cells",
                "instructions": (
                    "Copy A3:H4 from 01_excel_table.xlsx."
                ),
            },
            {
                "id": "B",
                "method": "Word table",
                "instructions": (
                    "Copy the entire table from "
                    "02_word_table.docx."
                ),
            },
            {
                "id": "C",
                "method": "HTML table",
                "instructions": (
                    "Open 03_html_table.html in Edge "
                    "and copy only the table."
                ),
            },
            {
                "id": "D",
                "method": "TSV",
                "instructions": (
                    "Open 04_tab_separated.tsv and copy "
                    "both lines."
                ),
            },
            {
                "id": "E",
                "method": "RTF",
                "instructions": (
                    "Open 05_rich_text.rtf in Word "
                    "and copy all content."
                ),
            },
        ],
    }

    output_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return output_path


def generate_results_template() -> Path:
    output_path = LAB_DIR / "results.md"

    content = """# Slack Compatibility Lab — Results

| Test | Method | Native table | Links preserved | Visual quality | Copy speed | QR compatible | Result |
|---|---|---:|---:|---:|---:|---:|---|
| A | Excel cells |  |  |  |  |  |  |
| B | Word table |  |  |  |  |  |  |
| C | HTML table |  |  |  |  |  |  |
| D | TSV |  |  |  |  |  |  |
| E | RTF |  |  |  |  |  |  |

## Notes

### Test A — Excel

- Result:
- Observations:

### Test B — Word

- Result:
- Observations:

### Test C — HTML

- Result:
- Observations:

### Test D — TSV

- Result:
- Observations:

### Test E — RTF

- Result:
- Observations:
"""

    output_path.write_text(
        content,
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    records = load_worklist()

    source_record = choose_sample_record(
        records
    )

    sample = operational_record(
        source_record
    )

    generated_files = [
        generate_excel(sample),
        generate_word(sample),
        generate_html(sample),
        generate_tsv(sample),
        generate_rtf(sample),
    ]

    manifest_path = generate_test_manifest(
        sample,
        generated_files,
    )

    results_path = generate_results_template()

    print("=" * 80)
    print("SLACK COMPATIBILITY LAB")
    print("=" * 80)
    print(f"Client selected: {TARGET_CLIENT}")
    print(f"Source: {SOURCE_WORKLIST}")
    print()
    print("FILES GENERATED")
    print("-" * 80)

    for path in generated_files:
        print(path)

    print(manifest_path)
    print(results_path)

    print()
    print("=" * 80)
    print("LAB GENERATION COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()