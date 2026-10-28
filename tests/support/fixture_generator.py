"""Render the reviewed synthetic catalog without clocks, randomness or real data."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from email.message import EmailMessage
from email.policy import SMTP
from html import escape
from pathlib import Path, PurePosixPath
from typing import Any

from engine.paths import repository_path

FAMILIES = ("weekly", "parser", "detection", "classification", "scenarios", "malformed")
SUM_FIELDS = {
    "evaluation_programme",
    "nps",
    "evaluation_avg_facilitator",
    "ignore_reporting",
}


@dataclass(frozen=True)
class FixtureInputs:
    """Explicit catalog and literal rows; no application configuration is loaded."""

    catalog: dict[str, Any]
    rows: dict[str, Any]


def fixture_root() -> Path:
    """Return the versioned synthetic input root."""
    return repository_path("tests", "fixtures")


def load_inputs(root: Path | None = None) -> FixtureInputs:
    """Read explicit inputs and reject ambiguous IDs and unsafe relative paths."""
    root = root or fixture_root()
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    rows = json.loads((root / "rows.json").read_text(encoding="utf-8"))
    ids: set[str] = set()
    paths: set[str] = set()
    for spec in catalog["fixtures"]:
        path = PurePosixPath(spec["path"])
        family = spec["family"]
        if (
            family not in FAMILIES
            or len(path.parts) != 2
            or path.parts[0] != family
            or not path.name.startswith(family + "_")
            or path.suffix != ".eml"
            or "\\" in spec["path"]
            or ":" in spec["path"]
            or spec["path"] in paths
            or spec["id"] in ids
        ):
            raise ValueError(f"Unsafe or duplicate fixture: {spec['path']}")
        ids.add(spec["id"])
        paths.add(spec["path"])
        for row_id in spec["rows"]:
            if row_id not in rows["rows"]:
                raise ValueError(f"Undefined synthetic row: {row_id}")
    for bundle in catalog["bundles"].values():
        if not set(bundle["fixtures"]) <= ids:
            raise ValueError("Bundle references an undefined fixture")
    return FixtureInputs(catalog=catalog, rows=rows)


def cell_html(field: str, row: dict[str, Any], placement: str) -> str:
    """Escape text and anchor targets; optional placement selects invitation links."""
    text = escape(row["values"][field])
    link = row["links"].get(field, "")
    if field.startswith("survey_invitation") and placement != "row":
        keep = (
            placement == "both"
            or (placement == "first" and field == "survey_invitation")
            or (placement == "last" and field == "survey_invitation_link")
        )
        if not keep:
            link = ""
    if link:
        return f'<a href="{escape(link, quote=True)}">{text}</a>'
    return text


def report_html(spec: dict[str, Any], inputs: FixtureInputs) -> str:
    """Render the declared header order, group layout and intentional malformations."""
    labels = inputs.catalog["headers"]
    fields = [key for key in spec["header_order"] if key != spec["missing_header"]]
    headers = []
    for field in fields:
        label = labels[field]
        if spec["sum_headers"] and field in SUM_FIELDS:
            label += " Sum"
        if indicator := spec.get("header_indicators", {}).get(field):
            label += " " + indicator
        headers.append(f"<th>{escape(label)}</th>")
    body = []

    def append_non_data_rows(position: int) -> None:
        for extra in spec.get("non_data_rows", []):
            if extra["after_row"] == position:
                cells = "".join(f"<td>{escape(value)}</td>" for value in extra["cells"])
                body.append(
                    f'<tr class="{escape(extra["class"], quote=True)}">{cells}</tr>'
                )

    append_non_data_rows(0)
    for index, row_id in enumerate(spec["rows"]):
        row = inputs.rows["rows"][row_id]
        cells = []
        for field in fields:
            if field == "billing_office" and index in spec["omit_office_rows"]:
                continue
            tag = "th" if field == "billing_office" and spec["grouped"] else "td"
            attrs = ' rowspan="2"' if tag == "th" else ""
            cells.append(
                f"<{tag}{attrs}>{cell_html(field, row, spec['invitation'])}</{tag}>"
            )
        if spec["cell_counts"]:
            width = spec["cell_counts"][index]
            cells = (cells + ["<td>Fixture extra cell</td>"] * width)[:width]
        body.append('<tr class="dataRow">' + "".join(cells) + "</tr>")
        append_non_data_rows(index + 1)
    table_class = "fixtureOtherTable" if spec["no_table"] else "reportTable"
    return (
        "<html><body><p>Synthetic fixture; all entities invented.</p>"
        f'<table class="{table_class}"><tr>{"".join(headers)}</tr>'
        + "".join(body)
        + "</table></body></html>"
    )


def render_fixture(spec: dict[str, Any], inputs: FixtureInputs) -> bytes:
    """Build stable UTF-8 MIME with declared transfer encoding and fixed boundary."""
    message = EmailMessage(policy=SMTP)
    message["From"] = "Fixture Sender <reports@example.invalid>"
    message["To"] = "Fixture Operator <operator@example.invalid>"
    message["Date"] = inputs.catalog["email_date"]
    message["Message-ID"] = f"<{spec['id']}@example.invalid>"
    message["Subject"] = spec["subject"]
    html = report_html(spec, inputs)
    if spec["mime"] == "plain":
        message.set_content("Synthetic plain text only.", charset="utf-8", cte="base64")
    elif spec["mime"] == "multipart":
        message.make_mixed(boundary="fixture-boundary-" + spec["id"])
        for content, subtype, attachment in (
            ("Synthetic plain text.", "plain", False),
            ("<p>Fixture small alternative</p>", "html", False),
            (html, "html", False),
            ("<p>" + "Fixture attachment " * 1000 + "</p>", "html", True),
        ):
            part = EmailMessage(policy=SMTP)
            part.set_content(content, subtype=subtype, charset="utf-8", cte="base64")
            if attachment:
                part.add_header(
                    "Content-Disposition", "attachment", filename="fixture.html"
                )
            message.attach(part)
    else:
        message.set_content(
            html, subtype="html", charset="utf-8", cte=spec.get("html_cte", "base64")
        )
    return message.as_bytes(policy=SMTP)


def json_bytes(value: object) -> bytes:
    """Serialize versioned metadata independently of platform newline settings."""
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def generate(
    destination: Path,
    *,
    inputs_root: Path | None = None,
    write_versioned: bool = False,
) -> dict[str, Any]:
    """Write only catalog-listed EML files and a hash/provenance manifest.

    Versioned input writes require an explicit flag. No existing directory is
    recursively cleaned, and an existing fixture with different bytes is refused
    unless the explicit versioned-write action was requested.
    """
    root = inputs_root or fixture_root()
    inputs = load_inputs(root)
    destination = destination.resolve()
    if destination.is_relative_to(root.resolve()) and not write_versioned:
        raise ValueError("Versioned input writes require --write-versioned")
    rendered = [
        (spec, render_fixture(spec, inputs)) for spec in inputs.catalog["fixtures"]
    ]
    entries = []
    for spec, content in rendered:
        path = destination / "eml" / spec["path"]
        if not path.resolve().is_relative_to(destination):
            raise ValueError("Fixture destination escapes the supplied root")
        if path.exists() and path.read_bytes() != content and not write_versioned:
            raise FileExistsError(f"Refusing to overwrite different bytes: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        entries.append(
            {
                "id": spec["id"],
                "path": "eml/" + spec["path"],
                "family": spec["family"],
                "data_rows": len(spec["rows"]),
                "rows": spec["rows"],
                "properties": spec["properties"],
                "scenarios": spec["scenarios"],
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    manifest = {
        "schema_version": 1,
        "provenance": (
            "Invented entities; generated only from catalog.json and rows.json."
        ),
        "inputs": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("catalog.json", "rows.json")
        },
        "fixtures": entries,
    }
    (destination / "fixture_manifest.json").write_bytes(json_bytes(manifest))
    return manifest


def main() -> None:
    """Generate into a required scratch destination or explicitly update fixtures."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--destination", type=Path)
    group.add_argument("--write-versioned", action="store_true")
    args = parser.parse_args()
    destination = fixture_root() if args.write_versioned else args.destination
    manifest = generate(destination, write_versioned=args.write_versioned)
    print(f"Generated {len(manifest['fixtures'])} synthetic fixtures in {destination}")


if __name__ == "__main__":
    main()
