# Execution Plan — F1 Phase 1 safety net

Status: APPROVED WITH AMENDMENTS — review decisions recorded; this task is plan-only.
Prepared: 2026-10-28. Base: develop at `70ad957` (merged Phase 0 tooling).
Planning branch: `test/phase-1-plan`. This task writes only this plan.

## 1. Purpose

Make the automated suite run from a clean clone using invented Salesforce-shaped
emails, and pin the current parse-to-output behavior before Phase 2 fixes or Phase 3
refactors. Add reviewed golden masters, replace operational fixture dependencies,
and turn print scripts into assertions without changing application behavior.

## 2. Context

- Governing sources: AGENTS.md; ENGINEERING_STANDARDS.md section 6;
  DEFINITION_OF_DONE.md; DEVELOPMENT_ROADMAP.md NPS-008, NPS-009, NPS-018, NPS-019;
  F0-02_phase_0_tooling.md. Paths here are relative to the repository root unless noted.
- F0-01/F0-02 Windows baseline: 69 unittest cases, 63 passed, zero failures,
  six missing-fixture errors, zero skips. Pytest runs the same 69 cases but calls
  those exceptions six failures. Linux reference: 62 passed, one separator assertion
  failure, six missing-fixture errors. These are prior observations, not F1-01 reruns.
- Recursive inventory: 29 `test_*.py` files, 11 contributing TestCase classes and
  18 contributing no cases. `tests/test_pod_rule.py:34` only sets a flag on mismatch;
  its failure branch at line 40 prints and cannot fail either runner.
- Parser: `engine/stages/email_parser.py` functions `normalize_header`,
  `find_header_row`, `build_header_positions`, `get_row_cell`, `extract_records`,
  `extract_html_from_eml`. Fourteen required logical headers yield 15 raw fields
  because Project URL is extracted separately. Header recognition needs at least
  ten recognized cells, then requires the entire required-header set.
- Normalization: `engine/stages/normalize.py` accepts M/D/YYYY and M/D/YY, maps
  statuses and boolean glyphs, and marks invalid or missing required values REVIEW.
- Application seams: `process_report_file(..., system_config_override=...)`,
  `process_weekly_run(..., execution_config=...)`, existing controller/session
  injection, and unittest.mock patches to environment/path collaborators. The full
  `execute_weekly_end_to_end` resolves module constants and loads its own TEST config;
  patch those collaborators in tests, not the pipeline stages being characterized.
- Execution IDs contain clock time and a UUID in `engine/execution_manager.py`;
  manifests and summaries contain timestamps and paths. Workbook serialization is
  not byte-stable. These require narrow test-side canonicalization.
- Retire the letter labels used for missing operational sets in F0-01. Synthetic
  fixture families use weekly/, parser/, detection/, classification/, scenarios/
  and malformed/ directories with matching filename prefixes (section 5.1).

## 3. Scope

In scope for later approved F1-02 through F1-05:

- Test-only deterministic generation, a versioned synthetic fixture catalog,
  test harnesses, assertions, snapshots and test documentation.
- Replace the six missing-fixture lookups; make the Windows path assertion portable.
- Resolve the disposition of all 18 non-executed files in section 5.3.
- Apply the approved NPS-019 execution policy: option A for Windows, supplemented
  by option B Linux evidence at F1-03 and F1-05 closure; defer option C to optional F1-06.
- Align the DoD Git rule in the first F1-02 commit (section 5.6).

Out of scope:

- **No file under app/, engine/, config/ or packaging/ changes in Phase 1.**
- No production dependencies, GUI launch, packaging/build, operational installation
  access, OneDrive access, real emails, production exports or production identities.
- No fixes to NPS-001 through NPS-007, NPS-011 through NPS-017, rule semantics,
  eligibility, window policies, exclusions, output columns or application architecture.
- No deletion of executable files except tests' own empty temporary placeholders
  under the existing AGENTS.md exception; no process termination.

This F1-01 task implements none of the proposed tests, helpers or fixtures.

## 4. Constraints

Preserve today's business behavior, including known defects. Snapshot review means
agreement about the observed baseline, not approval of that behavior as business
policy. Do not change MERCADO_LIBRE substring matching, singular POD matching,
empty Ignore Reporting handling, coaching scope or Survey Invitation decisions.

All client, project and person entities are invented. Use identifiers such as
`Fixture Client Aurora`, `Fixture Session 001`, and `Fixture Facilitator Lumen`;
use example.invalid email addresses/URLs and synthetic 15/18-character Salesforce
IDs. Required matcher literals from checked-in configuration may be embedded in
clearly fictional labels solely to exercise exclusions. They do not identify a
real customer, employee, project or operational record. Never copy data to preserve
the historical 83/38/45 or 46/83/110 counts printed by legacy scripts.

Create disposable files only below an isolated TEST root or an approved temporary
directory. Fixtures are immutable inputs: always copy before lifecycle processing.
Pass absolute test-only lifecycle paths and disable retention in the in-memory
override. Assert all resulting paths stay beneath the designated test root.
Patch path constants before use as well as setting the environment: import-time
constants are a known limitation (NPS-017). Inject an isolated SessionManager.

The product owner approved this plan with the amendments recorded here, including
the snapshot review process, directory families, the 151-case estimate and the
NPS-019 execution policy. This review task does not start implementation. Individual
Windows test escalations and acceptance of actual snapshot candidates still require
the approvals described below. No business-rule approval is requested or assumed.

