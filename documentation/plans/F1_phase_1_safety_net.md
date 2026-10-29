# Execution Plan — F1 Phase 1 safety net

Status: APPROVED WITH AMENDMENTS — F1-05A candidates implemented; PR-gated approval remains pending.
Prepared: 2026-10-28. Base: develop at `70ad957` (merged Phase 0 tooling).
Planning branch: `test/phase-1-plan`. F1-04 branch: `test/phase-1-test-conversion`.

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
- Apply NPS-019 Option A only: explicitly approved Windows test commands, including
  coverage. Linux portability is an accepted risk; no cloud evidence is required.
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
4. F1-05A amendment (2026-10-29): the product owner explicitly requests committing
   candidate snapshots under tests/snapshots on test/phase-1-golden-master while
   APPROVAL.md remains PENDING, with empty approver fields. Use the proposal commit
   `test: propose phase 1 golden master snapshots`; this is not acceptance. Approval
   happens on the future PR: the architect reviews all candidate diffs, then the
   product owner signs APPROVAL.md with references/date. Nothing reaches develop
   before both steps. This task pushes the branch but creates no PR. Initial
   acceptance and every later update require that same review and signoff.
   Never bulk-accept unexpected diffs or interpret passing comparisons as approval.
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
the filename. NPS-018 is closed on F1-03 Windows evidence (81/81) and code review of the
Path-based full relative-location assertion. Linux portability remains an accepted,
documented risk; no Linux execution is required.

### 5.5 NPS-019 Windows execution policy

Only Option A remains: retain the explicit-approval exception for exact Windows
unittest/pytest commands using the local virtual environment, with TMP/TEMP set to
repository .tmp before Python starts. Coverage uses the same exception and exact
F1-03 command: `python -m pytest --cov=engine --cov-report=term-missing -q`.
Each elevated command requires approval. Do not change ACLs or monkeypatch global
tempfile/os functions. The accommodation does not repair NPS-019, which remains
PLANNED. Windows is the sole execution platform for Phase 1. Linux portability is
an accepted risk, supported only by code review of platform-neutral assertions.
The optional F1-06 helper remains separately deferred, not a selected policy.

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
| F1-03 | Restore clean-clone baseline; test/phase-1-baseline | tests/test_backend_blocking_scenarios.py, tests/test_processing_error_lifecycle.py, tests/test_controller_session_integration.py, tests/support/fixture_paths.py | `test: replace missing operational fixture dependencies`; `test: make controller output path assertion portable` | Windows-only execution; Linux portability accepted as a risk. Original six tests pass with weekly inputs, original 69 IDs retained; no new methods. Estimate 81/81 pass on both runners on Windows, zero failures/errors/skips; no prior-run dependency. Record Windows engine/ pytest-cov line coverage as a baseline, not a gate |
| F1-04 | Convert inventory; test/phase-1-test-conversion | Plan amendment and roadmap NPS-018 status first; then the 18-file disposition map and its named destinations; tests/manual frontend preview; test-only harness support | FIRST `docs(plan): drop Linux cloud evidence; Windows-only execution`; then `test: convert stage and rule print scripts to assertions`; `test: convert weekly integration scripts to isolated cases`; `test: move interactive failure preview out of discovery`; `docs(plan): record F1-04 results` | Windows local primary; no Linux evidence required. Estimate 60 new methods from section 5.3 and 141/141 pass on both runners. All retained test_*.py files contribute cases; imports do not execute scenarios or print verdicts. Confirm a deliberately wrong POD expectation fails, then restore the scratch expectation before committing |
| F1-05A / F1-05B | Propose candidates, then obtain PR-gated approval; test/phase-1-golden-master | .codex/config.toml move, POD test/config labels, three golden master helpers, tests/test_pipeline_golden_master.py, PENDING tests/snapshots/phase1/v1/APPROVAL.md and candidates, tests/README.md, plan evidence | F1-05A: `chore(codex): move project config to .codex/config.toml`; `test: read POD pattern from configuration and correct NPS labels`; `test: add semantic pipeline golden master comparisons`; `test: propose phase 1 golden master snapshots`; `docs(plan): record F1-05A results and PR-gated snapshot approval`. F1-05B: architect full-diff review and product-owner signoff on the future PR before any merge to develop | Ten new methods; 151/151 on both Windows runners. Independent-root repeatability and business/runtime mutation controls. Same engine coverage command as F1-04; list uncovered preflight paths if below 75%, without adding tests. Push branch only; no PR or approval in F1-05A |

