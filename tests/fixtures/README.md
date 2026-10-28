# Synthetic report fixtures

Every client, project and person in this catalog is invented. No operational email
or record was used. Matcher literals from checked-in business rules occur only in
clearly fictional labels; the special-email alias is an invented full name.
All email addresses and input URLs use example.invalid. Project IDs are synthetic
FXT-prefixed 15/18-character values, including an explicitly encoded URL variant.

`catalog.json` declares the 26 files, layout variants, structural properties and
scenario bundles. `rows.json` contains 95 literal synthetic rows with independently
authored normalization, classification, window and worklist outcomes. These are
fixture contracts, not approved golden master snapshots. Known behavior is retained.

The weekly reference Monday is 8/3/2026; the window is 8/4 through 8/10 inclusive.
The six directories and matching filename prefixes are weekly, parser, detection,
classification, scenarios and malformed. The full per-file inventory, data-row
counts, properties, scenario tags and SHA-256 hashes are in `fixture_manifest.json`.
Bundles reference catalog IDs and do not duplicate stored email bytes.

Generate twice from the repository root, using the local virtual environment:

```powershell
python -m tests.support.fixture_generator --destination .tmp/f102-first
python -m tests.support.fixture_generator --destination .tmp/f102-second
```

The two output roots contain byte-identical email files and manifest metadata.
MIME boundaries, Date, Message-ID, base64 UTF-8 transfer encoding, CRLF line endings,
header order and row order are fixed. The fixture-local .gitattributes preserves
email bytes and LF JSON inputs on checkout. Manifest hashes cover both JSON inputs
and each email.
No clocks, random values, file discovery or production configuration are generator
inputs. The checked-in application/configuration is read only by contract tests.

After an intentional catalog/row edit, explicitly regenerate versioned inputs:

```powershell
python -m tests.support.fixture_generator --write-versioned
```

Review input provenance, email content and manifest diffs before committing.
Ordinary tests regenerate only into disposable roots and never accept snapshots.
`fixture_path(id)` resolves a declared input; `copy_fixture(id, destination)` copies
it to a fresh file before processing. Never pass a versioned input to a lifecycle
operation that moves or mutates it. Unknown IDs, writes into the source root and
overwriting an existing operational copy fail explicitly.

The Chile email deliberately remains REVIEW with the stock detector. A later
unconfigured-source test uses the existing detection seam to supply a detected
Chile context; it must not edit the production detection configuration. Last 30 days
reports are detected but known out of scope for weekly_upcoming. Malformed emails
have detectable envelopes and deliberately invalid parser structure.

The existing six NPS-009 tests still look under ignored processed data. F1-02 does
not redirect them; F1-03 will consume this catalog. The Windows suite should report
81 cases, 75 passed and the same six missing-fixture exceptions (errors in unittest,
failures in pytest). Windows test commands require explicit approval under NPS-019;
generation and static quality checks stay inside the sandbox.