## 5. Steps

### 5.1 Fixture design and catalog

Proposed generator: `tests/support/fixture_generator.py`, invoked as a module from
the repository root. Inputs: `tests/fixtures/catalog.json` plus literal synthetic
row data and variant declarations in `tests/fixtures/rows.json`. No production
emails, current dates, random UUIDs, file discovery or private data are inputs.
Use Python's standard-library email construction with an explicit MIME boundary,
fixed UTF-8 content-transfer encoding, fixed CRLF policy, fixed Date/Message-ID,
fixed row ordering and explicit per-variant IDs. Never use Python's randomized
hash to allocate identifiers. A fixed seed alone is insufficient for MIME stability.

Variant declarations identify filename, source/country/report type, header order,
Sum suffixes, office layout, inherited office groups, invitation link placement,
MIME layout, subject prefix, record IDs and intentional malformed structure. An
explicit ordered catalog expands named variants; no uncontrolled Cartesian product.
Generation to a supplied scratch destination is the default. A separate explicit
write action updates versioned fixtures; ordinary tests never regenerate expectations.
Record SHA-256 hashes and variant provenance in a versioned fixture manifest.

Reference Monday: 8/3/2026. Main window: 8/4/2026 through 8/10/2026 inclusive.
Generator timestamps are fixed independently of business dates. Boundary rows on
8/3, 8/4, 8/10 and 8/11 pin both inclusive edges and outside-window behavior.

All paths below are under `tests/fixtures/eml/`. Each family has a directory and
matching filename prefix, such as `weekly/weekly_Argentina_upcoming.eml`.
Scenario bundles reference files rather than duplicating bytes.

| Directory / family | Versioned files / declarations | Scenarios and Salesforce properties reproduced |
|---|---|---|
| weekly/ — foundational weekly inputs | `weekly/weekly_Argentina_upcoming.eml`, `weekly/weekly_Brazil_upcoming.eml`, `weekly/weekly_Mexico_upcoming.eml` | Three required source subjects; neutral Conf/✕ rows inside the window; synthetic project anchors/IDs. Brazil has an initial Billing Office th in a 14-cell row and a following 13-cell inherited-office row; Mexico has 14 plain td cells; Argentina has explicit office cells. Weekly inputs all include a valid HTML reportTable and dataRow rows. |
| parser/ — parser compatibility | `parser/parser_Brazil_plain_headers.eml`, `parser/parser_Brazil_sum_headers.eml`, `parser/parser_Mexico_14_td.eml`, `parser/parser_Argentina_invitation_first.eml`, `parser/parser_Argentina_invitation_last.eml`, `parser/parser_Argentina_invitation_both.eml`, `parser/parser_Brazil_forwarded_multipart.eml`, `parser/parser_Brazil_multiple_offices.eml` | Plain versus Sum headers for evaluation programme, NPS, evaluation average facilitator and Ignore Reporting; Project: Project Name and Client_Name punctuation/underscores; glyphs ✔/✕; identical record expectations across equivalent layouts. Link in Survey Invitation, Survey Invitation Link, or both (last-column anchor takes precedence). Fw: subject, multipart text+HTML, HTML attachment ignored, longest non-attachment HTML part selected; grouped office transitions and inherited rows. |
| detection/ — detection and scope | `detection/detection_Chile_upcoming.eml`, `detection/detection_unknown_subject.eml`, `detection/detection_Argentina_last30.eml`, `detection/detection_Brazil_last30.eml`, `detection/detection_Mexico_last30.eml` | Detected but unconfigured country (using the existing detection seam where necessary), unknown/unrecognized report, and each configured Last 30 days subject. Last Results inputs are known out of scope for weekly_upcoming, not missing required sources and not parser errors. Unknown detection expectations follow inspected current detector behavior, not an invented new status. |
| classification/ — classification and review | `classification/classification_Argentina_rules.eml`, `classification/classification_Brazil_normalization.eml`, `classification/classification_Mexico_worklist_review.eml` | Rule rows and normalization cases below; same 14-header structure with synthetic entities. Missing Project URL produces worklist REVIEW after eligibility; malformed/missing required fields or unknown boolean/status produce normalization REVIEW; invitation presence remains eligible when other current checks pass. |
| scenarios/ — scenario bundles | `scenarios/scenarios_Mexico_duplicate_source.eml`, `scenarios/scenarios_Brazil_duplicate_project.eml`; bundle membership in catalog.json | Complete weekly = weekly trio; each missing-country bundle = weekly inputs minus that country; duplicate-source bundle = weekly inputs plus a second Mexico report under another filename; cross-source duplicate = same synthetic Project ID/date/session in two otherwise valid sources. Include complete six-report bundle = weekly inputs plus three detection Last 30 days files; out-of-window, business review and worklist review bundles use classification rows. Existing-run uses the complete weekly trio with a precreated isolated run; partial processing failure combines two weekly inputs with one malformed input. |
| malformed/ — malformed / failing input | `malformed/malformed_Brazil_no_html.eml`, `malformed/malformed_Brazil_no_table.eml`, `malformed/malformed_Brazil_missing_header.eml`, `malformed/malformed_Brazil_bad_cells.eml`, `malformed/malformed_Brazil_orphan_group.eml` | Valid detectable Upcoming envelope but no HTML; HTML without reportTable; recognizable header row missing a required column; wrong data-row width (12/15); 13-cell row before an office exists. Assert current parser exceptions and failed-file lifecycle. A second failure mode injects a controlled parser exception after a valid weekly report enters processing. |

