from pathlib import Path

from bs4 import BeautifulSoup

from engine.stages.email_parser import (
    HEADER_MAPPING,
    extract_html_from_eml,
    normalize_header,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

REPORT_PATH = (
    PROJECT_ROOT
    / "input"
    / "processed"
    / "brazil_upcoming_test.eml"
)


def main() -> None:
    html_content = extract_html_from_eml(
        REPORT_PATH
    )

    soup = BeautifulSoup(
        html_content,
        "html.parser",
    )

    report_table = soup.find(
        "table",
        class_=lambda value: (
            value
            and "reportTable" in value
        ),
    )

    if report_table is None:
        raise ValueError(
            "No se encontró la tabla reportTable."
        )

    print("=" * 80)
    print("HEADER ROW DIAGNOSTIC")
    print("=" * 80)
    print(f"Report: {REPORT_PATH}")
    print()

    candidates = []

    for row_number, row in enumerate(
        report_table.find_all("tr"),
        start=1,
    ):
        cells = row.find_all(
            ["th", "td"],
            recursive=False,
        )

        if not cells:
            continue

        raw_headers = [
            cell.get_text(
                " ",
                strip=True,
            )
            for cell in cells
        ]

        normalized_headers = [
            normalize_header(header)
            for header in raw_headers
        ]

        recognized_headers = [
            header
            for header in normalized_headers
            if header in HEADER_MAPPING
        ]

        recognized_count = len(
            recognized_headers
        )

        if recognized_count > 0:
            candidates.append(
                (
                    recognized_count,
                    row_number,
                    raw_headers,
                    normalized_headers,
                    recognized_headers,
                )
            )

    candidates.sort(
        key=lambda item: (
            item[0],
            -item[1],
        ),
        reverse=True,
    )

    for (
        recognized_count,
        row_number,
        raw_headers,
        normalized_headers,
        recognized_headers,
    ) in candidates[:10]:
        print("-" * 80)
        print(f"Row: {row_number}")
        print(f"Cells: {len(raw_headers)}")
        print(
            f"Recognized: {recognized_count}"
        )

        print("\nRAW HEADERS")
        for index, header in enumerate(
            raw_headers
        ):
            print(f"{index}: {header!r}")

        print("\nNORMALIZED HEADERS")
        for index, header in enumerate(
            normalized_headers
        ):
            mapped = HEADER_MAPPING.get(
                header,
                "[NOT MAPPED]",
            )

            print(
                f"{index}: {header!r} "
                f"-> {mapped}"
            )

        print()

    if candidates:
        best = candidates[0]

        print("=" * 80)
        print("BEST CANDIDATE")
        print("=" * 80)
        print(f"Row: {best[1]}")
        print(f"Recognized: {best[0]}")
    else:
        print("No recognized header candidates.")


if __name__ == "__main__":
    main()