# Execution Plan — F1 Phase 1 safety net

Status: PROPOSED — PLAN ONLY; implementation requires human approval.
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
- F/P/U/C/S/M shorthand has no definitions in the committed Phase 0 documents.
  Section 5.1 gives explicit proposed meanings rather than attributing invented
  definitions to F0 findings. Confirm these labels during plan review.

## 3. Scope

In scope for later approved F1-02 through F1-05:

- Test-only deterministic generation, a versioned synthetic fixture catalog,
  test harnesses, assertions, snapshots and test documentation.
- Replace the six missing-fixture lookups; make the Windows path assertion portable.
- Resolve the disposition of all 18 non-executed files in section 5.3.
- Present NPS-019 choices; implement none without the human's selection.

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

Approvals needed before implementation: this plan, the initial snapshot review
process in section 5.2, the catalog/count allocation, and an NPS-019 operating
choice in section 5.5. No business-rule approval is requested or assumed.

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

All filenames below are under `tests/fixtures/eml/`. F/P/U/C/S/M are proposed
catalog families; scenario bundles reference files rather than duplicating bytes.

| Set | Versioned files / declarations | Scenarios and Salesforce properties reproduced |
|---|---|---|
| F — foundational weekly inputs | `F_Argentina_upcoming.eml`, `F_Brazil_upcoming.eml`, `F_Mexico_upcoming.eml` | Three required source subjects; neutral Conf/✕ rows inside the window; synthetic project anchors/IDs. Brazil has an initial Billing Office th in a 14-cell row and a following 13-cell inherited-office row; Mexico has 14 plain td cells; Argentina has explicit office cells. F inputs all include a valid HTML reportTable and dataRow rows. |
| P — parser compatibility | `P_Brazil_plain_headers.eml`, `P_Brazil_sum_headers.eml`, `P_Mexico_14_td.eml`, `P_Argentina_invitation_first.eml`, `P_Argentina_invitation_last.eml`, `P_Argentina_invitation_both.eml`, `P_Brazil_forwarded_multipart.eml`, `P_Brazil_multiple_offices.eml` | Plain versus Sum headers for evaluation programme, NPS, evaluation average facilitator and Ignore Reporting; Project: Project Name and Client_Name punctuation/underscores; glyphs ✔/✕; identical record expectations across equivalent layouts. Link in Survey Invitation, Survey Invitation Link, or both (last-column anchor takes precedence). Fw: subject, multipart text+HTML, HTML attachment ignored, longest non-attachment HTML part selected; grouped office transitions and inherited rows. |
| U — detection and scope | `U_Chile_upcoming.eml`, `U_unknown_subject.eml`, `U_Argentina_last30.eml`, `U_Brazil_last30.eml`, `U_Mexico_last30.eml` | Detected but unconfigured country (using the existing detection seam where necessary), unknown/unrecognized report, and each configured Last 30 days subject. Last Results inputs are known out of scope for weekly_upcoming, not missing required sources and not parser errors. Unknown detection expectations follow inspected current detector behavior, not an invented new status. |
| C — classification and review | `C_Argentina_rules.eml`, `C_Brazil_normalization.eml`, `C_Mexico_worklist_review.eml` | Rule rows and normalization cases below; same 14-header structure with synthetic entities. Missing Project URL produces worklist REVIEW after eligibility; malformed/missing required fields or unknown boolean/status produce normalization REVIEW; invitation presence remains eligible when other current checks pass. |
| S — scenario bundles | `S_Mexico_duplicate_source.eml`, `S_Brazil_duplicate_project.eml`; bundle membership in catalog.json | Complete weekly = F trio; each missing-country bundle = F minus that country; duplicate-source bundle = F plus a second Mexico report under another filename; cross-source duplicate = same synthetic Project ID/date/session in two otherwise valid sources. Include complete six-report bundle = F plus three U_last30 files; out-of-window, business review and worklist review bundles use C rows. Existing-run uses complete F with a precreated isolated run; partial processing failure combines two F inputs with one M input. |
| M — malformed / failing input | `M_Brazil_no_html.eml`, `M_Brazil_no_table.eml`, `M_Brazil_missing_header.eml`, `M_Brazil_bad_cells.eml`, `M_Brazil_orphan_group.eml` | Valid detectable Upcoming envelope but no HTML; HTML without reportTable; recognizable header row missing a required column; wrong data-row width (12/15); 13-cell row before an office exists. Assert current parser exceptions and failed-file lifecycle. A second failure mode injects a controlled parser exception after a valid F report enters processing. |

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

