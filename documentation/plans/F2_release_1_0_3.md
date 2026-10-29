# Execution Plan — F2-01 Release 1.0.3

Status: PLAN ONLY; implementation and release execution are not authorized by this document.
Prepared 2026-10-29. Product owner: Mateo Hernández. Architect/reviewer: Claude.

## 1. Purpose

Deliver and certify patch release 1.0.3: make source failures visible, retain invitation
information, correct Slack copying, exclude POD/PODs, clarify orphan-row errors, remove
verified dead code and reconcile documentation. Preserve all other business decisions.
Phase 2 includes Windows certification and manual production promotion, not just fixes.

## 2. Context

Read together with AGENTS.md, ENGINEERING_STANDARDS.md, DEFINITION_OF_DONE.md,
DEVELOPMENT_ROADMAP.md and F1_phase_1_safety_net.md. Paths below are repository-relative;
line references have been rechecked against merged develop at `8865741` (PR #9),
not future edited line numbers. Application/config files are unchanged from `b2c4c77`.

The planning branch originally started at `b2c4c77` (PR #8); develop `8865741` now
includes F1-06 through PR #9 and was merged into this branch with a merge commit,
without rebasing. Phase 1 is DONE: 169 tests and 141 approved candidate hashes.
The merged F1-06 evidence records 169/169 on both runners, engine line coverage
2,523/2,858 (88.2785%) and weekly_preflight.py 140/141 (99.2908%; only line 505,
the direct-module entry shim, uncovered). These are now integrated develop results.
The Phase 1 plan's F1-06 closure section remains the coverage evidence; no code,
configuration, test or snapshot changes are introduced by this planning update.

Current relevant layers are source processing/orchestration, application controller,
regional aggregation, worklist/Excel/HTML rendering, and the registered Weekly Run UI.
The approved baseline is `tests/snapshots/phase1/v1/`; its APPROVAL.md records PR #8.
Phase 1 preserved these defects deliberately; approval of a baseline does not approve
the proposed fixes or an invitation-based exclusion rule.

## 3. Scope

In scope: NPS-001, NPS-002, NPS-003, NPS-005, NPS-020, NPS-011, NPS-012;
the already-correct off-Monday UI contract test; version 1.0.3; documentation,
certification, release PR/tag, and owner-operated promotion/rollback preparation.

Out of scope: NPS-004, NPS-006, NPS-015 and NPS-016 until separately approved;
NPS-007 window unification, NPS-013 extensibility and other 1.1.0 refactors;
NPS-014 retention/config synchronization; NPS-017 path injection; NPS-019 tooling;
NPS-021 JSON CLI failure output; FEAT-001 and V2 lifecycle/resume capabilities.
Recording these backlog requirements is not implementation authorization.

## 4. Constraints

- Never access the operational installation or OneDrive NPS_AUTOMATION as an agent.
  Production promotion and real-report acceptance are performed by the product owner.
- Synthetic, versioned fixtures only in Git; no production names, reports, exports or
  secrets. No new dependencies, process termination, destructive cleanup or history rewrite.
- Preserve source attribution, row order, window boundaries, existing REVIEW decisions,
  links and duplicate handling except the explicitly approved changes below.
- POD/PODs exclusion was decided by Mateo Hernández on 2026-10-29. Existing invitation
  data must be displayed, never used to change eligibility (NPS-016 remains undecided).
- Off-Monday operation was decided by the product owner on 2026-10-29: selected date
  maps to the Monday of that same week (Monday maps to itself); the processing window
  is Tuesday through the following Monday, inclusive. Execution day does not restrict use.
- D1–D3 were decided by Mateo Hernández on 2026-10-29 and are recorded below.
  They define future implementation scope; this task still changes documentation only.
- Each issue gets its own branch and PR into develop, from updated develop after the
  preceding approved PR. Snapshot proposals remain pending until architect review and
  product-owner signature on that PR. No automatic baseline acceptance.
- For every Git write, check .git for locks, then request approval for the exact command
  outside the local sandbox. Stop on locks or an approved command failing. No direct
  commits to main/develop. Building and promotion require a later execution task.

## 5. Steps

| # | Step | Files | Validation | Commit message |
|---|---|---|---|---|
| 1 | F1-06 merged via PR #9; verify integrated baseline | Existing F1-06 changes; no copying into this plan | 169 tests, recorded coverage, 141 unchanged candidate hashes | Merge origin/develop into chore/phase-2-plan |
| 2 | Implement NPS-001, approved D1 A | Orchestrator/controller, run lifecycle and failure tests | Failed source never success; recovery rehearsal | See 5.1 |
| 3 | Implement NPS-002, approved D2 C | Worklist and CSV/Excel projections only | Invitation text/link in approved exports; Slack byte-identical | See 5.2 |
| 4 | Implement NPS-003 | HTML renderer and copy tests | Visible warning excluded from every copy path | See 5.3 |
| 5 | Implement NPS-005 | Business rules config, expected fixture metadata, tests | Singular/plural boundaries; only intended exclusion | See 5.4 |
| 6 | Implement NPS-020 | Email parser, orphan-error expectations | Actionable error; parsing behavior unchanged | See 5.5 |
| 7 | Implement NPS-011, approved D3 disposition | Named legacy files and import/registration checks | Active UI and retained tools preserved | See 5.6 |
| 8 | Implement NPS-012 | Documentation and consistency checks | Current UI/version/flow/count claims verified | See 5.7 |
| 9 | Pin selected-date contract | Weekly Run UI tests only | Monday–Sunday, window and signal assertions | See 5.8 |
| 10 | Prepare and certify release | Four version surfaces, docs, release evidence | Section 5.9 and release DoD | chore(release): prepare version 1.0.3 |

### 5.1 NPS-001 — failed source reported as success (D1)

Current: `engine/weekly_orchestrator.py:141–145` returns COMPLETED_WITH_REVIEW after
mixed success/failure. `engine/application_controller.py:472–510` treats it as success
with empty issues. `engine/process_weekly_run.py:314–343` continues to regional outputs;
`engine/selam_aggregator.py:302–304` skips failed sources. The UI success path at
`app/main_window.py:793–810` consequently presents READY/success.
Evidence: `partial_failure/operation.json` says success=true, issues=[],
COMPLETED_WITH_REVIEW; `partial_failure/weekly_manifest.json`, summary.json,
excel_cells.json and slack.html show two processed sources and outputs missing one.

Both choices below require FAILED, success=false, a red failed UI status and actionable
issues naming the failed source/country/file, error and processed/failed counts.
A run with all sources processed and ordinary manual-review rows retains its existing
behavior. No choice may report success when any source failed.

| Option | Operator sees: UI/issues/Excel/HTML | Recovery | Pros / cons |
|---|---|---|---|
| A — withhold weekly outputs (recommended) | FAILED plus source issues; no regional Excel, HTML, CSV or Slack Markdown; disable output/copy actions for the failed attempt, including stale output from another attempt | Archive failed attempt intact; correct/re-export failed report; resubmit fresh copies of all three reports and restart that failed week under controlled recovery | Smallest safe publish contract; cannot accidentally work a partial list. Requires complete resubmission |
| B — quarantined diagnostics | Same FAILED/issues; partial Excel and HTML visibly INCOMPLETE with failed source identified; diagnostic links only, all Slack copy paths disabled; diagnostic CSV/Markdown never offered as publishable results | Same full restart as A; diagnostic rows must not be acted on | Easier diagnosis; more UI/file safeguards and risk of exporting partial data |

D1 decision — Mateo Hernández, 2026-10-29: Option A is approved, including the
owner-assisted failed-attempt recovery procedure below. Option B is retained only
as decision history; it is not authorized for implementation.

Recovery is part of D1, not an assumed existing feature. Currently source files move
to processed/error, and `engine/weekly_run.py` create_weekly_run refuses an existing
weekly directory; session reset alone cannot retry it. Specify an owner-assisted,
documented failed-attempt archive/reset procedure (only FAILED attempts, preserving
source artifacts, error details, manifests and logs), then rerun the same reference
Monday with a full fresh source set. Test it in isolated roots. Never use overwrite=True
as a production shortcut, never overwrite a completed week, and never delete evidence.
Failed-source-only resume/deduplication is a separate lifecycle feature, not this patch.

Branch: `fix/nps-001-failed-source-status`. First commit
`test: reproduce failed source success and unsafe weekly outputs`: controller + pipeline
tests must fail on current success/status/issues/output behavior; pin all-success and
all-processed/manual-review controls. Add a failed-attempt recovery integration test
proving evidence preservation, no stale links and no duplicate output. Then
`fix(orchestrator): fail weekly runs with failed sources` implements the selected contract
through backend, UI and recovery documentation. Finally propose reviewed snapshots
with `test: propose NPS-001 golden master changes`. Run section 6 and exercise UI failure.

Exact baseline delta for A, under `partial_failure/` only:
- Modify operation.json and weekly_manifest.json (failure status/issues).
- Delete consolidation_issues.json, manual_review_issues.json, selam_consolidated.json,
  selam_manual_review.json, summary.json, weekly_csv.json, excel_cells.json, slack.html
  and slack_ready.md: weekly aggregation/publication no longer occurs.
- Retain all per-source artifacts byte-identically, including error_details.json,
  execution_manifest.json, execution_summary.json, csv.json and slack_ready.json.

The Option A file list is the implementation allowlist. Unexpected deltas are defects
to investigate, not permission to enlarge the list silently. The discarded Option B
does not supply an alternative snapshot allowlist.
The harness currently expects success for weekly scenarios: collect the intended
FAILED partial-failure manifest explicitly, while keeping unexpected failures fatal.
Do not fabricate an application manifest; the blocked-case test inventory is distinct.

### 5.2 NPS-002 — invitation visibility (D2)

Current: `engine/stages/email_parser.py:459–465,508–512` captures invitation text/link;
`engine/stages/worklist.py:368–418` drops them. Output schemas omit them at
`engine/selam_output.py:20–32`, `engine/stages/slack_output.py:5–14`,
`engine/weekly_excel.py:1403` and `engine/slack_canvas_renderer.py:15`.
Compare complete_weekly/raw.json with worklist.json, weekly_csv.json, excel_cells.json
and slack.html. review_and_boundaries/raw.json and selam_manual_review.json preserve
additional original fields that are absent from ordinary output columns.

Target is visibility only, with no invitation-based exclusion or REVIEW decision.
The original A/B alternatives below are retained as history; neither is selected.

| Option | Output contract | Pros / cons |
|---|---|---|
| A — two explicit columns (original recommendation; not selected) | Carry text/link in worklist JSON/CSV; append Survey Invitation and Survey Invitation Link to regional CSV, Excel and Slack HTML/Markdown. Include worklist REVIEW rows; expose original invitation fields in manual-review CSV/Excel too | Explicit, auditable, consistent across surfaces; wider tables |
| B — compact display | Preserve both raw fields in JSON/CSV; show a compact invitation text/hyperlink cell in Excel, HTML and Markdown, with full URL available in the cell/link; manual-review export preserves both original values | Narrower display; link less obvious when printed or copied as text, needs careful fallback tests |
| C — export-only explicit columns (approved) | Survey Invitation and Survey Invitation Link in worklist JSON/CSV, regional CSV and Excel Worklist/Revision Manual only; preserve all existing Slack surfaces | Auditable export fields without widening Slack output; invitation details are available through exports only |

D2 decision — Mateo Hernández, 2026-10-29: Option C is approved. Both explicitly named
columns must appear in worklist JSON/CSV (including worklist REVIEW rows), regional
worklist/manual-review CSV and Excel Worklist/Revision Manual sheets. Map existing
manual-review survey_invitation/survey_invitation_link values at export time; do not
add aliases to the original selam_manual_review.json records. Preserve invitation
text/URL values, render Excel hyperlinks safely and keep missing values empty.

Slack HTML, regional and per-source Markdown, slack_ready JSON/CSV outputs and every
Copy for Slack path remain byte-identical to the immediately preceding approved
baseline for this issue. Keep SLACK_COLUMNS and shared Markdown OPERATIONAL_COLUMNS
unchanged; extend CSV/Excel-specific schemas instead. The separate NPS-003 copy fix
and NPS-005 row exclusions retain their own explicitly authorized Slack diffs.

Branch: `fix/nps-002-invitation-visibility`. Commit
`test: reproduce invitation loss across weekly outputs` first: synthetic invitation
text and distinct URL must survive worklist, regional aggregation, CSV and Excel
Worklist/Revision Manual cells/links, including missing text/link, escaping and REVIEW
rows. Assert unchanged decisions, counts, grouping and source attribution. Add controls
that compare full Slack HTML, both Markdown outputs, slack_ready records/CSV and all
copy paths against their prior behavior, not just absence of new headers. Then
`fix(outputs): preserve survey invitation fields in CSV and Excel`; then
`test: propose NPS-002 golden master changes`. Preserve URL values and avoid making
unsafe URL schemes clickable. Run section 6; no new business classification.

Exact semantic snapshot allowlist for approved Option C, after approved NPS-001 A
(19 files; all paths below are relative to tests/snapshots/phase1/v1/):

- In each of complete_weekly, review_and_boundaries and cross_source_duplicates:
  worklist.json, csv.json, selam_consolidated.json, weekly_csv.json and excel_cells.json
  (five each: new worklist fields, regional CSV columns and the two Excel sheets).
- partial_failure/worklist.json and partial_failure/csv.json (per-source outputs only;
  D1 A has already removed regional publication for that failed week).
- review_and_boundaries/worklist_review.json and parser_equivalence/worklist.json.

selam_manual_review.json already retains original invitation keys; it stays identical.
csv.json changes only worklist.csv/worklist_review.csv sections; slack_ready.csv and
all other embedded CSV sections remain identical. weekly_csv.json changes the regional
worklist/manual-review CSV schemas and values only. excel_cells.json changes Worklist
and Revision Manual only; Home, Manifest and Issues sheets stay identical. Duplicate
diagnostics currently embed complete worklist records at engine/selam_aggregator.py:235–262:
preserve their existing field set when adding invitation fields, so neither
cross_source_duplicates/consolidation_issues.json nor the Excel Issues sheet acquires
these export-only fields. Test this boundary explicitly; do not expand the allowlist
to accommodate incidental propagation. Raw/normalized/classified data, outside-window
rows, manifests, summaries, issues and every Slack snapshot remain byte-identical.
Only provenance.json candidate hashes and a signed APPROVAL.md addendum accompany
these 19 semantic files; no behavior-input or fixture changes are needed for NPS-002.

### 5.3 NPS-003 — warning copied into Slack

Current: `engine/slack_canvas_renderer.py:516` inserts the separate-email warning row
inside the client table. Copy at lines 1090–1091 uses table.outerHTML/table.innerText;
the selection fallback at line 1119 also selects that table.
Evidence: review_and_boundaries/slack.html contains the warning in the copied table.

Target: keep the warning visible next to its client group and preserve marked records,
but place it outside the copyable table so HTML, plain text and selection fallback all
exclude it. Do not remove the warning from the operator's screen or change record order.
Branch: `fix/nps-003-slack-copy-warning`. Commit
`test: reproduce warning leakage into Slack copies` with DOM/table-boundary assertions
that fail today, then `fix(slack): keep separate-email warnings outside copied tables`,
then `test: propose NPS-003 golden master changes`. Check all three copy paths with
existing Qt WebEngine support and a Windows manual clipboard check; no new browser dependency.

Exact snapshot delta: slack.html in complete_weekly, review_and_boundaries and
cross_source_duplicates, because the shared warning CSS changes. D1 A removes
partial_failure/slack.html before this issue. Only review_and_boundaries changes warning
placement; the others change shared CSS. No Markdown, JSON, CSV or workbook delta is expected.

### 5.4 NPS-005 — plural PODs exclusion (decided)

Current: `config/business_rules.json:35–36` uses `\bpod\b`; the regex matcher is
`engine/stages/business_rules.py:88`. The control_plural synthetic row (Fixture Session
PODs) remains eligible/READY in review_and_boundaries/classified.json and worklist.json,
and cross_source_duplicates/classified.json and worklist.json. Its source/raw row stays.

Target: exclude standalone POD and PODs, case-insensitively, using `\bpods?\b` or an
equivalent reviewed pattern. Embedded words such as Empoderamiento remain non-matching.
Branch: `fix/nps-005-pod-plural`. First `test: reproduce plural POD exclusion gap`:
test both configured project fields, case variants, punctuation/boundaries, singular,
plural and embedded negative controls; update the old plural characterization deliberately.
Then `fix(rules): exclude singular and plural POD names`, including required config
version/CHANGELOG handling; then `test: propose NPS-005 golden master changes`.
Do not hardcode a competing pattern into tests: load configuration and assert its behavior.

Exact set, in review_and_boundaries and cross_source_duplicates only:
classification_partitions.json, classified.json, csv.json, execution_summary.json,
worklist.json, slack_ready.json, selam_consolidated.json, summary.json, weekly_csv.json,
weekly_manifest.json, excel_cells.json, slack_ready.md and slack.html. One plural row
moves from eligible/READY to excluded per scenario; singular-POD matched_pattern strings
also change to the new configured expression without changing those existing decisions.
review_and_boundaries READY 26→25, EXCLUDED 37→38, REVIEW 17 unchanged;
cross_source_duplicates READY 10→9, REVIEW 9 unchanged. Confirm all other counts against
fixture identities, not only totals. Raw rows, review aggregates and parser_equivalence
stay identical. Update tests/fixtures rows.json rule expectations and fixture_manifest.json
input hashes, not rendered .eml bytes. Only business_rules.json and affected fixture
metadata input hashes change in provenance; validate all 26 .eml hashes unchanged.

### 5.5 NPS-020 — orphan grouped-row error

Current: `engine/stages/email_parser.py:301–335` accepts a full 14-cell row and a
13-cell row that inherits a preceding Billing Office, but an orphan 13-cell row reaches
the contradictory generic size error. Evidence:
malformed_Brazil_orphan_group/error_details.json (including final traceback exception)
and execution_manifest.json. It fails closed today; preserve that lifecycle and ValueError.

Target message: "La fila de 13 celdas no tiene un Billing Office anterior para heredar."
Keep valid inherited 13-cell rows and unrelated malformed-size errors unchanged.
Branch: `fix/nps-020-orphan-billing-office-error`. First
`test: reproduce misleading orphan grouped-row error`, asserting actionable error and
failed lifecycle plus valid inherited-row and other-size controls. Then
`fix(parser): explain missing inherited Billing Office`; then
`test: propose NPS-020 golden master changes`. Run parser, lifecycle and full section 6.

Exact snapshot delta: malformed_Brazil_orphan_group/error_details.json and
execution_manifest.json only, for the error and final exception message. csv.json and
report_context.json remain identical. Update catalog.json expected_parse_error and
fixture_manifest.json metadata/input hashes; all synthetic .eml bytes remain identical.
Traceback frames, source paths and line numbers must never enter projections.

### 5.6 NPS-011 — verified dead code (D3)

Current evidence: `app/main_window.py:29` imports the active nested WeeklyRunView;
line 282 onward registers five views. `app/views/weekly_run_view.py:31` is the legacy
class; `app/views/manual_review/manual_review_view.py:25` is unregistered, but
manual_review_view_preview.py imports it. No semantic golden file proves import
reachability; this is structural evidence, not a claimed pipeline defect.

Branch: `fix/nps-011-dead-code`. First record consumers with rg and preserve an active
UI construction/signal smoke test. Add a failing structural check that concrete runtime
view classes are registered or reachable from registered views, with explicit preview
exceptions; current orphan runtime classes violate it. Commit
`test: characterize active views and legacy consumers`, then
`refactor(ui): retire verified unused views and scripts` under approved D3.

D3 decision — Mateo Hernández, 2026-10-29: owner confirmed no manual use of the four
legacy processing scripts. Delete exactly tests/scripts/apply_business_rules.py,
tests/scripts/normalize_fields.py, tests/scripts/generate_worklist.py and
tests/scripts/generate_slack_output.py; delete app/views/weekly_run_view.py. Move
app/views/manual_review/manual_review_view.py and manual_review_view_preview.py together
to tests/manual/manual_review_preview/, preserving useful preview behavior and updating
imports/package markers as needed. Retain tests/scripts/cleanup_retention.py and all
inspection/extraction/read scripts; never execute retention. Do not extend the deletion
list. Check repository consumers before the future removal; owner confirmation is already
recorded and does not require another manual-use decision.
Run active UI/import smoke checks and both runners. All 141 baseline candidates
(or the approved post-NPS-001 count) and behavior-input hashes must stay byte-identical.

### 5.7 NPS-012 — documentation drift

Current: documentation/README.md:7,9,24,69,78 gives old versions, Manual Review screen,
64/64 and future Power Automate integration; documentation/VERSION.md:37,51 gives
69/69/future integration; documentation/WEEKLY_OPERATION.md:5,207,315 describes 1.0.0
and a separate Manual Review screen; documentation/ROADMAP.md:5,30 repeats old version
and future ingestion. Compare the five registered views at app/main_window.py:282
and current file-based email ingestion. No golden file represents prose correctness;
complete_weekly outputs are an unchanged regression control, not evidence of these claims.

Target: document the actual UI (manual review integrated with weekly outputs), existing
Power Automate .eml capture, current procedures and dated, commit-bounded validation
counts. Distinguish certified production 1.0.2 from candidate 1.0.3 until release approval;
do not claim Salesforce API integration. Reconcile README, VERSION, WEEKLY_OPERATION,
ROADMAP, ARCHITECTURE where needed, and tests/README.md against the merged F1-06 baseline.
Branch: `fix/nps-012-documentation-drift`. First
`test: detect documented version and workflow drift`: narrow consistency checks against
version metadata, registered views and actual ingestion contract must fail on the stale
claims (avoid tests that merely search for their own new prose or exact test count).
Then `docs: align operations and version documentation`; validate links, claims and
operator walkthrough plus section 6. No semantic snapshot or provenance-input changes.

### 5.8 Off-Monday Weekly Run contract — test only in 1.0.3

The implementation already complies: configuration_card.py:402–407 subtracts
selected_date.weekday(); lines 409–416 compute Monday+1 through Monday+7;
lines 448–461 return reference_date_text. weekly_run_view.py:146–155 emits that
reference date for both preflight and processing, not the raw selected date at card:464.
These paths are under app/views/weekly_run/. Backend weekly_preflight.py:60–86 still
validates a Monday reference; this does not prohibit execution on another day.
There is no existing golden snapshot of the date picker; complete_weekly/preflight.json
pins the backend reference/window, not UI conversion.

Branch: `fix/nps-007-reference-monday-contract` (contract test only; NPS-007 remains
Phase 3). Commit `test: pin weekly UI reference Monday for any selected day`:
construct the card/view with fixed dates and assert reference text, displayed inclusive
window and both emitted operation dates for Monday through Sunday; include a year
boundary (2026-01-01→2025-12-29, window 2025-12-30 through 2026-01-05).
Monday maps to itself. Tests should pass before any application change; no fake failing
test is required for already-correct behavior. No production fix or golden delta is
expected. Preserve this contract when NPS-007 unifies schedule calculation in 1.1.0.

### 5.9 Release preparation, certification and promotion

After the issue PRs and UI contract test merge, create release/1.0.3 from updated
develop. No direct commits to main/develop. Commit
`chore(release): prepare version 1.0.3` and `docs: record 1.0.3 certification results`
separately; submit the release PR into main only after all gates below. Synchronize
release-only changes back to develop through a PR. No release actions occur in F2-01.

1. Update documentation/VERSION.md (the repository's VERSION.md),
   documentation/CHANGELOG.md, app/main_window.py:223 application_version,
   packaging/windows_version_info.txt:4–5,21,26: product 1.0.3, Windows 1.0.3.0.
   Record approved POD policy and operator-visible fixes; reconcile all release docs.
   Test version consistency before bumping, then full suite. Metadata changes alone
   must not change semantic snapshots. Record actual release source hashes separately
   from the historical Phase 1 informational source_sha256.
2. On Windows, explicitly authorize a build in a fresh disposable source checkout
   with existing dependencies, no prior build/dist artifacts and no .exe to clean.
   Inspect before invoking packaging/build_release.py: its cleanup removes build/dist;
   never run it over a populated distribution or delete any executable as an agent.
   The builder imports validate_release as a sibling module. To obey the module-launch
   rule, launch from the checkout root with packaging added to PYTHONPATH, preserving
   the existing value, then `python -m build_release` and `python -m validate_release`.
   Confirm the module resolves to this checkout before building. A repeat uses another
   clean checkout; a locked file is closed by the human, never by killing processes.
3. Require validate_release to pass, correct executable/file version, approved config
   inventory, clean TEST/PRODUCTION directory layouts, and no bundled reports, secrets
   or development output. Preserve the certified artifact and hashes. No dependency
   installation or packaging refactor is implicit in the release task.
4. Run the packaged executable in TEST against synthetic complete, review/duplicate,
   missing-source, mixed-failure and orphan-report scenarios in an isolated release
   data root. Verify selected-date conversion, visible failed status/issues, recovery,
   output availability, invitation values/links, POD/PODs, Excel sheets and all Slack
   clipboard paths. Record screenshots/checklist without real identities; confirm
   TEST writes never reach PRODUCTION. Excel semantic cells do not certify layout.
5. The owner runs preserved certified 1.0.2 and candidate 1.0.3 in separate nonoperational
   copies against identical real weekly reports, kept locally outside this repository
   in an owner-controlled local_acceptance/ workspace. Never open the operational
   installation as an agent. Keep immutable originals and independent input copies,
   since processing moves files; isolate output/log/runtime roots and record effective
   config hashes. No real files, identities or exports enter Git/review bundles.
6. Compare source inventory and attribution; parsed rows; excluded/REVIEW/READY and
   outside-window identities/counts; date boundaries; duplicates; invitation text/URLs;
   Excel values/links/sheets; HTML/Markdown content, order, warnings and clipboard result.
   Ignore only declared runtime IDs/timestamps/root prefixes, never business dates or
   decisions. Approved differences are the selected NPS-001 contract, invitation display,
   warning copy boundary, standalone PODs exclusion, orphan message and version metadata.
   Every difference needs row-level explanation; any unexplained missing source/row,
   changed decision/link/date/order blocks release. Include a clean week and representative
   known edge cases; supplement unavailable real failure cases with synthetic evidence.
   Do not post to Slack or create NPS during comparison. Owner signs comparison results
   and limitations in the release PR; retain sensitive evidence only locally.
7. Complete release DoD and obtain architect review plus Mateo's explicit go/no-go
   approval in the release PR. Merge release/1.0.3 into main, create tag v1.0.3 on
   that merged commit and push tag/artifact. Record exact commit, artifact/config hashes,
   test counts, coverage, approvals and rollback location. Main remains certified only.
8. Product owner manually closes the application, preserves a restorable 1.0.2 artifact
   and pre-promotion config/data backup, stages and verifies 1.0.3, then replaces only
   application payload. Preserve input/, output/, logs/, runtime/ and operational
   config/. Apply only the approved POD rule/config-version migration after comparing
   effective config with the certified candidate; do not overwrite operational config
   with repository defaults (NPS-014 remains open). Verify UI version, TEST isolation
   and first weekly operation before marking Phase 2 production promotion complete.

For human Git work use GitHub Desktop: Branch > New branch..., Repository > Push,
Branch > Create Pull Request (review/merge in GitHub), and History > right-click the
release merge commit > Create Tag..., then Repository > Push. The agent performs
authorized Git writes when possible; these are fallback instructions, not a request
for the human to use a terminal.

## 6. Validation strategy

For this planning task: check evidence, scope/options, links, snapshot filenames,
template sections and git diff --check; verify only the two requested Markdown files
changed. No runtime tests/build or snapshot regeneration is needed for prose-only planning.

Post-merge verification, 2026-10-29: compileall passed; the exact unittest runner
passed 169/169 (91.823s), and pytest passed 169 tests plus 590 subtests (88.25s),
with no failures, errors or skips. All 141 candidate hashes, 10 behavior-input hashes
and 26 synthetic email hashes remain identical. Application/config/test trees match
merged develop 8865741 and F1-06 1192f19, so the file:line evidence still applies.
The F1-06 coverage JSON and committed closure table were checked: engine 2,523/2,858,
preflight 140/141, missing only line 505. Coverage was not remeasured for this prose update.

For every implementation PR, run from root with the local virtual environment:

```powershell
$env:TMP = "$PWD\.tmp"; $env:TEMP = "$PWD\.tmp"
New-Item -ItemType Directory -Force .tmp | Out-Null
python -m compileall -q app engine packaging
python -m unittest discover -s tests -p "test*.py" -v
python -m pytest -q
```

Only the exact full-runner commands may be escalated under NPS-019, with explicit
approval; all other commands stay sandboxed. Preserve F1-06's integrated test IDs
and report actual run/passed/failed/errors/skipped plus each new case, not an invented
fixed total. Use the Phase 1 approved coverage command
`python -m pytest --cov=engine --cov-report=term-missing -q` only with its explicit
coverage approval; export coverage JSON inside the sandbox. Report engine total and
weekly_preflight.py against the integrated baseline, explaining any regression.
Run available ruff/format checks on changed Python and mypy in its existing scope;
missing tools are a reported prerequisite, not permission to install dependencies.

Golden workflow for each behavior-changing PR:

- Generate pending candidates into ignored .codex-log/snapshot-candidates/, compare
  full semantic diffs against that PR's immediately preceding approved baseline,
  and review only the exact scenario/file lists in section 5. All remaining files
  must be byte-identical. New focused unit fixtures do not imply new golden scenarios.
- Retain Phase 1 canonicalization, independent-root repeatability, business-date,
  decision and link mutation failures, and runtime-token equivalence controls. The
  blank-line email_parser.py scratch control must still leave projections/provenance
  passing; no traceback locations or asserted source hashes may be reintroduced.
- provenance.json changes only affected candidate hashes and behavior-input hashes
  (config/*.json and tests/fixtures metadata). Historical source_sha256 is information,
  not an asserted freeze on app/engine/packaging; do not refresh it to disguise churn.
  Preserve all unaffected hashes and fixture .eml bytes. Under approved D1 A the candidate
  count becomes 132 (141 minus nine removed weekly outputs). Later column,
  regex and message changes alter hashes, not file counts.
- Append a pending issue-specific addendum to APPROVAL.md: selected product decision,
  old/new hashes and source/output counts, exact changed/deleted files and reason,
  preserved remaining known defects, architect review reference and product-owner
  PR comment/date/signature. Preserve the historical Phase 1 approval. Architect
  reviews the full diff; Mateo signs the addendum on that PR before baseline acceptance
  and merge. A candidate-generating commit is not approval; never auto-update in tests.
- Before each commit verify changed paths, no real data, and the issue's permitted
  application/config scope. Phase 1's source freeze is historical, not a prohibition
  on the specifically approved Phase 2 fixes. No unrelated refactors.

## 7. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Baseline evidence becomes stale | Low after PR #9 merge | Incorrect closure/coverage claim | Recheck source/test identity and integrated results against develop 8865741; retain dated F1-06 coverage evidence |
| Partial data acted on as complete | High today | Missing-country worklist | D1 failure status plus publication/recovery contract, UI and packaged checks |
| Retry overwrites evidence or duplicates work | Medium | Data loss/duplicate NPS | Archive FAILED attempt only; full fresh input set; completed-week guard; no external actions during comparison |
| Invitation display becomes a new eligibility rule | Medium | Unapproved business change | D2 visibility only; assert all classifications unchanged |
| Golden update hides unrelated changes | Medium | Regression accepted | Exact per-PR allowlist, byte checks, full diff and signed addendum |
| Dead-code removal affects a repository consumer | Low; owner confirmed no manual use | Lost tool or import | Follow exact D3 delete/move/retain list; check imports and preview smoke behavior |
| Operational config differs | Unknown | Untested production behavior | Owner compares effective config, minimal migration, backup; NPS-014 not silently fixed |
| Packaging cleanup removes executables | Known tool behavior | Breach/data loss | Fresh build checkout, absent prior artifacts; human handles occupied/locked paths |
| Cell projections miss UI/Excel/clipboard problems | Medium | Operational defect | Windows packaged TEST and manual clipboard/layout checks |

## 8. Rollback

Before merge, revert unapproved issue commits on their branch without rewriting published
history. After merge, use a reviewed revert PR into develop with the corresponding
approved baseline restoration; never accept a mismatched snapshot to make tests green.

For production failure, Mateo closes the app and restores the preserved 1.0.2 application
artifact and pre-promotion operational config (including the old POD policy if reproducing
the certified 1.0.2 behavior). Preserve new input/output/log/runtime evidence and reconcile
any externally created NPS before retrying; do not blindly roll operational state backwards
or process the same week again. Record reason, artifact/config hashes and affected week
locally; reopen release approval before another promotion. Agent never touches that install.

## 9. Progress

- [x] Read required standards, Phase 1 plan and current code/snapshot evidence.
- [x] Draft issue options, test-first work packages and exact golden diff expectations.
- [x] Record Phase 2 certification, off-Monday constraint, NPS-021 and FEAT-001 in roadmap.
- [x] Record D1 A, D2 export-only Option C and D3 exact disposition; Mateo Hernández, 2026-10-29.
- [x] Merge origin/develop 8865741 (F1-06 via PR #9); verify evidence, both runners 169/169 and unchanged application/config/snapshot trees.
- [ ] Architect review of the revised plan.
- [ ] Issue PRs, signed baseline updates and UI contract test merged.
- [ ] Release certification, approved release PR/tag and manual production promotion.

## 10. Decision log

| Date | Decision | Reason | Decided by |
|---|---|---|---|
| 2026-10-29 | F2-01 is plan only; no implementation, build, PR or promotion now | Explicit task boundary | Product owner |
| 2026-10-29 | Exclude standalone POD and PODs; embedded words do not match | Approved NPS-005 policy | Mateo Hernández |
| 2026-10-29 | Any selected/execution day; reference is same-week Monday; Tuesday–following-Monday window | Off-Monday product requirement; preserve during NPS-007 unification | Product owner |
| 2026-10-29 | 1.0.3 certification/promotion belongs to Phase 2; Phase 4 certifies 1.1.0 | Release boundary | Product owner |
| 2026-10-29 | D1 = A: withhold weekly outputs if any source fails; approve owner-assisted failed-attempt archive/reset and full-input restart described in 5.1 | No failed source may be reported as success; preserve failure evidence | Mateo Hernández |
| 2026-10-29 | D2 = C: two explicit invitation columns in worklist JSON/CSV, regional CSV and Excel Worklist/Revision Manual only; all Slack/slack_ready/copy paths unchanged for this issue | Surface evidence in exports without changing Slack or deciding NPS-016 | Mateo Hernández |
| 2026-10-29 | D3: delete four named legacy processing scripts and legacy weekly_run_view.py; move manual-review view/preview; keep retention and inspection scripts (5.6) | Owner confirmed no manual use of the four processing scripts | Mateo Hernández |
| 2026-10-29 | Merge origin/develop including F1-06 via PR #9; preserve Phase 1 DONE and F2-01 roadmap additions, without rebase or force-push | Establish 169-test integrated baseline and recorded preflight coverage | Mateo Hernández |
| Pending release | Sign baseline addenda on issue PRs and certify/promote tagged 1.0.3 | Separate implementation, snapshot acceptance and production approval | Architect and Mateo Hernández |