The catalog lists each concrete row and expected stage outcome. It must include:

- All four requested statuses: Conf eligible subject to other rules; Prelim, Tent
  and Cancelled excluded with STATUS_NOT_ELIGIBLE. Include Confirmed/Tentative and
  case variants to pin existing normalization, plus one unknown and one empty status.
- Ignore Reporting: ✔ and ✕; every current TRUE_VALUES/FALSE_VALUES spelling in
  subtests; empty and x retain NPS-006 behavior; unknown token goes to REVIEW.
- Every checked-in exclusion pattern in every configured field, with neutral
  values in other fields to isolate it: MERCADO_LIBRE's two contains patterns;
  POD regex in project_name/project_sub_type; six COACHING phrases; three BTS_CLIENT
  prefixes. Add negative controls and case/accent normalization controls.
- Every REVENUE_ADMIN pattern in each configured field, yielding REVIEW; cases
  combining exclusion and review verify EXCLUDED precedence and ordered reason lists.
- NPS-004/005/015 controls: fictional words containing meli, singular POD versus
  PODs and embedded nonwords, generic coaching sessions and 1:1 meetings. Assert
  current behavior even where the register proposes a future business decision.
- Date formats, whitespace/entities, invented accented names, missing start/client/
  project/status, invalid date and invalid boolean; per-row validation issue lists.
- Duplicate facilitator spellings and empty placeholders; valid 15- and 18-character
  project IDs, encoded project URLs and unextractable IDs; ready/review separation.
- Invitation anchor/text retained in raw/normalized/classified records but absent
  from the current worklist/Excel/HTML (NPS-002/016); no duplicate prevention invented.
- In-window and outside-window business review rows; cross-source ready and manual
  review duplicates; deterministic ordering, counts and duplicate issue details.
- Slack grouping, escaping and separate-email warning path: use an invented full
  facilitator alias containing a matcher token already present in the renderer,
  never a real full name. Confirm the warning remains inside the copied table
  (NPS-003); preserve copy markup, ordering and links.

Versioned .eml tracking: F1-02 may add six narrow `.gitignore` allow rules, one for
`tests/fixtures/eml/<family>/*.eml` in each approved directory, including any required
parent unignore. No global removal of the .eml prohibition and no force-adding
unknown emails. Review every
fixture's catalog provenance before staging explicit paths. Actual generated run
artifacts remain ignored; only synthetic source fixtures/snapshots are versioned.

### 5.2 Golden master contract

Location: `tests/snapshots/phase1/v1/<scenario>/`. Proposed test-side helpers:
`tests/support/pipeline_harness.py`, `snapshot_projection.py` and
`snapshot_candidates.py`. No new dependency. JSON is UTF-8, sorted object keys,
stable indentation and final newline; preserve list order unless the product
explicitly declares that list unordered. Missing keys and nulls stay distinct.

| Snapshot | Exact semantic surface |
|---|---|
| `raw.json` | Every parsed field in source row order, including project and invitation links |
| `normalized.json`, `validation_issues.json` | Typed booleans/statuses/dates plus every validation status/reason and row number |
| `classified.json`, `classification_partitions.json` | Decisions, primary/all reason codes, matched rules/fields/patterns; eligible/excluded/review partitions |
| `worklist.json`, `worklist_review.json`, `outside_window.json` | Every output column/value, readiness issues and rejected dates/window reasons |
| `selam_consolidated.json`, `selam_manual_review.json`, `consolidation_issues.json` | Ordered records, source/country attribution and cross-source duplicate details |
| `summary.json`, `weekly_manifest.json`, `execution_summary.json` | Counts, windows, source statuses, filenames, lifecycle stages, review/duplicate issues and output relationships |
| `excel_cells.json` | Sheet order/names: Home, Worklist, Revision Manual, Manifest, Issues; nonempty cell coordinates, values/types/formulas and hyperlink targets; header order, dimensions, merged ranges and freeze panes. Load with data_only=False; no ZIP bytes or document creation metadata |
| `slack.html`, `slack_ready.md` | Full generated Slack HTML and retained Markdown, including scripts, warning/copy-table markup, groups, ordering, text, escaping and links; normalize only declared runtime tokens and line endings |

Also compare CSV headers and parsed ordered rows to JSON/workbook projections.
Do not remove Excel formatting assumptions by pretending cells alone prove visual
equivalence; no pixel/layout certification is claimed. No binary workbook snapshot.

Canonicalization is a test-only explicit allowlist, shared across projections:

1. Map each generated execution ID to a stable source/ordinal token, consistently
   across manifests, filenames, links and workbook cells. Validate source association
   before replacement; never collapse two IDs into one.
2. Replace only declared runtime timestamp fields (started_at, finished_at,
   created_at, updated_at, generated_at, processing timestamps and failure timestamps
   actually found during implementation) with a fixed sentinel. Assert each value's
   format and lifecycle ordering first. Preserve business/session/window dates.
3. Relativize paths beneath the known temporary root to `<TEST_ROOT>/...`, normalize
   separators only for path-valued fields, and replace the known checkout root in
   diagnostic paths. Assert containment first. Unknown absolute roots fail review.
   Never rewrite Salesforce/result URLs, arbitrary backslashes in text or client IDs.
4. Project workbook cells through that same allowlist; omit ZIP order, file mtimes
   and workbook document metadata. Retain formula strings and hyperlinks.