Versioned .eml tracking: F1-02 may add a narrow `.gitignore` allow rule for
`tests/fixtures/eml/*.eml` only, including any required parent unignore. No global
removal of the .eml prohibition and no force-adding unknown emails. Review every
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
3. Architect/reviewer reviews parser fidelity and projections; product owner explicitly
   approves the initial baseline and any business-visible difference. Initial approval
   must identify preserved NPS defects. No snapshot update can authorize a rule change.
4. Only after approval copy named candidates to tests/snapshots and commit them in a
   separate `test: approve phase 1 golden master snapshots` commit, with approval
   reference and reason in the commit/PR description. Never bulk-accept unexpected diffs.
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
| test_duplicate_source_is_blocked | F trio plus a second copy of F Mexico under a distinct filename; expect source duplicate blocking, not cross-project deduplication |
| test_existing_weekly_run_is_blocked | F trio plus the expected weekly output directory under a fresh TEST root |
| test_missing_argentina_is_blocked | F Brazil and F Mexico only |
| test_missing_brazil_is_blocked | F Argentina and F Mexico only |
| test_missing_mexico_is_blocked | F Argentina and F Brazil only |
| test_failed_report_is_moved_to_error | F Brazil, with the existing controlled parser exception injected after the lifecycle enters processing; assert error move/details/manifest/log and propagated exception |

These six tests must become passing assertions, never skipped, xfailed or converted
to expected failures. Retain a separate actual malformed-M parser test later so
controlled injection does not stand in for malformed-input coverage.

At tests/test_controller_session_integration.py:246 replace the literal Windows
separator expectation with `str(Path('output') / 'report.xlsx')` (or an equivalent
Path comparison). Keep the exact relative location assertion; do not assert only
the filename. Run the same 69 original test IDs on Windows and Linux. NPS-018 is
closed only after both operating systems have evidence, not merely a local edit.

### 5.5 NPS-019 choices — human decision required

The F0-02 diagnosis established that mkdtemp's 0o700 ACL is unusable by the Windows
restricted token; setting TMP/TEMP inside the repository did not fix it. Do not
change ACLs or monkeypatch global tempfile/os functions to get a green run.

| Option | Pros | Cons / limits |
|---|---|---|
| A. Retain the current explicit-approval exception for exact Windows unittest/pytest commands | Exercises the actual Windows environment without altering tests or production code; supported by F0-02 baseline | Every elevated run requires explicit approval and runs outside token confinement; does not repair the sandbox. Exact-command limitation complicates alternate tooling/coverage commands |
| B. Run automated suite in the configured Linux cloud; human also runs Windows locally | Linux isolation avoids the observed Windows ACL incompatibility and tests NPS-018 portability | Linux alone cannot certify Windows. Cloud dependencies/wrapper must already be available; no automatic installs or packaging. Requires a separately recorded Windows run |
| C. Introduce a portable test-only temporary-root helper using ordinary inherited-permission directories | Can keep test-created roots inside the sandbox without weakening production code or the stdlib; explicit containment/cleanup contracts | Touches many existing test setups, needs careful unique allocation and cleanup validation, and may not control Qt/third-party tempfile usage. Could mask isolation mistakes; must preserve temporary .exe cleanup constraints |

No option is selected by this plan. NPS-019 remains PLANNED until the human selects
an approach and its acceptance criteria are verified. Option C is not included in
the case-count budget below: if selected, revise this plan before implementation to
identify every affected test and additional helper tests. A/B do not change counts.
A manually approved exception is an operating accommodation, not an underlying fix.

### 5.6 Sequenced execution work packages

Each branch starts from updated develop after the previous package is reviewed and
merged. No implementation starts from an unapproved plan or unapproved snapshot.
Publish task branches only; PRs target develop. Record actual counts and explain any
variance before changing the budget; never remove useful tests to meet a number.

