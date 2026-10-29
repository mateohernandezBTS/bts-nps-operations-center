# Automated tests and golden master candidates

Run from the repository root using the existing local virtual environment. Inputs
are versioned synthetic emails; tests do not require prior processed reports.
Set TMP and TEMP to repository `.tmp` before starting Python:

```powershell
$env:TMP = "$PWD\.tmp"
$env:TEMP = "$PWD\.tmp"
New-Item -ItemType Directory -Force .tmp | Out-Null
python -m compileall -q app engine packaging
python -m unittest discover -s tests -p "test*.py" -v
python -m pytest -q
python -m pytest --cov=engine --cov-report=term-missing -q
```

On this Windows environment, NPS-019 requires explicit approval for each exact
outside-sandbox test command. Keep other commands inside the sandbox. Do not change
ACLs, patch tempfile/os functions, install packages or run the interactive preview
to work around test execution restrictions. Expected collection is 151 methods:
141 existing cases plus ten golden master methods. Subtests do not add methods.

## Candidate comparison

`test_pipeline_golden_master.py` executes the real controller and pipeline with fresh
stdlib temporary roots, absolute TEST lifecycle paths, retention disabled and an
injected SessionManager. It reuses the TEST constant patches required by NPS-017.
Immutable emails are copied before processing; source/error/processed bytes and
execution manifest/log consistency are checked. No production transformation is
mocked. Parser variants also run through the real pure stages.

Every scenario is executed again in an independent root and compared with the
first projection. JSON/CSV checks preserve typed JSON versus CSV string semantics,
classification partitions and column order. Weekly CSV rows are compared with
consolidated JSON and every exported workbook field/hyperlink. Mutations to a
copied business date, decision and link must fail the same comparison used for
snapshots. Runtime-only timestamp, ID and contained-path mutations must compare
equal; unknown roots, malformed timestamps and reversed lifecycles must fail.

`tests/snapshots/phase1/v1/` currently contains **PENDING proposals**. Ordinary tests
read and compare them; missing/extra files or changed semantics fail. A green test
result means the proposals match the current implementation, not that an architect
or product owner approved them. Neither tests nor helper functions approve data.
The authoritative status, counts, known-defect evidence, empty signoff fields and
provenance hash are in `snapshots/phase1/v1/APPROVAL.md`.

The 14 scenarios are:

- `complete_weekly`
- `review_and_boundaries`
- `cross_source_duplicates`
- `partial_failure`
- `missing_argentina`, `missing_brazil`, `missing_mexico`
- `duplicate_source`
- `parser_equivalence` (all eight parser variants)
- `malformed_Brazil_no_html`, `malformed_Brazil_no_table`
- `malformed_Brazil_missing_header`, `malformed_Brazil_bad_cells`
- `malformed_Brazil_orphan_group`

Blocked cases snapshot real controller preflight plus
`test_inventory_manifest.json`, created by the harness for inventory assertions.
The application does not create that manifest after blocking.
Malformed standalone reports snapshot actual failed lifecycle artifacts and
diagnostics. They do not invent Excel or Slack outputs. Full successful/partial
scenarios retain every required stage surface, complete Slack HTML/Markdown and
workbook cells, types/formulas, hyperlinks and structural metadata. Outside-window
records use their persisted CSV representation. Workbook ZIP/document metadata is
excluded; no pixel, formatting or production-data certification is claimed.

The canonicalization allowlist is in `support/snapshot_projection.py`. It validates
and replaces named runtime timestamps, source-associated execution IDs and contained
filesystem paths only. Business dates, decisions, received email dates, URLs and
array order remain. Every traceback field contains only its final exception type
and message; paths, line numbers and source lines are omitted. The separate error
field remains unchanged. Generated HTML whitespace is retained, with
a scoped Git whitespace attribute; all snapshot files have LF endings.

## Explicit candidate export and PR approval

When an authorized task requests new proposals, set
`BTS_EXPORT_GOLDEN_CANDIDATES=1` before an approved exact test command. This explicit
development mode writes only to ignored
`.codex-log/snapshot-candidates/F1-05B/` and bypasses stored-candidate comparisons
for that run. Independent catalog assertions, cross-artifact checks, repeatability
and mutation controls still run. Remove the environment variable afterward and
run both normal comparison commands before reporting validation. CI and ordinary
tests must not set it. Export does not write to `tests/snapshots/` or sign approval.

F1-05A explicitly authorizes copying and committing reviewed-for-provenance proposals
to the task branch while APPROVAL.md stays PENDING. The F1-05B architect corrections
retain that status. Provenance assertions cover config/*.json, fixture metadata
and candidate hashes only. app/, engine/ and packaging/ source hashes are recorded
in source_sha256 for information and are never asserted. Phase 1 frozen-tree Git
checks enforce the source freeze; Phase 2/3 refactors must not fail merely because
source bytes or traceback frames move. Do not bulk
accept unexpected differences or treat repeated generation as independent evidence
of correctness; the literal catalog checks and full human diff review remain required.

Snapshot approval happens on the future PR: the architect reviews the complete
candidate changes, then the product owner fills the signoff references/date in
APPROVAL.md. Until both steps are complete, nothing reaches develop. Initial
acceptance and every later snapshot update require that same review. F1-05A creates
no PR and performs no merge or snapshot approval. No approval authorizes a business
rule change. See `documentation/plans/F1_phase_1_safety_net.md` section 5.2.