5. Keep row counts, filenames, statuses, decisions, reason strings, output columns,
   weekly IDs and date windows intact. Do not mask differences using broad regexes,
   remove all dates, sort all rows or drop warning rows.

Establish complete, review, boundary/duplicate and partial-failure scenarios. A
partial source failure deliberately records today's COMPLETED_WITH_REVIEW/success
behavior (NPS-001), not the desired Phase 2 fix. Missing/duplicate-source runs and
malformed standalone reports snapshot blocked/failed manifests and issues rather
than demanding nonexistent Excel/HTML outputs.

Approval workflow for both initial creation and updates:

1. Run current frozen application code with the reviewed synthetic catalog. Write
   candidate projections beneath ignored `.codex-log/snapshot-candidates/`; absent
   snapshots fail tests. CI/ordinary tests never create or accept baselines.
2. Compare candidates with catalog facts and independent semantic assertions;
   expected records are not obtained solely by re-running the same production helper.
   Review complete diffs, not only hashes or counts. Record runtime and config hashes.
3. The architect reviews the full candidate diffs, parser fidelity and projections.
   Prepare `tests/snapshots/phase1/v1/APPROVAL.md` with per-scenario input/output
   counts and a list of preserved known defects: NPS-xxx ID, observed behavior and
   the scenario/snapshot path where each appears. Record candidate/config hashes,
   architect review reference, product-owner approval reference and date. The product
   owner approves this document for the initial baseline and each later update.
   No snapshot approval can authorize a business-rule change.
4. Only after approval copy named candidates to tests/snapshots and commit them in a
   separate `test: approve phase 1 golden master snapshots` commit together with the
   approved APPROVAL.md, with approval reference and reason in the commit/PR
   description. Never bulk-accept unexpected diffs.
5. A second run in a different TEST root must match. Targeted mutation controls change
   a business date, decision and link in a copied projection and must fail comparison;
   runtime-only token changes must compare equal. Restore only scratch copies.

### 5.3 Disposition of all 18 non-executed test files

All automated conversions use unittest.TestCase methods so both runners collect
the same cases. Table counts are proposed new test methods, not assertions or
subtests; existing 69 cases remain. Merges remove the superseded script only after
equivalent assertions exist at the named destination. No bulk tests/scripts deletion.

| Existing file | One decision | Destination / reason | New cases in F1-04 |
|---|---|---|---:|
| tests/scripts/test_engine_email_parser.py | Merge | tests/test_email_parser.py; six format/link/MIME/failure methods replace the real-email print preview | 6 |
| tests/scripts/test_engine_normalize.py | Merge | tests/test_normalize.py; four date/boolean/status/required-field methods with explicit variant subtests | 4 |
| tests/scripts/test_engine_business_rules.py | Merge | tests/test_business_rules.py; five methods cover complete exclusion, eligibility, review, precedence and negative-control matrices | 5 |
| tests/scripts/test_engine_worklist.py | Merge | tests/test_worklist.py; four methods pin boundaries, project-ID extraction, facilitator normalization and REVIEW partition | 4 |
| tests/scripts/test_engine_slack_output.py | Merge | tests/test_slack_output.py; two methods assert per-source Markdown content and summary grouping | 2 |
| tests/scripts/test_execution_lifecycle.py | Convert | tests/test_execution_lifecycle.py; two methods assert temporary-file lifecycle and persisted manifest/log, with no root input/pending access | 2 |
| tests/test_application_controller.py | Merge | tests/test_controller_session_integration.py; two synthetic ready/blocked preflight methods supplement existing mocked session tests | 2 |
| tests/test_application_controller_weekly.py | Merge | tests/test_controller_session_integration.py; two real synthetic full-pipeline/partial-failure controller methods, isolated sessions | 2 |
| tests/test_frontend_controlled_failure.py | Move to tests/manual/ | tests/manual/frontend_controlled_failure.py; interactive show/exec preview is not a discoverable test; no automated GUI launch | 0 |
| tests/test_inventory_manifest_integration.py | Convert | Same path; three TestCase methods for ready, blocked and persisted manifest round-trip | 3 |
| tests/test_pod_rule.py | Convert | Same path; seven assertive TestCase methods replace seven import-time print comparisons; singular/plural characterization also in rule matrix | 7 |
| tests/test_selam_aggregator.py | Convert | Same path; four methods for attribution/order, duplicate ready records, review aggregation and persistence | 4 |
| tests/test_selam_output.py | Convert | Same path; three methods for CSV/schema, summary/manual-review window and retained Markdown | 3 |
| tests/test_six_reports_manifest.py | Merge | tests/test_inventory_manifest_integration.py; one additional six-report method asserts three matched and three known-out-of-scope | 1 |
| tests/test_source_config.py | Convert | Same path; three methods for enabled sources, required sources and historical optional group | 3 |
| tests/test_source_inventory.py | Convert | Same path; four methods for complete/missing/duplicate/unknown-or-out-of-scope inventories, using scenario subtests | 4 |
| tests/test_weekly_orchestrator.py | Convert | Same path; four methods for success, continue-after-failure, stop-on-error and preserved lifecycle/source results | 4 |
| tests/test_weekly_run.py | Convert | Same path; four methods for default window, manifest persistence, existing-run rejection and invalid weekday | 4 |
| **Total** | **17 automated dispositions; one manual move** | **18 files accounted for** | **60** |

No unconditional deletion is proposed. Deletions following a merge are limited to
the listed superseded test scripts. Other tests/scripts utilities and preview files
are outside this task's 18-file inventory; do not sweep them into cleanup.