Count budget: 69 original + 12 fixture contracts + 60 converted cases + 10 golden
master methods = 151. Matrix rows use subtests and do not multiply collected cases.
The product owner approved 151 as an estimate, not a gate or a result claimed by
F1-01. Any extra needed test must be justified and the expected counts revised
openly. Phase 1's success is
meaningful asserted coverage and clean-clone parity, not the exact number 151.

### 5.7 Optional F1-06 stub — deferred temporary-root helper

After F1-05, a separately authorized `test/phase-1-temp-helper` package may explore
a temporary-root helper. Scope: test-only portable temporary-root allocation and contained cleanup,
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
- Windows is the sole execution platform; do not launch the interactive manual preview.
- Record engine/ line coverage at F1-03, F1-04 and F1-05 using the same approved
  NPS-019 exception: `python -m pytest --cov=engine --cov-report=term-missing -q`.
  Record covered/total statements, missed lines, percentage, platform and tool
  versions. Export ignored JSON from the resulting coverage data inside the sandbox.
  Coverage is a baseline, not a gate. No Linux closure run is required.
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
| tempfile ACL incompatibility persists | Confirmed | Windows sandbox cannot complete suite | Option A for exact Windows tests and coverage; no implicit sandbox workaround |
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
- [x] NPS-019: Option A only on Windows, including coverage; helper deferred to F1-06.
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
- [x] F1-03 closure: NPS-018 DONE on 81/81 Windows evidence and Path assertion review;
  Linux portability accepted as an unverified risk.
- [x] F1-04: all 18 file dispositions completed; 60 new cases, 141/141 passing
  on both Windows runners; coverage 84.53%. Evidence and conversion table below.
- [x] F1-05A: ten golden master methods and 141 candidate files across 14 scenarios;
  151/151 both Windows runners; PENDING approval and PR gate documented below.
- [ ] Architect reviews full candidate diffs; product owner approves APPROVAL.md with
  per-scenario counts and preserved known-defect locations.
- [ ] F1-05: approved snapshots/APPROVAL.md, Windows closure evidence
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
session. The F1-04 amendment extends that exact-command policy to Windows
coverage runs and closes NPS-018 on Windows evidence plus code review. Linux
portability is an accepted unverified risk. Architect and product-owner review remain pending.

### F1-04 Windows evidence - 2026-10-29

Branch: `test/phase-1-test-conversion`, created from updated develop `6f42131`.
Commits, in required order: `30e82be` (plan amendment and NPS-018 DONE),
`c6a108d` (28 stage/rule cases), `02b99e6` (32 integration cases),
`9889fed` (manual preview move), followed by `docs(plan): record F1-04 results`.
Application behavior and all fixture bytes are unchanged. Nothing was built or
launched interactively. Publishing is limited to this branch; no PR is requested.

#### Conversion table

Counts below are collected TestCase methods, not assertion or subtest counts.
The planned 60 cases were implemented without dropping any of the original 81.

