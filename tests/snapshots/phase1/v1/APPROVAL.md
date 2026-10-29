# Phase 1 golden master candidates

Status: APPROVED

Prepared: 2026-10-29. Package: F1-05A, corrected by F1-05B architect review.
Branch: `test/phase-1-golden-master`. Base: `develop` at `e2a49bd`.

Architect reviewer: Claude (Anthropic), architect/reviewer role

Architect review reference: F1-05A and F1-05B review bundles; approved 2026-10-29

Product-owner approver: Mateo Hernández

Product-owner approval reference: PR #8 comment

Approval date: 2026-10-29

These are proposed observations of the frozen application, including known defects.
Passing candidate comparisons does not approve the baseline or its business behavior.
The F1-05A task explicitly permits committing PENDING candidates on this branch.
Nothing reaches develop until the architect reviews the complete candidate diffs
and the product owner signs this document on the PR. This task creates no PR and
provides no approval. Any later candidate change requires the same review and signoff.

## Inputs and counts

All inputs are copied from the versioned synthetic catalog. No operational data was
used. Reference Monday: 8/3/2026; inclusive window: 8/4/2026 through 8/10/2026.

READY and REVIEW are final exported weekly counts, after deduplication and manual
review window filtering. EXCLUDED is the pre-consolidation classification count.
Outside is the count of eligible rows rejected by the weekly window. Parsed counts
only successful parsing; a malformed source contributes zero parsed rows. Sources
blocked means all three configured sources were prevented from processing by the
weekly preflight gate, including otherwise received sources. Parser equivalence
uses eight parser variants through pure stages, so no source lifecycle is counted.

| Scenario | Input emails | Parsed | READY | EXCLUDED | REVIEW | Outside | Sources processed | Failed | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| complete_weekly | 3 | 6 | 6 | 0 | 0 | 0 | 3 | 0 | 0 |
| review_and_boundaries | 3 | 85 | 26 | 37 | 17 | 2 | 3 | 0 | 0 |
| cross_source_duplicates | 3 | 47 | 10 | 25 | 9 | 0 | 3 | 0 | 0 |
| partial_failure | 3 | 4 | 4 | 0 | 0 | 0 | 2 | 1 | 0 |
| missing_argentina | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| missing_brazil | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| missing_mexico | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| duplicate_source | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| parser_equivalence | 8 | 15 | 15 | 0 | 0 | 0 | 0 | 0 | 0 |
| malformed_Brazil_no_html | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| malformed_Brazil_no_table | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| malformed_Brazil_missing_header | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| malformed_Brazil_bad_cells | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| malformed_Brazil_orphan_group | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

The review/boundary scenario has 18 classified business REVIEW rows before window
filtering: 15 are exported, plus two worklist REVIEW rows, giving 17 final reviews.
The duplicate scenario has 11 classified business REVIEW rows; one cross-source
duplicate is removed and one out-of-window review is omitted, giving nine exports.
Its 11 ready rows become ten after deduplication. Thus these columns are deliberately
different stages and are not intended to sum to Parsed. Missing-date/invalid-date
business review rows remain visible in classified and manual-review aggregates.
Blocked cases contain preflight results and test_inventory_manifest.json, an
independently inventoried persisted manifest created by the test harness.
The application does not create it after blocking; its test_ prefix distinguishes
it from application-produced weekly_manifest.json in completed weekly scenarios.
Standalone malformed cases contain failed execution manifests, detection and error
details; no nonexistent workbook or Slack output is asserted.

## Preserved known defects

Paths below are relative to this directory. Row identifiers refer to
`tests/fixtures/rows.json`; the corresponding invented project name is retained in
the snapshots so the architect can check every claim directly.

| ID | Scenario and snapshot file | Observed behavior preserved |
|---|---|---|
| NPS-001 | partial_failure/operation.json; weekly_manifest.json; summary.json | Brazil fails, Argentina and Mexico process, but the controller reports success with COMPLETED_WITH_REVIEW and empty top-level issues. Final outputs contain four rows and omit Brazil. |
| NPS-002 | parser_equivalence/raw.json and normalized.json; review_and_boundaries/worklist.json, excel_cells.json and slack.html | Invitation text/links are parsed and normalized, but invitation columns are absent from the worklist, workbook and rendered HTML. The invitation row remains present without those fields. |
| NPS-003 | review_and_boundaries/slack.html | The invented special-email facilitator triggers tr.separate-email-warning inside the client table copied by Copy for Slack. Complete copy JavaScript and table markup are retained. The renderer's existing warning text is preserved verbatim. |
| NPS-004 | review_and_boundaries/raw.json and classified.json | control_substring uses the fictional client Fixture Client Ameliara (Fixture Session 039): the meli substring produces MERCADO_LIBRE exclusion. |
| NPS-005 | review_and_boundaries/raw.json and classified.json | control_plural contains PODs and remains ELIGIBLE; configured singular POD examples are excluded. No plural rule is added. |
| NPS-006 | review_and_boundaries/raw.json, normalized.json and classified.json | Empty Ignore Reporting normalizes to False and remains eligible subject to other rules; x becomes True and is excluded, while the cross glyph becomes False. |
| NPS-015 | review_and_boundaries/raw.json and classified.json | control_generic_coaching and control_generic_meeting remain ELIGIBLE under the finite configured coaching patterns. No broader coaching policy is inferred. |
| NPS-016 | parser_equivalence/classified.json; review_and_boundaries/classified.json and worklist.json | Existing Survey Invitation values/links do not create an exclusion. The invented invitation row remains eligible and ready when other checks pass. |
| NPS-013 | complete_weekly/weekly_manifest.json and slack.html | The current three configured sources and fixed country presentation are retained. This is evidence of the present three-country baseline, not a test of adding a fourth source. |