### 5.4 Repair NPS-009 and NPS-018 without application edits

F1-03 replaces country-name globbing of ignored processed emails with explicit
catalog IDs in tests/support/fixture_paths.py. Pass those immutable paths to the
existing copy helper or copy into fresh temp pending directories. Keep each original
test method and its assertions; remove dependency on prior runs or execution order.

| Existing broken test | Synthetic inputs / setup |
|---|---|
| test_duplicate_source_is_blocked | weekly trio plus a second copy of weekly Mexico under a distinct filename; expect source duplicate blocking, not cross-project deduplication |
| test_existing_weekly_run_is_blocked | weekly trio plus the expected weekly output directory under a fresh TEST root |
| test_missing_argentina_is_blocked | weekly Brazil and weekly Mexico only |
| test_missing_brazil_is_blocked | weekly Argentina and weekly Mexico only |
| test_missing_mexico_is_blocked | weekly Argentina and weekly Brazil only |
| test_failed_report_is_moved_to_error | weekly Brazil, with the existing controlled parser exception injected after the lifecycle enters processing; assert error move/details/manifest/log and propagated exception |

These six tests must become passing assertions, never skipped, xfailed or converted
to expected failures. Retain a separate actual malformed-input parser test later so
controlled injection does not stand in for malformed-input coverage.

At tests/test_controller_session_integration.py:246 replace the literal Windows
separator expectation with `str(Path('output') / 'report.xlsx')` (or an equivalent
Path comparison). Keep the exact relative location assertion; do not assert only
the filename. Run the same 69 original test IDs on Windows and Linux. NPS-018 is
closed only after both operating systems have evidence, not merely a local edit.

### 5.5 NPS-019 decision and deferred option

The F0-02 diagnosis established that mkdtemp's 0o700 ACL is unusable by the Windows
restricted token; setting TMP/TEMP inside the repository did not fix it. Do not
change ACLs or monkeypatch global tempfile/os functions to get a green run.

| Option | Pros | Cons / limits |
|---|---|---|
| A. Retain the current explicit-approval exception for exact Windows unittest/pytest commands | Exercises the actual Windows environment without altering tests or production code; supported by F0-02 baseline | Every elevated run requires explicit approval and runs outside token confinement; does not repair the sandbox. Exact-command limitation complicates alternate tooling/coverage commands |
| B. Human-launched Linux cloud evidence at F1-03 and F1-05 closures | Linux isolation avoids the observed Windows ACL incompatibility and tests NPS-018 portability | Linux alone cannot certify Windows. Cloud dependencies/wrapper must already be available; no automatic installs or packaging. Requires a separately recorded Windows run |
| C. Introduce a portable test-only temporary-root helper using ordinary inherited-permission directories | Can keep test-created roots inside the sandbox without weakening production code or the stdlib; explicit containment/cleanup contracts | Touches many existing test setups, needs careful unique allocation and cleanup validation, and may not control Qt/third-party tempfile usage. Could mask isolation mistakes; must preserve temporary .exe cleanup constraints |

Approved decision: option A applies to all Windows runs, limited to the exact test
commands with explicit approval. Windows local is primary for every package.
Option B supplies required Linux evidence only at F1-03 and F1-05 closure; the human
launches a Codex cloud task for each closure. No Linux run is required for F1-02 or
F1-04. Option C is deferred to optional F1-06 after F1-05, not selected for current
implementation. The 151-case estimate excludes F1-06. NPS-019 remains PLANNED because
the approved operating accommodation does not repair the underlying incompatibility.

### 5.6 Sequenced execution work packages

Each branch starts from updated develop after the previous package is reviewed and
merged. No implementation starts from an unapproved plan or unapproved snapshot.
Publish task branches only; PRs target develop. Record actual counts and explain any
variance before changing the budget; never remove useful tests to meet a number.

The first F1-02 commit changes only documentation/DEFINITION_OF_DONE.md: replace
"Work is on the correct branch; the agent ran no Git write operations." with
"Work is on the correct branch; no direct commits on `main` or `develop`."
Commit exactly `docs(dod): align git rule with AGENTS.md`, before fixture commits.
This correction is planned here; the DoD file is unchanged by the review task.