| Original file | Decision | Destination | New cases |
|---|---|---|---:|
| tests/scripts/test_engine_email_parser.py | Merge; remove superseded script | tests/test_email_parser.py | 6 |
| tests/scripts/test_engine_normalize.py | Merge; remove superseded script | tests/test_normalize.py | 4 |
| tests/scripts/test_engine_business_rules.py | Merge; remove superseded script | tests/test_business_rules.py | 5 |
| tests/scripts/test_engine_worklist.py | Merge; remove superseded script | tests/test_worklist.py | 4 |
| tests/scripts/test_engine_slack_output.py | Merge; remove superseded script | tests/test_slack_output.py | 2 |
| tests/scripts/test_execution_lifecycle.py | Convert; remove superseded script | tests/test_execution_lifecycle.py | 2 |
| tests/test_application_controller.py | Merge; remove superseded script | tests/test_controller_session_integration.py | 2 |
| tests/test_application_controller_weekly.py | Merge; remove superseded script | tests/test_controller_session_integration.py | 2 |
| tests/test_frontend_controlled_failure.py | Move; retain interactive main guard | tests/manual/frontend_controlled_failure.py | 0 |
| tests/test_inventory_manifest_integration.py | Convert | Same path | 3 |
| tests/test_pod_rule.py | Convert import-time verdicts to assertions | Same path | 7 |
| tests/test_selam_aggregator.py | Convert | Same path | 4 |
| tests/test_selam_output.py | Convert | Same path | 3 |
| tests/test_six_reports_manifest.py | Merge; remove superseded script | tests/test_inventory_manifest_integration.py | 1 |
| tests/test_source_config.py | Convert | Same path | 3 |
| tests/test_source_inventory.py | Convert | Same path | 4 |
| tests/test_weekly_orchestrator.py | Convert | Same path | 4 |
| tests/test_weekly_run.py | Convert | Same path | 4 |
| **Total** | **17 automated dispositions and one manual move** | **18 originals accounted for** | **60** |

New support modules: `tests/support/stage_cases.py` reads explicit fixture/catalog
row IDs and runs the real stages; `tests/support/weekly_cases.py` supplies fresh
stdlib temporary roots, absolute TEST lifecycle overrides with retention disabled,
copy-before-processing inputs, environment/path patches and containment assertions.
Every integration method creates its own root. Inputs are read only from the
versioned synthetic fixture catalog. Copied bundle bytes are checked against their
immutable sources after each case. Only the named superseded scripts were removed;
other tests/scripts utilities were left alone.

Parser cases cover plain/Sum equivalence, grouped offices, Mexico td rows, all
invitation placements, forwarded multipart selection and five malformed inputs
(including the second bad-cell width). Normalization checks dates/whitespace,
boolean/status matrices, required fields, issue lists and row numbers. Rule cases
cover every configured exclusion field/pattern, review, precedence, eligibility
and negative/case/accent controls. Worklist and per-source Markdown cases pin both
window edges, ID extraction, facilitator normalization, readiness, columns, links,
client grouping and filtering.

Integration cases exercise real inventory/readiness, six-report scope, weekly
creation, persistence, duplicate/existing-run protection, real lifecycle moves,
continue/stop-on-error behavior, aggregation attribution/order and ready/review
deduplication, CSV projection, manual-review window filtering, retained Markdown,
and real controller preflight/full/partial processing with injected sessions.
Chile's stock detector outcome remains REVIEW; only the existing detector seam is
patched to exercise the separate unconfigured-source inventory branch.

Known-defect assertions are labeled in code: NPS-001 partial failure still reports
COMPLETED_WITH_REVIEW/success with empty top-level issues and omits Brazil;
NPS-002 invitation columns are still absent from worklist/CSV; NPS-004 substring
matching, NPS-005 singular POD matching, NPS-006 empty/x boolean handling,
NPS-015 coaching scope and NPS-016 invitation eligibility are preserved.
NPS-017 is accommodated by patching import-time TEST constants before execution.
No business decision or production fix is implemented.

#### Validation

All runtime suite commands used Windows 11 / win32, local virtual environment,
Python 3.14.6, and repository `.tmp` for TMP/TEMP before Python started. Each
outside-sandbox command received approval under the amended NPS-019 Option A.

