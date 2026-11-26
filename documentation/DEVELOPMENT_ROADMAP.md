# Development Roadmap — 1.0.3 and 1.1.0

Baseline: `v1.0.2` (certified, in production). Owner: Mateo Hernández.
Roles: product owner = Mateo; architect/reviewer = Claude; implementer = Codex.

## Phases

| Phase | Goal | Exit criteria |
|---|---|---|
| 0. Foundations | Standards, AGENTS.md, branching, dev environment outside OneDrive, tooling | Codex loads the rules, runs the suite in a clean clone, cannot touch `main` |
| 1. Safety net — DONE | Synthetic fixtures, golden-master tests of the full pipeline, real test cases | Suite runs green in a clean clone and covers parse -> outputs end to end |
| 2. Release 1.0.3 | Fix NPS-001, NPS-002, NPS-003, NPS-005, NPS-020; remove verified dead code (NPS-011); reconcile docs (NPS-012); certify and promote 1.0.3 | Test-first fixes; signed golden-master updates; Windows build, packaged TEST E2E, real parallel run against 1.0.2, owner approval and manual production promotion; release DoD satisfied |
| 3. Release 1.1.0 | Behavior-preserving refactor (NPS-007, NPS-013, structure, typing) | Golden master identical after each module; release DoD satisfied |
| 4. Certification 1.1.0 | Build, docs, parallel run against certified 1.0.3, promotion of 1.1.0 | Equivalent outputs on real weeks except separately approved changes; explicit approval and release DoD |
| V2-1. Claude-native Upcoming — IN PROGRESS | Read-only Upcoming from Salesforce as a Claude skill (`nps_v2/`, `skill/`), replacing e-mail parsing; see `V2_CLAUDE_NATIVE_ARCHITECTURE.md` and `plans/V2-1_upcoming_read_only.md` | Parallel run against v1.0.2 with 0 unexplained differences on 2–3 Mondays (`V2_PARALLEL_RUN.md`); PO sign-off |

Phase 1 status (2026-10-29): DONE. Golden master approved in PR #8; F1-06 adds
18 preflight methods for 169/169 passing on both Windows runners. All 141 candidate
hashes remain identical. Final engine line coverage: 2,523/2,858 (88.2785%);
weekly_preflight.py: 140/141 (99.2908%), exceeding the 85% target.
No unreachable/defensive preflight behavior lines were identified. The only uncovered
statement is weekly_preflight.py:505 (__main__ delegates to the tested public main()).
NPS-007 and NPS-017 remain characterized, not fixed. NPS-019 option A remains in use;
optional option C is separately deferred as F1-07. See the Phase 1 plan for full evidence.

Product-owner decision 2026-11-25: desktop 1.0.3 is not built or released; the NPS-001 fix
will still be merged into the engine (F2-02b) because V2 reuses it; new investment goes to the Claude-native
V2 (phases above). v1.0.2 keeps running on Mondays until V2-1 is signed off.

Business-rule changes (NPS-004, NPS-006, NPS-015, NPS-016) are excluded from
1.0.3 and 1.1.0 until the product owner approves them; they will be a separate release.

Release 1.0.3 execution plan: [F2-01](plans/F2_release_1_0_3.md). Plan only;
Mateo Hernández decided D1–D3 on 2026-10-29: withhold weekly outputs on any source
failure with owner-assisted failed-attempt recovery; show invitation text/link in
JSON/CSV/Excel exports only (all Slack paths unchanged for NPS-002); follow the exact
legacy-code delete/move/retain list in the plan. F1-06 is merged into develop via
PR #9 (`8865741`); its 169-test Phase 1 closure is now the integrated baseline.