NPS-007 remains unfixed: complete_weekly/preflight.json, weekly_manifest.json and
worklist.json record the currently aligned windows. These candidates do not change
schedule configuration to demonstrate the known disagreement between implementations.
NPS-017 is accommodated by the TEST constant patches in
tests/support/weekly_cases.py; contained paths in every manifest demonstrate isolation,
not a repair of import-time resolution. NPS-019 remains the Windows tempfile sandbox
limitation; runtime tests use approved elevated commands, and no snapshot demonstrates
or fixes its ACL behavior. NPS-011, NPS-012 and NPS-014 remain outside this package:
dead code, broader documentation drift and production retention are not characterized
by these candidate scenarios. No roadmap defect is closed by proposing this baseline.

## Projection and provenance

There are 141 semantic files across 14 scenarios. JSON preserves null/missing keys,
types and list order, uses sorted object keys, UTF-8, two-space indentation and a
final newline. Each source keeps every parsed field and row, with catalog assertions
for normalization/classification, typed JSON versus CSV serialization checks, and
classification partition checks. Outside-window data follows the persisted CSV
representation; it is not coerced back into invented typed values.

Runtime timestamp fields are exactly: started_at, finished_at, created_at, updated_at,
generated_at, processing_started_at, processing_finished_at, failed_at, aggregated_at
and inventoried_at. Nonempty values must be valid ISO timestamps; start/finish and
create/update pairs must be ordered before replacement with <RUNTIME_TIMESTAMP>.
received_at and every business/session/window date remain unchanged.

Each generated execution ID is checked against its source filename, manifest and
durable log, then mapped to a unique source/ordinal token. Only registered ID fields,
contained filesystem path fields, Manifest workbook values and parsed Issues workbook
JSON use that mapping. Unknown operational roots fail. Every traceback field is
projected to its final exception type and message only. File paths, line numbers,
stack frames and source lines are not retained. The separate error field is unchanged.
Salesforce/result URLs and arbitrary business text are not rewritten.

Workbook projections use data_only=False and preserve sheet order, dimensions,
nonempty cell coordinates, types, formulas, hyperlink targets, merged ranges and
freeze panes. Every exported worklist/manual-review field is compared with its CSV
counterpart. ZIP ordering and workbook creation metadata are omitted. No visual
formatting/layout certification or binary workbook equivalence is claimed. Full
Slack HTML, scripts and Markdown are retained; only line endings are normalized.
The generated HTML includes whitespace-only lines. Its scoped Git whitespace
attribute permits those original bytes; no trailing whitespace is stripped from
the captured renderer output.