| Command/check | Final result |
|---|---|
| `python -m unittest discover -s tests -p "test*.py" -v` | 141 run, 141 passed, 0 failures/errors/skips; 15.590s |
| `python -m pytest -q` | 141 passed, 559 subtests passed, 0 failures/errors/skips; 18.41s |
| `python -m pytest --cov=engine --cov-report=term-missing -q` | 141 passed, 559 subtests passed, 0 failures/errors/skips; 24.99s |
| `python -m pytest --collect-only -q` (sandbox, after manual move) | 141 collected; 1.02s |
| `python -m compileall -q app engine packaging` and changed test/support/manual paths | Passed |
| `python -m ruff check` and `python -m ruff format --check` on all 18 changed Python files | Passed; 18 formatted files |
| `python -m mypy --follow-imports=skip` on the same 18 changed Python files | No issues in 18 source files; untouched imports excluded |
| AST inventory against `6f42131` | All 81 original class/method IDs retained |
| Import all recursive tests/test_*.py modules, capturing stdout/stderr | 26 modules, all silent and all contributing cases; 141 cases total |
| Import moved manual preview, capturing stdout/stderr | Silent; no GUI construction/show/exec |
| Reversed module and method order for 28 pure-stage/rule methods (sandbox) | Two runs, 28/28 passed each; 2.416s and 3.425s |
| Frozen-tree checks against `6f42131` and `70ad957`, cached diff, status and whitespace | Passed before each commit; matching directory tree object IDs |

POD mutation proof: a scratch copy at `.tmp/f104_pod_mutation.py` changed only
`test_singular` from True to False. Its seven-case run produced exactly one failure
(`AssertionError: True is not False`) and zero errors. The scratch file was restored
byte-for-byte to the unmutated source before the stage/rule commit; the tracked
module was never mutated. Its seven real assertions pass in both full runners.

Early development runs identified three incorrect new expectations (country wording
and the additional partial-run blocker; CSV field projection; an em dash damaged by
shell encoding). Those expectations were corrected against the current implementation.
The final runs above are green. No unrelated test failure, skip or expected failure
was accepted. Case-count variance: none (81 + 60 = 141).

The complete suite ran repeatedly with independently allocated per-case temporary
roots across unittest, pytest and coverage. Only the pure-stage subset was executed
in reversed order; a reversed full integration invocation was not performed because
the exact-command NPS-019 exception does not permit alternate elevated runners.
No separate fresh-clone checkout was made. No snapshots were added or accepted:
reviewed semantic golden masters, Excel/HTML projection certification and their
approval workflow belong to F1-05. These are explicit limits on this evidence.

#### Coverage delta

Same Windows command and tool versions as F1-03: pytest 9.2.0, pytest-cov 7.1.0,
coverage 7.17.0. JSON exported inside the sandbox using
`python -m coverage json -o .codex-log/f104/engine-coverage.json`; machine reports
remain ignored. Comparisons use the retained F1-03 JSON report and its recorded
baseline, not terminal-rounded percentages.

| Engine total | F1-03 | F1-04 | Delta |
|---|---:|---:|---:|
| Covered / statements | 1,446 / 2,858 | 2,416 / 2,858 | +970 covered; denominator unchanged |
| Missed | 1,412 | 442 | -970 |
| Line coverage | 50.5948% | 84.5346% | +33.9398 percentage points |
| Excluded lines | 0 | 0 | 0 |

Five least-covered modules after F1-04, ranked by unrounded percentage:

| Module | F1-03 | F1-04 covered / statements | F1-04 missed | F1-04 | Delta (pp) |
|---|---:|---:|---:|---:|---:|
| engine/weekly_preflight.py | 51.77% | 73 / 141 | 68 | 51.77% | 0.00 |
| engine/schedule_config.py | 27.27% | 23 / 33 | 10 | 69.70% | +42.42 |
| engine/source_config.py | 70.69% | 42 / 58 | 16 | 72.41% | +1.72 |
| engine/weekly_manifest.py | 13.58% | 61 / 81 | 20 | 75.31% | +61.73 |
| engine/weekly_excel.py | 13.93% | 245 / 323 | 78 | 75.85% | +61.92 |

For comparison, the former F1-03 bottom five all improved:

| Module | F1-03 | F1-04 | Delta (pp) |
|---|---:|---:|---:|
| engine/selam_aggregator.py | 11.64% | 83.60% | +71.96 |
| engine/weekly_manifest.py | 13.58% | 75.31% | +61.73 |
| engine/weekly_orchestrator.py | 13.59% | 90.29% | +76.70 |
| engine/weekly_excel.py | 13.93% | 75.85% | +61.92 |
| engine/selam_output.py | 15.43% | 86.42% | +70.99 |