| # | Task / branch | Files | Planned commits, in order | Validation / expected counts |
|---|---|---|---|---|
| F1-02 | Synthetic inputs; test/phase-1-fixtures | documentation/DEFINITION_OF_DONE.md first; then tests/support generator/path helpers, tests/fixtures catalog/rows/eml/manifest, tests/test_fixture_catalog.py, narrow .gitignore exception | FIRST `docs(dod): align git rule with AGENTS.md`; then `test: add deterministic synthetic report fixtures`; `test: validate synthetic fixture catalog contracts` | Windows local primary; no Linux evidence required. Two scratch generations have identical bytes/hashes; check catalog provenance, six directory families, structural signatures and absence of operational data. Estimate 12 new TestCase methods: six family contracts plus determinism, byte/MIME stability, invented entities, safe links/IDs, catalog/hash completeness and immutable copies. Estimate 81 total: 75 pass + 6 known errors (pytest labels these failures) |
| F1-03 | Restore clean-clone baseline; test/phase-1-baseline | tests/test_backend_blocking_scenarios.py, tests/test_processing_error_lifecycle.py, tests/test_controller_session_integration.py, tests/support/fixture_paths.py | `test: replace missing operational fixture dependencies`; `test: make controller output path assertion portable` | Windows local primary; human launches the Linux cloud task at closure. Original six tests pass with weekly inputs, original 69 IDs retained; no new methods. Estimate 81/81 pass on both runners and both OSes, zero failures/errors/skips; no prior-run dependency. Record engine/ pytest-cov line coverage from Linux closure as a baseline, not a gate |
| F1-04 | Convert inventory; test/phase-1-test-conversion | The 18-file disposition map and its named destinations; tests/manual frontend preview; test-only harness support | `test: convert stage and rule print scripts to assertions`; `test: convert weekly integration scripts to isolated cases`; `test: move interactive failure preview out of discovery` | Windows local primary; no Linux evidence required. Estimate 60 new methods from section 5.3 and 141/141 pass on both runners. All retained test_*.py files contribute cases; imports do not execute scenarios or print verdicts. Confirm a deliberately wrong POD expectation fails, then restore the scratch expectation before committing |
| F1-05 | Golden master and closure evidence; test/phase-1-golden-master | tests/support projections/candidate helper, tests/test_pipeline_golden_master.py, tests/snapshots/phase1/v1 including APPROVAL.md, tests/README.md; Phase 1 documentation evidence only | `test: add semantic pipeline golden master comparisons`; after architect full-diff review and product-owner approval of APPROVAL.md, `test: approve phase 1 golden master snapshots`; `docs: record phase 1 safety net validation` | Windows local primary; human launches the Linux cloud task at closure. Estimate 10 new methods: complete pipeline, parser equivalence, rule/review matrix, window edges, source blocking, cross-source duplicates, partial failure, canonicalization repeatability, mutation detection and provenance. Estimate 151/151 pass on both runners/OSes, zero failures/errors/skips. Record engine/ pytest-cov line coverage as a baseline, not a gate; compare Excel/Slack projections, verify APPROVAL.md counts/defect locations and frozen production tree |

Count budget: 69 original + 12 fixture contracts + 60 converted cases + 10 golden
master methods = 151. Matrix rows use subtests and do not multiply collected cases.
The product owner approved 151 as an estimate, not a gate or a result claimed by
F1-01. Any extra needed test must be justified and the expected counts revised
openly. Phase 1's success is
meaningful asserted coverage and clean-clone parity, not the exact number 151.

### 5.7 Optional F1-06 stub — deferred temporary-root helper

After F1-05, a separately authorized `test/phase-1-temp-helper` package may explore
option C. Scope: test-only portable temporary-root allocation and contained cleanup,
plus conversion of explicitly inventoried test setups; no app/, engine/, config/
or packaging/ changes. Do not change ACLs or patch global tempfile/os functions.

Risks: shared-directory collisions, leaked files, unsafe cleanup, and third-party/Qt
tempfile calls that bypass the helper. Validation must exercise containment,
uniqueness and cleanup, including only tests' own empty .exe placeholders, then run
the full suite against the already approved F1-05 golden master with no snapshot
updates. Compare Windows sandbox behavior with the approved Windows baseline and
record any residual permission failures. Keep option A until replacement is proven.
Additional helper tests and their count are defined in the future package; they are
outside the approved 151-case estimate. This stub authorizes no F1-06 implementation.

## 6. Validation strategy

For each approved implementation package:

- Run compileall for app/engine/packaging and new test/support modules.
- Run unittest discovery and `python -m pytest -q` from the root using the local
  virtual environment; record run/passed/failures/errors/skips and collected IDs.
  Windows local is primary for every package. Set TMP/TEMP to repository .tmp before
  Python starts. Under approved option A request
  approval for the exact test commands only; no compound elevated scripts.
- At F1-03 and F1-05 closure only, the human launches a Codex cloud task for Linux
  evidence. Use `/workspace/.setup/bts/headless.sh` for Python and Qt headless settings.
  Do not launch the interactive manual preview on either platform.
- At those two closures, record pytest-cov line coverage for engine/ as a baseline,
  not a gate: covered/total statements, missed lines, percentage, platform and tool
  versions. Collect it in the human-launched Linux task with
  `/workspace/.setup/bts/headless.sh -m pytest -q --cov=engine --cov-report=term-missing --cov-report=json:.codex-log/engine-coverage.json`.
  Keep the machine report ignored and record its summary in the closure evidence.
  This does not broaden the exact-command Windows escalation exception. Required
  cloud tooling must be provisioned by the environment; stop and report if absent.
- Inspect unittest and pytest collection inventories without executing legacy mains;
  no silent skips, expected-failure labels or reliance on import-time print checks.
- Run Ruff check/format-check on new or converted Python test modules; baseline
  production debt (152 Ruff violations, 32 mypy errors in 11 files from F0-02) is
  not permission to reformat/fix frozen directories. Run mypy on new test helpers
  where feasible and record scope. No new tools or runtime dependencies.
- Run both orders (or equivalent targeted reversed-order invocation), twice in
  independent roots, and compare snapshots. Never require tests/runtime to be
  populated before a clean-clone run. No network or real-data dependency.
- Human review: synthetic fidelity, rule/row coverage matrix, known-defect labels,
  canonicalization allowlist, full candidate diffs and product-owner approval of
  APPROVAL.md. NPS-019 operating policy and execution ownership are already approved.

### Frozen-tree verification

Before every implementation commit and at Phase 1 closure, run read-only Git checks
against the package's base and against the Phase 0 anchor `70ad957`:

```text
git diff --exit-code 70ad957 -- app/ engine/ config/ packaging/
git diff --cached --exit-code -- app/ engine/ config/ packaging/
git status --short --untracked-files=all -- app/ engine/ config/ packaging/
git diff --check
```

The first two must exit 0 and the status query must print nothing; inspect ignored
or generated artifacts separately without staging them. At review, compare directory
tree object IDs to the anchor as an additional tracked-content check. Any production
tree difference blocks the package; report it rather than expanding Phase 1 scope.
Check fixture/snapshot diffs for real data before staging explicit paths, never git add .

For this PLAN ONLY task, validate document completeness, all 18 inventory rows,
case-count arithmetic, Markdown structure, the sole changed path and Git diff
whitespace. Do not execute the runtime test suite or create fixtures merely to
validate a prose plan; compileall/full-suite implementation gates remain for F1-02+.

## 7. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Synthetic HTML misses grouping/header quirks | Medium | False confidence in parser coverage | Explicit structural signatures, paired equivalent variants and reviewer signoff; never claim production-data certification |
| Golden master blesses known bugs or hides business changes | High | Regression net protects the wrong assumption | Label NPS-001..007 behavior, independent semantic assertions, explicit approval and no automatic snapshot acceptance |
| Canonicalization hides meaningful differences | Medium | False-green snapshots | Narrow field allowlist, containment checks and mutation/repeatability tests |
| Tests mutate inputs or shared sessions | Medium | Order dependence and data loss | Copy immutable inputs; TEST-only overrides; isolated sessions; containment assertions and independent roots |
| tempfile ACL incompatibility persists | Confirmed | Windows sandbox cannot complete suite | Approved option A for exact Windows tests; option B at two closures; no implicit sandbox workaround |
| Fixture files remain ignored or expose real data | Medium | Clean clone fails or data leaks | Narrow ignore exception, explicit catalog/manifest tracking and invented-entity review |
| Open approvals delay F1-05 | Medium | Snapshots cannot be committed | Prepare reviewable candidates; stop before acceptance and report human action |
| Actual test design needs more than the budget | Medium | Misleading collection target | Retain useful tests, update arithmetic with reasons and obtain review; never trade coverage for a number |

## 8. Rollback

Each package is isolated on its own branch and committed in coherent steps. If
rollback is requested after merge, create revert commits through the normal review
workflow. Never reset published history, force-push, delete branches/tags, touch
operational installations or remove executable files. The production tree is
unchanged throughout, so no application deployment or operational-data migration
is part of Phase 1. Preserve approved prior snapshots as Git history.

## 9. Progress

- [x] F1-01: inspect Phase 0 documents, parser/normalizer and all 18 file dispositions.
- [x] F1-01: prepare this plan for review; no implementation performed.
- [x] Human approves plan with directory families and the 151-case estimate.
- [x] NPS-019: option A on Windows; option B Linux evidence at F1-03/F1-05 closures;
  option C deferred to optional F1-06. Windows local owns every package's primary run.
- [x] F1-02: DoD correction (280fecf), synthetic catalog/generator (18e985a), and
  12 contract methods completed on Windows. The catalog has 26 emails and 95
  invented literal rows. Two scratch generations and the versioned inputs matched
  byte-for-byte, including the manifest and all SHA-256 hashes. Unittest: 81 run,
  75 passed, 0 failures, 6 known errors, 0 skipped; pytest: 75 passed and the same
  6 missing-fixture exceptions classified as failures (340 subtests passed).
  Compileall and scoped Ruff check/format-check passed; scoped mypy checked four
  new modules with no issues, using --follow-imports=skip for untouched imports.
  Frozen-tree checks passed; no Linux evidence is required for this package.
- [x] F1-03 Windows implementation: multipart weekly fidelity fix, six repaired tests,
  portable path assertion and Windows engine/ coverage baseline recorded below.
- [ ] F1-03 closure: human-launched Linux evidence for NPS-018 and Linux coverage
  baseline remain pending; NPS-018 is not yet closed.
- [ ] F1-04: all 18 file dispositions completed.
- [ ] Architect reviews full candidate diffs; product owner approves APPROVAL.md with
  per-scenario counts and preserved known-defect locations.
- [ ] F1-05: approved snapshots/APPROVAL.md, human-launched Linux closure evidence
  and engine/ line-coverage baseline recorded.
- [ ] Optional F1-06: separately authorize and scope the deferred temporary-root helper.

### F1-03 Windows evidence ? 2026-10-28

Branch: `test/phase-1-baseline`, based on updated develop `d0570d2`.
Implementation commits: `f80f67c` (weekly MIME), `d3aa688` (NPS-009),
`1355e6d` (portable path assertion). Application behavior is unchanged.

The three weekly emails now use multipart/alternative with UTF-8 text/plain and
base64 text/html parts, fixed boundaries and the existing fixed envelope metadata.
Decoded HTML bytes are identical to the pre-change inputs. Two independently
supplied scratch roots (`.tmp/f103-first`, `.tmp/f103-second`) and the versioned
root matched byte-for-byte for all 26 emails and the manifest (27 files per root).
The existing weekly-family contract checks MIME type, boundary, ordered parts,
UTF-8 charset, base64 encoding and absence of attachments; no new methods added.