Off-Monday operation constraint for NPS-007 (decided 2026-10-29 by the product owner):
the operator may execute on any day. The selected date maps to the Monday of its own
week (the preceding Monday, or the date itself when Monday); the inclusive weekly
window is Tuesday through the following Monday, anchored to that reference Monday.
The UI already converts this at `app/views/weekly_run/configuration_card.py:402–416`
and emits the reference date through `app/views/weekly_run/weekly_run_view.py:146–155`.
1.0.3 pins that contract with tests; 1.1.0 NPS-007 unification must preserve it rather
than require that the application itself be run on a Monday.

## Known-issue register

Status: OPEN, DECISION (needs business approval), PLANNED (assigned to a phase), DONE.

| ID | Severity | Status | Phase | Summary | Evidence |
|---|---|---|---|---|---|
| NPS-001 | Critical | PLANNED | 2 | A failed source yields `COMPLETED_WITH_REVIEW`, reported as success with empty issues; outputs omit that country silently. `COMPLETED_WITH_REVIEW` currently means "a source failed", not "manual review exists". | CONFIRMED: `engine/weekly_orchestrator.py:141`, `engine/application_controller.py:472` and `:510`, `engine/selam_aggregator.py:302` |
| NPS-002 | High | PLANNED | 2 | `survey_invitation` and `survey_invitation_link` are parsed but dropped from worklist/CSV/Excel, hiding possible duplicates. D2 approved 2026-10-29 by Mateo Hernández: two explicit columns in worklist JSON/CSV, regional CSV and Excel Worklist/Revision Manual only; all Slack paths unchanged for this issue. Visibility only; no rule change. | CONFIRMED: parsed at `engine/stages/email_parser.py:508`; omitted by `engine/stages/worklist.py:368`, `engine/weekly_excel.py:1403`; export/Slack boundary specified in F2-01 section 5.2 |
| NPS-003 | Medium | PLANNED | 2 | "Copy for Slack" copies the Mariano/Maider warning row because it is inside the client `<table>`. | CONFIRMED: warning inserted at `engine/slack_canvas_renderer.py:516`; whole-table copying at `engine/slack_canvas_renderer.py:1090` |
| NPS-004 | Medium | DECISION | — | MERCADO_LIBRE rule matches `meli` as substring (e.g. "Amelia", "Melissa"). | CONFIRMED: `config/business_rules.json:22`, substring matcher at `engine/stages/business_rules.py:76` |
| NPS-005 | Low | PLANNED | 2 | POD regex `\bpod\b` does not match plural "PODs". Product-owner decision 2026-10-29: exclude both singular "POD" and plural "PODs" (e.g. pattern `\bpods?\b`); embedded words such as "Empoderamiento" must remain non-matching. Decided by: Mateo Hernández. | CONFIRMED: `config/business_rules.json:36`, regex matcher at `engine/stages/business_rules.py:88` |
| NPS-006 | Medium | DECISION | — | Empty Ignore Reporting becomes False (eligible); letter `x` becomes True while `✕` is False. | CONFIRMED: `engine/stages/normalize.py:4` and `:14`; False passes this eligibility condition at `engine/stages/business_rules.py:176`, subject to other rules |
| NPS-007 | Medium | PLANNED | 3 | Weekly window computed in four places; changing `weekly_schedule.json` breaks preflight. | CONFIRMED: `engine/weekly_preflight.py:75`, `engine/weekly_run.py:90`, `engine/stages/worklist.py:65`, `app/views/weekly_run/configuration_card.py:402`; only weekly-run creation reads schedule offsets at `engine/weekly_run.py:147` |
| NPS-008 | High | DONE (Phase 1) | 1 | Several `tests/test_*.py` are print scripts without TestCase; the engine pipeline is not in the automated suite. Only 11 of 29 `test_*.py` files under tests/ contribute test cases. `tests/test_pod_rule.py` cannot fail the runner for a wrong match: its failure branch only prints. | CONFIRMED: manual main routines at `tests/test_weekly_orchestrator.py:62`, `tests/test_source_inventory.py:17`, `tests/test_six_reports_manifest.py:30`, `tests/test_selam_aggregator.py:21`, `tests/test_selam_output.py:23`, `tests/test_inventory_manifest_integration.py:31`; print-only result at `tests/test_pod_rule.py:34` and `:40`; F0-01/F0-02 discovery inventory below |
| NPS-009 | High | DONE (Phase 1) | 1 | Tests depend on previously processed `.eml` files that are git-ignored; six tests error in both clean-clone baselines. The six affected tests and their required fixture sets are listed below. | CONFIRMED: fixture lookup at `tests/test_backend_blocking_scenarios.py:31` and `tests/test_processing_error_lifecycle.py:26`; ignore rules at `.gitignore:45` and `:51`; Windows: 69 run / 63 passed / 0 failures / 6 errors / 0 skipped |
| NPS-010 | High | DONE (Phase 0) | 0 | `AGENTS.md` missing from repository. | Historical defect resolved: tracked root `AGENTS.md:1` exists |
| NPS-011 | Low | PLANNED | 2 | D3 approved 2026-10-29 by Mateo Hernández: delete the legacy weekly_run_view.py and four named processing scripts; move the manual-review view/preview; retain retention and inspection scripts. Exact paths in F2-01 section 5.6. | `app/main_window.py:282` registers only five views; legacy classes at `app/views/weekly_run_view.py:31` and `app/views/manual_review/manual_review_view.py:25`. Owner confirmed no manual use of the four processing scripts; repository consumers remain an implementation check |
| NPS-012 | Low | PLANNED | 2 | Documentation drift: README says 64/64, VERSION 69/69; Power Automate integration listed as future; WEEKLY_OPERATION says 1.0.0 and mentions a Manual Review screen. | CONFIRMED: `documentation/README.md:69` and `:78`, `documentation/VERSION.md:37`, `documentation/WEEKLY_OPERATION.md:5` and `:315` |
| NPS-013 | Low | PLANNED | 3 | Hardcoded `EXPECTED_SOURCE_COUNT = 3` and country order contradict N-source extensibility. | CONFIRMED: `app/controllers/ui_controller.py:197`, `engine/slack_canvas_renderer.py:27` |
| NPS-014 | Low | OPEN | — | Retention never executes; operational config is a copy that can drift from the repo. | PARTIALLY: retention enabled in dry-run mode at `config/system_config.json:16`; no call found in app/engine; standalone routine at `tests/scripts/cleanup_retention.py:114`; config copy at `packaging/build_release.py:74`. Operational drift was not inspected |
| NPS-015 | Medium | DECISION | — | Coaching exclusion narrower than business rule (generic "coaching sessions", 1:1 meetings). | PARTIALLY: finite phrases at `config/business_rules.json:50` omit those generic forms; intended broader business policy not independently established |
| NPS-016 | High | DECISION | — | Business rule for an existing Survey Invitation (duplicate prevention) undefined. | PARTIALLY: parsed at `engine/stages/email_parser.py:508`, with no invitation-based decision in `engine/stages/business_rules.py:102`; operational finding 2026-10-19 not independently available |
| NPS-017 | Low | OPEN | 3 | Import-time path constants (e.g. `PRODUCTION_INPUT`) ignore later environment changes; hinders dependency injection. | CONFIRMED: resolution at `engine/weekly_preflight.py:21`, reuse at `:104`, environment lookup at `engine/paths.py:44` |
| NPS-018 | Medium | DONE | 1 | Full relative output path assertion uses native Path construction. Linux portability is an accepted, unverified risk. | F1-03 Windows: 81/81 passed on both runners; code review confirms `str(Path("output") / "report.xlsx")` preserves the exact location. F1-04 task accepts Windows evidence without Linux execution. |
| NPS-019 | Medium | PLANNED | 1 | Python tempfile directory ACLs are incompatible with the Windows restricted-token sandbox, even when TMP and TEMP point inside the repository. | CONFIRMED: F0-02 sandbox probes below; ordinary mkdir succeeds, mkdtemp child creation fails with WinError 5; installed Python 3.14.6 `Lib/tempfile.py:381` uses `os.mkdir(file, 0o700)` |
| NPS-020 | Low | PLANNED | 2 | The orphan 13-cell row error is self-contradictory ("no reconocida: 13. Se esperaban 14 o 13"); it should say the row has no preceding Billing Office to inherit. | CONFIRMED: `tests/snapshots/phase1/v1/malformed_Brazil_orphan_group/error_details.json` |
| NPS-021 | Low | OPEN | — | With `--json`, preflight failures print non-JSON text rather than a JSON error response. Recorded only; not in 1.0.3 scope. | CONFIRMED: `engine/weekly_preflight.py:480–485`; `tests/test_weekly_preflight.py`, `test_cli_preflight_failure_uses_exit_one_and_actionable_message`, merged in PR #9 (`8865741`), asserts human text and exit 1 for `--json` failures |
| NPS-022 | Low | OPEN | V2 | Golden-master provenance hashes raw file bytes, so `test_provenance` fails on Linux checkouts (LF) while every behavior snapshot passes; the Claude runtime is Linux. Proposed: normalise line endings before hashing and re-sign provenance (PO approval). | CONFIRMED: `tests/test_pipeline_golden_master.py::test_provenance` fails on Linux, passes on Windows |
| NPS-023 | Low | OPEN | V2 | The special-case facilitator names are hard-coded in the desktop Slack renderer (`SPECIAL_EMAIL_NAMES`); V2 reads them from a watch-list outside the repository. Proposed: remove them from the code when the desktop app is retired. | CONFIRMED: `engine/slack_canvas_renderer.py`, `SPECIAL_EMAIL_NAMES` |