Coverage is evidence of executed lines, not a semantic-output certification or a
new gate. Weekly preflight's remaining misses are largely CLI/reporting/error
branches; no out-of-scope production changes were made to increase the percentage.

Task DoD: scope/branch, preserved behavior, assertions, compileall, both full
runners, scoped lint/format/typing, synthetic data review, frozen trees, documentation
and Conventional Commits pass. Bug-fix and golden-master acceptance items are not
applicable to this test-only package. Architect review and human `/review` against
develop remain pending. Linux portability remains the explicitly accepted risk;
NPS-019 remains unresolved. F1-05 snapshots and production defects remain out of scope.

### F1-05A Windows candidate evidence - 2026-10-29

Branch: `test/phase-1-golden-master`, created from updated develop `e2a49bd`.
Commits in order: `b472c09` (identical config move), `01595e7` (configured POD
pattern and precise NPS label), `bf47632` (three helpers and ten methods),
`749558c` (PENDING snapshot proposals), followed by
`docs(plan): record F1-05A results and PR-gated snapshot approval`.

The user explicitly amended section 5.2 to allow candidate snapshots to be committed
on this branch before approval. APPROVAL.md is PENDING; architect reviewer,
architect review reference, product-owner approver/reference and approval date
are empty. Snapshot comparison success does not approve business behavior.
Approval happens on the future PR after full architect review and product-owner
signoff. Nothing reaches develop until both occur. This package pushes only its
branch, creates no PR, and leaves Phase 1 snapshot acceptance/closure pending.

The first move attempt failed because .codex did not exist; work stopped under
AGENTS.md section 5a. The user then authorized creating the empty directory and
retrying. The resulting git mv has 100% identical content. The POD test now reads
POD patterns/match type through the configured loader; only the plural nonmatch
comment cites NPS-005. No business configuration changed.

The ten methods cover complete pipeline, parser equivalence, rule/review matrix,
window edges, source blocking (including standalone malformed lifecycles),
cross-source duplicates, partial failure, independent-root repeatability,
mutation detection and provenance. All 141 prior method IDs remain; collection is
151 exactly. There are 141 semantic candidate files across these 14 scenarios:
complete_weekly, review_and_boundaries, cross_source_duplicates, partial_failure,
missing_argentina, missing_brazil, missing_mexico, duplicate_source,
parser_equivalence, malformed_Brazil_no_html, malformed_Brazil_no_table,
malformed_Brazil_missing_header, malformed_Brazil_bad_cells and
malformed_Brazil_orphan_group. Parser equivalence includes all eight parser variants.

The harness uses real controller/pipeline/stages/renderers and existing isolated
TEST seams, with copied catalog inputs, fresh stdlib temporary roots, absolute
lifecycle configuration, retention disabled and an injected SessionManager.
Stage files come from actual persisted artifacts. Blocked runs include real
controller preflight plus an independently inventoried manifest; standalone
malformed reports preserve failed manifests/logs/error details. No outputs are
invented for blocked or malformed runs. Catalog literal normalization/classification
facts, partition CSVs, typed JSON versus CSV serialization, source bytes and every
exported workbook field/hyperlink are checked independently of stored snapshots.

The explicit canonicalization allowlist preserves business dates, decisions,
links, order, missing keys/nulls and all fields. Registered execution IDs are
validated against sources/manifests/logs; nonempty named runtime timestamps must
be ISO and lifecycle ordered; filesystem paths must be contained. received_at is
preserved. Workbook projections use data_only=False, retaining sheet order,
nonempty cells/types/formulas/hyperlinks, dimensions, merges and freeze panes.
Full HTML/scripts/Markdown are retained, including the known copied warning.
Outside-window data follows persisted CSV types. No workbook layout/pixel or
real-data certification is claimed. Generated HTML whitespace is preserved;
scoped snapshot attributes permit original whitespace-only lines and force LF.