| # | Task / branch | Files | Planned commits, in order | Validation / expected counts |
|---|---|---|---|---|
| F1-02 | Synthetic inputs; test/phase-1-fixtures | tests/support generator/path helpers, tests/fixtures catalog/rows/eml/manifest, tests/test_fixture_catalog.py, narrow .gitignore exception | `test: add deterministic synthetic report fixtures`; `test: validate synthetic fixture catalog contracts` | Two generations to separate scratch roots have identical bytes/hashes; catalog schema/provenance, six families and structural signatures checked; no operational names/paths. Add 12 TestCase methods: six family contract tests plus determinism, byte/MIME stability, invented-entity schema, safe links/IDs, catalog/hash completeness and immutable-copy behavior. Total 81: Windows 75 pass + 6 known errors; Linux 74 pass + 1 known path failure + 6 errors |
| F1-03 | Restore clean-clone baseline; test/phase-1-baseline | tests/test_backend_blocking_scenarios.py, tests/test_processing_error_lifecycle.py, tests/test_controller_session_integration.py, tests/support/fixture_paths.py | `test: replace missing operational fixture dependencies`; `test: make controller output path assertion portable` | Original six tests pass using F inputs, original 69 test IDs retained; no new methods. Both runners: 81 collected/run, 81 pass, 0 failures/errors/skips on Windows and Linux; no tests require a prior run |
| F1-04 | Convert inventory; test/phase-1-test-conversion | The 18-file disposition map and its named destinations; tests/manual frontend preview; test-only harness support | `test: convert stage and rule print scripts to assertions`; `test: convert weekly integration scripts to isolated cases`; `test: move interactive failure preview out of discovery` | Add exactly 60 proposed methods from section 5.3; total 141/141 pass on both runners and operating systems. All retained test_*.py files contribute cases; importing modules does not run scenarios or print pass/fail verdicts. Confirm intentional wrong POD expectation fails the test, then restore the scratch expectation before committing |
| F1-05 | Golden master and closure evidence; test/phase-1-golden-master | tests/support projections/candidate helper, tests/test_pipeline_golden_master.py, tests/snapshots/phase1/v1, tests/README.md; update only Phase 1 evidence in documentation | `test: add semantic pipeline golden master comparisons`; after explicit review `test: approve phase 1 golden master snapshots`; `docs: record phase 1 safety net validation` | Add 10 methods: complete pipeline, parser-equivalence variants, rule/review matrix, window edges, source-blocking bundles, cross-source duplicates, partial processing failure, canonicalization repeatability, meaningful-field mutation detection, snapshot/catalog/config provenance. Total 151/151 pass, 0 failures/errors/skips on both runners/OSes; compare complete projections including Excel/Slack; assert frozen production tree unchanged |

Count budget: 69 original + 12 fixture contracts + 60 converted cases + 10 golden
master methods = 151. Matrix rows use subtests and do not multiply collected cases.
Counts are implementation targets, not results claimed by F1-01. Any extra needed
test must be justified and the expected counts revised openly. Phase 1's success is
meaningful asserted coverage and clean-clone parity, not the exact number 151.

## 6. Validation strategy

For each approved implementation package:

- Run compileall for app/engine/packaging and new test/support modules.
- Run unittest discovery and `python -m pytest -q` from the root using the local
  virtual environment; record run/passed/failures/errors/skips and collected IDs.
  Set TMP/TEMP to repository .tmp before Python starts. Under option A request
  approval for the exact test commands only; no compound elevated scripts.
- On configured Linux, use `/workspace/.setup/bts/headless.sh` for Python and Qt
  headless settings. Do not launch the interactive manual preview on either platform.
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
  canonicalization allowlist, initial snapshots and explicit NPS-019 selection.

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
| tempfile ACL incompatibility persists | Confirmed | Windows sandbox cannot complete suite | Human selects NPS-019 option; no implicit sandbox workaround |
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
- [ ] Human approves plan, family labels and count allocation.
- [ ] Human selects NPS-019 option and confirms cross-platform execution ownership.
- [ ] F1-02: synthetic fixture catalog and generator.
- [ ] F1-03: six repaired tests and portable path assertion.
- [ ] F1-04: all 18 file dispositions completed.
- [ ] Human approves initial golden master candidates with architect review.
- [ ] F1-05: approved snapshots and cross-platform closure evidence.

## 10. Decision log

| Date | Decision / open item | Reason | Owner |
|---|---|---|---|
| 2026-10-28 | F1-01 writes only this plan; implementation waits for approval | Explicit PLAN ONLY request | User |
| 2026-10-28 | Freeze app/, engine/, config/, packaging/ for all Phase 1 work | Safety net must precede behavior fixes/refactors | User |
| 2026-10-28 | Proposed F/P/U/C/S/M family meanings and 151-case budget need review | Shorthand was not defined in committed F0 evidence; counts are design targets | Product owner / architect |
| 2026-10-28 | NPS-019 option A/B/C remains undecided | Explicit instruction that the human decides | Product owner |
| 2026-10-28 | Initial and later snapshots require explicit acceptance, including known-defect annotations | Prevent silent changes to the behavioral contract | Product owner / architect |
| 2026-10-28 | Confirm Windows/Linux execution ownership and evidence availability | NPS-018 cannot be closed from a single-platform run | Product owner |