The five blocking scenarios use explicit weekly catalog IDs through tests/support,
including two separate copies of weekly Mexico for duplicate-source blocking.
Their SessionManager is isolated under a fresh temporary root. The lifecycle test
copies weekly Brazil, proves the file entered processing before raising the
controlled parser exception, and retains the original error/manifest/log assertions.
It additionally checks persisted path containment and unchanged source/error bytes.
The controller assertion retains the full relative output/report.xlsx location
using native Path construction.

Validation used the local Windows virtual environment (Python 3.14.6), with TMP
and TEMP set to repository `.tmp` before Python started. Runtime commands ran outside
the sandbox with explicit approval under NPS-019 option A:

| Command | Final result |
|---|---|
| `python -m unittest discover -s tests -p "test*.py" -v` | 81 run, 81 passed, 0 failures, 0 errors, 0 skipped; final run 9.411s |
| `python -m pytest -q` | 81 passed, 340 subtests passed, 0 failures/errors/skips; 13.90s |
| `python -m pytest --cov=engine --cov-report=term-missing -q` | 81 passed, 340 subtests passed, 0 failures/errors/skips; 16.01s |
| `python -m pytest --collect-only -q` (sandbox) | 81 collected; all 69 original IDs retained |
| `python -m compileall -q app engine packaging` plus changed tests/support | Passed |
| `python -m ruff check` and `python -m ruff format --check` on five changed Python modules | Passed |
| `python -m mypy --follow-imports=skip` on the same five modules | No issues in 5 source files |

The five static-check targets were tests/support/fixture_generator.py,
tests/test_fixture_catalog.py, tests/test_backend_blocking_scenarios.py,
tests/test_processing_error_lifecycle.py and tests/test_controller_session_integration.py.
Untouched application typing/lint debt was not included. Original method IDs were
compared against the base using AST inventories, and pytest collection and verbose
unittest execution confirmed collection. No skips or expected failures were added.
Fresh temporary roots are created by each lifecycle/inventory invocation; no ignored
processed-email lookup remains in the six repaired cases. No separate fresh-clone
checkout or reversed-order runtime invocation was performed in this Windows task;
exact-command escalation limits remain in force.

Frozen-tree diff checks against `d0570d2` and `70ad957`, cached checks, untracked
status checks and whitespace checks passed before each implementation commit.
Tree object IDs for app/, engine/, config/ and packaging/ also match both anchors.
No dependencies, business rules, snapshots or operational files changed.

Coverage baseline (line coverage, not a gate): Windows win32, pytest 9.2.0,
pytest-cov 7.1.0, coverage 7.17.0. Engine total: **1,446 covered / 2,858 statements**,
**1,412 missed**, **50.5948%** (terminal rounded to **51%**). No excluded lines.
The ignored machine report is `.codex-log/f103/engine-coverage.json`, exported from
the same coverage data inside the sandbox. Five least-covered modules, ranked by
unrounded percentage:

| Module | Covered / statements | Missed | Coverage |
|---|---:|---:|---:|
| engine/selam_aggregator.py | 22 / 189 | 167 | 11.64% |
| engine/weekly_manifest.py | 11 / 81 | 70 | 13.58% |
| engine/weekly_orchestrator.py | 14 / 103 | 89 | 13.59% |
| engine/weekly_excel.py | 45 / 323 | 278 | 13.93% |
| engine/selam_output.py | 25 / 162 | 137 | 15.43% |

The product owner explicitly approved the exact Windows coverage command in this
session, amending section 6 only for this run. Linux NPS-018 evidence and the Linux
coverage baseline still require a human-launched Codex cloud task using the wrapper
and command in section 6. Architect review and product-owner review are pending.

## 10. Decision log

| Date | Decision / open item | Reason | Owner |
|---|---|---|---|
| 2026-10-28 | Phase 1 plan approved with amendments; this review changes only the plan | Explicit plan review; no implementation requested in this task | User |
| 2026-10-28 | Freeze app/, engine/, config/, packaging/ for all Phase 1 work | Safety net must precede behavior fixes/refactors | User |
| 2026-10-28 | Use weekly/, parser/, detection/, classification/, scenarios/, malformed/ directories and matching filename prefixes | Retired letters named missing operational sets in F0-01 | Product owner |
| 2026-10-28 | Approve 151 cases as an estimate; explain useful changes rather than enforcing the count | Coverage quality takes precedence over an exact total | Product owner |
| 2026-10-28 | Select option A for every Windows run and option B at F1-03/F1-05 closures; defer option C to optional F1-06 | Approved NPS-019 execution policy | Product owner |
| 2026-10-28 | Architect reviews full candidate diffs; product owner approves APPROVAL.md with per-scenario counts and preserved known-defect IDs/locations | Make snapshot acceptance explicit and reviewable | Product owner / architect |
| 2026-10-28 | Windows local is primary for all packages; human launches Linux cloud tasks only at F1-03/F1-05 closures | Required cross-platform closure evidence | Product owner |
| 2026-10-28 | Record engine/ pytest-cov line coverage at both closures as a baseline, not a gate | Quantify the safety net without a coverage threshold | Product owner |
| 2026-10-28 | F1-02 starts with docs(dod): align git rule with AGENTS.md | Correct contradictory DoD wording before fixture work | Product owner |

| 2026-10-28 | F1-03 includes weekly multipart fidelity before the six repairs, followed by portable assertion and results commits | Explicit task amendment; preserve decoded HTML and original 81 methods | Product owner |
| 2026-10-28 | Approve exact Windows pytest coverage command outside sandbox for F1-03 | Explicit session approval; Linux evidence remains separately pending | Product owner |