Candidates were exported only by explicit BTS_EXPORT_GOLDEN_CANDIDATES=1 runs to
ignored .codex-log/snapshot-candidates/F1-05A, then copied after checking all 141
SHA-256 values and synthetic provenance. Ordinary tests cannot create or accept
baselines; missing/extra files fail. Final comparison runs had export disabled.
The approval document records per-scenario parsed/READY/EXCLUDED/REVIEW/outside
and processed/failed/blocked counts, known-defect evidence and its limitations.
provenance.json records candidate and frozen runtime/config hashes and tool versions.

#### Validation

Windows / win32; Python 3.14.6, PySide6 6.11.1, openpyxl 3.1.5,
beautifulsoup4 4.15.0, pytest 9.2.0, pytest-cov 7.1.0, coverage 7.17.0.
TMP/TEMP were repository .tmp. Each exact runtime command received outside-sandbox
approval under NPS-019; static/metadata commands stayed inside the sandbox.

| Command/check | Final result |
|---|---|
| `python -m unittest discover -s tests -p test*.py -v` (export disabled) | 151 run, 151 passed, 0 failures/errors/skips; 40.025s |
| `python -m pytest -q` (export disabled) | 151 passed, 585 subtests passed, 0 failures/errors/skips; 40.32s |
| `python -m pytest --cov=engine --cov-report=term-missing -q` | 151 passed, 585 subtests passed, 0 failures/errors/skips; 41.58s |
| `python -m pytest --collect-only -q` | 151 methods collected |
| Every scenario executed a second time in independent temporary roots | Identical projections for all 14 scenarios, in both final runners and coverage |
| Mutation controls using the real comparison routine | Business date, decision and link mutations fail; runtime ID/path/timestamp changes compare equal; unknown root, invalid timestamp and reversed lifecycle rejected |
| compileall app/engine/packaging and changed tests/support | Passed |
| Ruff check and format-check on five changed Python files | Passed |
| mypy --follow-imports=skip on the same five files | No issues in 5 source files |
| Frozen-tree checks vs develop/e2a49bd and 70ad957; cached diff; status | Passed before every commit; no app/, engine/, config/ or packaging/ changes |
| Candidate hash/provenance scan | 141 exact hashes verified; no operational roots or binary artifacts |
| Git diff whitespace checks | Passed with scoped generated-HTML whitespace attributes |

Development runs caught incorrect new expectations for CSV None serialization,
first workbook data row and catalog row count, plus an unregistered inventoried_at
runtime timestamp. These were corrected before the final passing runs. The initially
unpushed POD commit received a Ruff formatting correction; no published history
was rewritten. No unrelated test failure was accepted. Case-count variance: none
(141 + 10 = 151). No Linux run or separate fresh-clone checkout was performed.

#### Coverage delta

Same F1-04 command and versions; compare its retained JSON with
.codex-log/review/F1-05A_engine-coverage.json, exported inside the sandbox using
`python -m coverage json -o .codex-log/review/F1-05A_engine-coverage.json`.

| Engine line coverage | F1-04 | F1-05A | Delta |
|---|---:|---:|---:|
| Covered / statements | 2,416 / 2,858 | 2,454 / 2,858 | +38 covered; denominator unchanged |
| Missed | 442 | 404 | -38 |
| Percentage | 84.5346% | 85.8642% | +1.3296 percentage points |
| Excluded | 0 | 0 | 0 |
| weekly_preflight.py | 73 / 141; 51.7730% | 73 / 141; 51.7730% | unchanged; 68 missed |

weekly_preflight.py remains below 75%. No tests were added to raise coverage.
These are uncovered code paths from line coverage; branch coverage was not measured:

- 60-61: malformed reference-date parsing error.
- 103: direct production environment resolution.
- 126, 131: missing or disabled source-group rejection.
- 181: unconfigured-source readiness issue.
- 263: existing input path that is not a directory.
- 273-274: SourceInventoryError conversion to WeeklyPreflightError.
- 339-432: CLI human-readable inventory/source/file/status/issue reporting,
  including matched-file and issue-printing conditionals.