provenance.json schema 2 asserts only behavior inputs: config/*.json and fixture
metadata in input_sha256, plus candidate_sha256. app/, engine/ and packaging/
hashes are retained separately in source_sha256 for information and are never
asserted. The Phase 1 source freeze is enforced by Git checks. Provenance also
records Python 3.14.6, Windows and dependency versions for information.
Its own SHA-256 is:

`02706db8951759aabe2da011f1811881cea2929d2449c89dcc1474413181553d`

| Configuration | SHA-256 |
|---|---|
| business_rules.json | 1baa27750aa9c43934c3bd08db2812cd7db5154f7e1fa9e59b875fb0f8a9a0a5 |
| operational_output.json | 9a60611533367e8363f674cada3b968ac9608f9b5fc0e607596285baa51e5d35 |
| report_detection.json | dc3599da15f75b681da6e48682b0c7711d8cc7d6ef479c5f92cc027975c2e4ea |
| report_sources.json | 298b39cad27eecaa29abc854c38583fe6c5e8f65cd8f83e861e25d3798b7a098 |
| system_config.json | 2c9231cc3ef8968189e90efd8e3d12533e83ba86022f3b5b0114a1ea51af90d4 |
| system_config_test.json | 287895bb823cb344e9fdbcca98f9dd6e86a0d2626540ddf74dda74de2627e7e1 |
| weekly_schedule.json | e27ea2990d0d9370b37810609049ed7837705aac9fda42c773011a2b34b86d9d |

The second execution of every scenario in a fresh independent temporary root must
match the first projection. Copied business date, decision and link mutations must
fail the actual comparison routine; changed runtime IDs, paths and timestamps must
compare equal. Ordinary tests never regenerate or accept snapshots, and missing
or extra candidate files fail comparisons. The explicit candidate-export mode
writes only to ignored .codex-log/snapshot-candidates/F1-05B and bypasses candidate
comparison for that development run; final validation runs without that opt-in.

F1-05B adds a refactor-independence control: a scratch working copy receives one
blank line at the top of engine/stages/email_parser.py. Snapshot comparisons and
test_provenance must still pass without candidate export. The scratch file is then
restored byte-for-byte, and the real checkout's frozen-tree Git check must pass.
Counts and business behavior above are unchanged. Approval remains PENDING.


## F2-02 / NPS-001 pending addendum — 2026-10-29

Status: PENDING

Decision: D1=A, approved by Mateo Hernández on 2026-10-29 in release plan
section 5.1 and explicitly authorized by task F2-02. This proposal does not
constitute baseline acceptance; historical Phase 1 approval above is preserved.

Only partial_failure changes: operation.json becomes FAILED / success=false with
actionable source/country/file/error and processed/failed counts;
weekly_manifest.json changes final status to FAILED and omits the regional
aggregation/manual-review/output metadata because those stages no longer run.
All other manifest content is identical. The nine regional output
projections listed below are deleted because publication is withheld.
Candidate count: 141 -> 132. Regional projection count for this case: 9 -> 0.
Source emails: 3 -> 3; processed: 2 -> 2; failed Brazil: 1 -> 1; parsed: 4 -> 4.
Regional READY: 4 -> withheld (no regional list); REVIEW: 0 -> withheld;
per-source READY remains 4. All per-source artifacts remain byte-identical,
including error_details, execution_manifest, execution_summary, csv and slack_ready.
All other scenarios and all ten behavior-input hashes are unchanged. Historical
source_sha256 is retained unchanged, not refreshed to conceal implementation changes.

The following table is the exact changed/deleted semantic file list. Paths are
relative to this directory. A missing new hash means deletion.

| File | Old SHA-256 | Proposed SHA-256 |
|---|---|---|
| partial_failure/operation.json | `33219b984722e9315b8dc414c5c91305dfeac551a893dd4bc516ac7b317f0f31` | `a5a7a94bb043f18f407f6d6bc149ff7b30ddf3ebca8394c75e42467ad0adb702` |
| partial_failure/weekly_manifest.json | `e6033be4db5bc690a4a4b28363eed71a41e797868bc5afef3391b41c7ea4cd78` | `2c3cf384514532618a9de81d176df3b8ac54d2410ed7f282ff544a43221bb38a` |
| partial_failure/consolidation_issues.json | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | DELETED |
| partial_failure/excel_cells.json | `2683f0305fa9061bb84854168d555b81c0c512a4d34c39dbbdaeb5dfd48a5f4b` | DELETED |
| partial_failure/manual_review_issues.json | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | DELETED |
| partial_failure/selam_consolidated.json | `60effdde458223a4595fb38cd0ffba321a786aa7795eb6a3e0463052e15ab0c1` | DELETED |
| partial_failure/selam_manual_review.json | `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570` | DELETED |
| partial_failure/slack.html | `6aa35478b8a7aa7452839f1e171900afc896b0cf0594bb52f2acb6a0a7e37076` | DELETED |
| partial_failure/slack_ready.md | `1489aa077c26597811a8d4d10d03d1f4b337fbd8d3505f0fc04da272ebb29c9e` | DELETED |
| partial_failure/summary.json | `d78d8c2411a491bfd65d98e5651e0774f402213aee023d3ea0e7be9ec6ccb201` | DELETED |
| partial_failure/weekly_csv.json | `b162348711e3c886d27e74bf66773abbca6b04f189f05a7419071ec4bc2bff3b` | DELETED |

All 130 other projections are byte-identical. Accompanying metadata changes are
only affected candidate hashes in provenance.json and this pending addendum.
The historical preserved-NPS-001 entry above describes the old baseline and is
superseded only by this proposal after human acceptance. NPS-002, NPS-003,
NPS-004, NPS-005, NPS-006, NPS-007, NPS-011 through NPS-017, NPS-019 and NPS-020
remain outside this repair; their historical observations/limitations still apply.

Architect review reference: PENDING

Product-owner PR comment/reference: PENDING (no PR requested in F2-02)

Product-owner signature: PENDING

Approval date: PENDING