## Feature backlog

| ID | Candidate release | Status | Requirement |
|---|---|---|---|
| FEAT-001 | V2-1 | Superseded by V2-1 flexible selection (2026-11-26) | Filter results of an already processed weekly run by a day range inside its weekly window, consistently in the view, Excel and Copy for Slack, so the operator can work day by day. Processing remains once per week; changing the filter never re-processes reports. Optional second level: track which NPS were already created and show only pending ones, related to the V2 lifecycle in the EXPANSION vision; requires separate design/approval. |
| FEAT-002 | V2-1 | Ready (2026-11-26); scheduled task pending install | Run the Upcoming automatically every Monday (standard week of today in Buenos Aires, read-only). Wider or filtered selections stay manual. Architecture §6.5. |
| FEAT-003 | V2-4 | Design note (2026-11-26) | Weekly scheduled search for available results; when found, generate the report with `survey-results-reports` and replace the card's `Results: NO` in the `#latam-nps` canvas, with preview and approval first. Architecture §6.6; open D-V2-9, D-V2-10; depends on V2-3 and D-V2-2. |

## F0-01 verification evidence

Verified on 2026-10-28 against develop at `7931ec0`. Application and test code were
unchanged. The Windows run used Python 3.14.6, PySide6 6.11.1, openpyxl 3.1.5 and
beautifulsoup4 4.15.0. Compilation passed. The completed Windows unittest run had
69 tests: 63 passed, no failures, six errors and no skips. The Linux reference had
69 tests: 62 passed, one failure, six errors and no skips. The only outcome difference
was the Windows path assertion in NPS-018. No missing fixtures were created.