- 436-466: CLI argument parser construction (date, TEST, JSON options).
- 470-501, 505: CLI main/entry point, error exit 1, JSON versus human output,
  and non-ready exit 2.

#### Review bundle and DoD

.codex-log/review/F1-05A_review_bundle.diff contains the ordered commit list,
diff --stat against develop, the full diff outside tests/snapshots/, then the full
APPROVAL.md diff and complete complete_weekly/partial_failure snapshot diffs.
It is regenerated after the final documentation commit so the commit list and
non-snapshot diff are complete. Actual bytes/line count are reported at delivery.
The ignored review artifacts are not staged or pushed.

Task DoD: scope/branch, frozen behavior, meaningful assertions, compileall, both
full runners, repeatability/mutation controls, scoped lint/format/typing,
synthetic provenance, isolation, documentation and Conventional Commits pass.
Bug-fix regression requirements are not applicable to this candidate-only package.
Architect review, product-owner approval and Phase 1 accepted golden-master closure
remain pending on the future PR. No build, GUI preview, operational access,
dependency installation or business-rule change occurred. NPS-001..007,
NPS-011..017 and NPS-019 remain outside the fix scope; observed known-defect
behavior and characterization limits are listed in APPROVAL.md.

## 10. Decision log

| Date | Decision / open item | Reason | Owner |
|---|---|---|---|
| 2026-10-28 | Phase 1 plan approved with amendments; this review changes only the plan | Explicit plan review; no implementation requested in this task | User |
| 2026-10-28 | Freeze app/, engine/, config/, packaging/ for all Phase 1 work | Safety net must precede behavior fixes/refactors | User |
| 2026-10-28 | Use weekly/, parser/, detection/, classification/, scenarios/, malformed/ directories and matching filename prefixes | Retired letters named missing operational sets in F0-01 | Product owner |
| 2026-10-28 | Approve 151 cases as an estimate; explain useful changes rather than enforcing the count | Coverage quality takes precedence over an exact total | Product owner |
| 2026-10-28 | Select Option A for Windows runs; temporary-root helper deferred to F1-06 (superseded execution evidence policy by F1-04 amendment) | Approved NPS-019 execution policy | Product owner |
| 2026-10-28 | Architect reviews full candidate diffs; product owner approves APPROVAL.md with per-scenario counts and preserved known-defect IDs/locations | Make snapshot acceptance explicit and reviewable | Product owner / architect |
| 2026-10-28 | Windows execution policy amended by F1-04: no cloud runs required | Linux portability accepted as a risk | Product owner |
| 2026-10-28 | Record engine/ pytest-cov line coverage at both closures as a baseline, not a gate | Quantify the safety net without a coverage threshold | Product owner |
| 2026-10-28 | F1-02 starts with docs(dod): align git rule with AGENTS.md | Correct contradictory DoD wording before fixture work | Product owner |

| 2026-10-28 | F1-03 includes weekly multipart fidelity before the six repairs, followed by portable assertion and results commits | Explicit task amendment; preserve decoded HTML and original 81 methods | Product owner |
| 2026-10-28 | Approve exact Windows pytest coverage command outside sandbox for F1-03 | Explicit session approval; F1-04 removes further platform evidence requirements | Product owner |

| 2026-10-29 | F1-04: only Option A remains, coverage included; NPS-018 DONE on F1-03 81/81 Windows and Path assertion code review; F1-05 needs no Linux run | Explicit task amendment; Linux portability accepted risk | Product owner |

| 2026-10-29 | F1-04 completed with exactly 60 new methods; 141/141 both runners; 84.53% Windows engine coverage | Assertion conversions preserve current behavior; F1-05 snapshot approval remains separate | Codex implementation evidence |

| 2026-10-29 | F1-05A permits PENDING candidate commits on the task branch; approval is PR-gated after architect review and product-owner signoff | Explicit user task amendment; nothing reaches develop before both approvals; push branch only, no PR | Product owner |