### NPS-008 discovery inventory

F0-02 rechecked the recursive inventory: 29 files named `test_*.py` under `tests/`,
of which these 11 define the TestCase classes contributing the 69 unittest cases:

- `tests/test_application_controller_failure.py`
- `tests/test_backend_blocking_scenarios.py`
- `tests/test_controller_session_integration.py`
- `tests/test_operational_logging.py`
- `tests/test_packaging_release.py`
- `tests/test_paths.py`
- `tests/test_preflight_session_weekly_run_id.py`
- `tests/test_processing_error_lifecycle.py`
- `tests/test_prod_safeguards.py`
- `tests/test_session_isolation.py`
- `tests/test_session_manager.py`

### NPS-009 missing fixture sets

All six errors occur before the intended scenario can be exercised. Both fixture
helpers search `tests/runtime/weekly_pipeline/processed/*.eml`. Country-specific
lookups match the country name in the filename. The required sets below come from
the test setup; the first missing lookup stops execution.

| Test | Required existing fixture set | First missing lookup | Evidence |
|---|---|---|---|
| `test_duplicate_source_is_blocked` | Argentina, Brazil, Mexico; Mexico copied twice | Argentina | `tests/test_backend_blocking_scenarios.py:298` |
| `test_existing_weekly_run_is_blocked` | Argentina, Brazil, Mexico | Argentina | `tests/test_backend_blocking_scenarios.py:346` |
| `test_missing_argentina_is_blocked` | Brazil, Mexico | Brazil | `tests/test_backend_blocking_scenarios.py:181` |
| `test_missing_brazil_is_blocked` | Argentina, Mexico | Argentina | `tests/test_backend_blocking_scenarios.py:220` |
| `test_missing_mexico_is_blocked` | Argentina, Brazil | Argentina | `tests/test_backend_blocking_scenarios.py:259` |
| `test_failed_report_is_moved_to_error` | Any valid previously processed Upcoming .eml | Any valid .eml | `tests/test_processing_error_lifecycle.py:62` |

### NPS-011 retained output

`selam_slack_ready.md` is excluded from the dead-code candidates: it is still
generated at `engine/selam_output.py:665` and consumed by the load at
`engine/weekly_excel.py:1342`. F0-02 does not change that behavior.

## F0-02 NPS-019 sandbox diagnosis

On 2026-10-28, both probes ran from the repository root inside the Windows sandbox
using `.venv/Scripts/python` (Python 3.14.6), without escalation:

```text
python -c "import os,tempfile; os.makedirs('.tmp/plain/x', exist_ok=True); print('plain OK')"
plain OK
exit: 0

python -c "import os,tempfile; d=tempfile.mkdtemp(dir='.tmp'); print(d); os.makedirs(os.path.join(d,'x')); print('mkdtemp OK')"
<repository>\.tmp\tmpjthvgs3y (absolute path)
PermissionError: [WinError 5] Access is denied: '<repository>\\.tmp\\tmpjthvgs3y\\x'
exit: 1; "mkdtemp OK" was not reached

icacls .tmp\tmpjthvgs3y
.tmp\tmpjthvgs3y: Access is denied.
Successfully processed 0 files; Failed processing 1 files
```

For comparison, `icacls .tmp` and `icacls .tmp/plain/x` both succeeded. Both listed
two inherited sandbox SID entries with `(I)(OI)(CI)(M)` and inherited SYSTEM,
Administrators and current-user entries with `(I)(OI)(CI)(F)`. The new mkdtemp
directory's ACL could not be read from the sandbox; no ACL was changed or bypassed.

Inspection of the installed `Lib/tempfile.py:381` confirmed that `mkdtemp` invokes
`_os.mkdir(file, 0o700)`. The [Python 3.14 os.mkdir documentation](https://docs.python.org/3.14/library/os.html#os.mkdir)
states that Windows gives mode 0o700 special access control for the current user
and administrators (introduced in Python 3.13). Together, the control probe, denied
mkdtemp access and installed source confirm the tempfile ACL incompatibility in
this Python 3.14 environment; they do not establish the full unreadable DACL.

Redirecting TMP/TEMP alone therefore does not resolve this issue. The approved
exception in AGENTS.md is limited to the exact unittest and pytest commands with
explicit human approval; application behavior, ACLs and test code remain unchanged.
