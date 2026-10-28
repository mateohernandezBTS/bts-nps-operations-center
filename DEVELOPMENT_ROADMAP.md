# Development Roadmap — 1.0.3 and 1.1.0

Baseline: `v1.0.2` (certified, in production). Owner: Mateo Hernández.
Roles: product owner = Mateo; architect/reviewer = Claude; implementer = Codex.

## Phases

| Phase | Goal | Exit criteria |
|---|---|---|
| 0. Foundations | Standards, AGENTS.md, branching, dev environment outside OneDrive, tooling | Codex loads the rules, runs the suite in a clean clone, cannot touch `main` |
| 1. Safety net | Synthetic fixtures, golden-master tests of the full pipeline, real test cases | Suite runs green in a clean clone and covers parse -> outputs end to end |
| 2. Release 1.0.3 | Fix NPS-001, NPS-002, NPS-003; remove dead code (NPS-011) | Each fix has a failing-then-passing test; release DoD satisfied |
| 3. Release 1.1.0 | Behavior-preserving refactor (NPS-007, NPS-013, structure, typing) | Golden master identical after each module; release DoD satisfied |
| 4. Certification | Build, docs, parallel run against 1.0.2, promotion | Equivalent outputs on real weeks; explicit approval |

Business-rule changes (NPS-004, NPS-005, NPS-006, NPS-015, NPS-016) are excluded from
1.0.3 and 1.1.0 until the product owner approves them; they will be a separate release.

## Known-issue register

Status: OPEN, DECISION (needs business approval), PLANNED (assigned to a phase), DONE.

| ID | Severity | Status | Phase | Summary | Evidence |
|---|---|---|---|---|---|
| NPS-001 | Critical | PLANNED | 2 | A failed source yields `COMPLETED_WITH_REVIEW`, reported as success with empty issues; outputs omit that country silently. `COMPLETED_WITH_REVIEW` currently means "a source failed", not "manual review exists". | `engine/weekly_orchestrator.py` (`determine_final_weekly_status`), `engine/application_controller.py` (`run_weekly_process`) |
| NPS-002 | High | PLANNED | 2 | `survey_invitation` and `survey_invitation_link` are parsed but dropped from worklist, Excel and HTML, hiding possible duplicates. Surface only; no rule change. | `engine/stages/worklist.py` (`create_worklist_record`), `engine/weekly_excel.py` |
| NPS-003 | Medium | PLANNED | 2 | "Copy for Slack" copies the Mariano/Maider warning row because it is inside the client `<table>`. | `engine/slack_canvas_renderer.py` (`render_client_table`) |
| NPS-004 | Medium | DECISION | — | MERCADO_LIBRE rule matches `meli` as substring (e.g. "Amelia", "Melissa"). | `config/business_rules.json` |
| NPS-005 | Low | DECISION | — | POD regex `\bpod\b` does not match plural "PODs". | `config/business_rules.json` |
| NPS-006 | Medium | DECISION | — | Empty Ignore Reporting becomes False (eligible); letter `x` becomes True while `✕` is False. | `engine/stages/normalize.py` (`TRUE_VALUES`, `FALSE_VALUES`) |
| NPS-007 | Medium | PLANNED | 3 | Weekly window computed in four places; changing `weekly_schedule.json` breaks preflight. | `engine/weekly_preflight.py`, `engine/weekly_run.py`, `engine/stages/worklist.py`, `app/views/weekly_run/configuration_card.py` |
| NPS-008 | High | PLANNED | 1 | Several `tests/test_*.py` are print scripts without TestCase; the engine pipeline is not in the automated suite. | `tests/test_weekly_orchestrator.py`, `test_source_inventory.py`, `test_six_reports_manifest.py`, `test_selam_aggregator.py`, `test_selam_output.py`, `test_inventory_manifest_integration.py` |
| NPS-009 | High | PLANNED | 1 | Tests depend on real `.eml` files that are git-ignored; in a clean clone 6 tests error (Codex cloud onboarding, 2026-10-28: 62 passed, 6 errors, 1 failure). | `tests/test_processing_error_lifecycle.py`, `.gitignore` |
| NPS-010 | High | DONE (Phase 0) | 0 | `AGENTS.md` missing from repository. | repository root |
| NPS-011 | Low | PLANNED | 2 | Dead code: legacy `app/views/weekly_run_view.py`; unregistered `app/views/manual_review/`; legacy `tests/scripts/*`; `selam_slack_ready.md` output superseded by HTML. Preview files to be moved, not deleted, if still useful. | `app/main_window.py` registers 5 views only |
| NPS-012 | Low | PLANNED | 2 | Documentation drift: README says 64/64, VERSION 69/69; Power Automate integration listed as future; WEEKLY_OPERATION says 1.0.0 and mentions a Manual Review screen. | `documentation/*` |
| NPS-013 | Low | PLANNED | 3 | Hardcoded `EXPECTED_SOURCE_COUNT = 3` and country order contradict N-source extensibility. | `app/controllers/ui_controller.py`, `engine/slack_canvas_renderer.py` |
| NPS-014 | Low | OPEN | — | Retention never executes; operational config is a copy that can drift from the repo. | `config/system_config.json`, release layout |
| NPS-015 | Medium | DECISION | — | Coaching exclusion narrower than business rule (generic "coaching sessions", 1:1 meetings). | `config/business_rules.json` |
| NPS-016 | High | DECISION | — | Business rule for an existing Survey Invitation (duplicate prevention) undefined. | operational finding 2026-10-19 |
| NPS-017 | Low | OPEN | 3 | Import-time path constants (e.g. `PRODUCTION_INPUT`) ignore later environment changes; hinders dependency injection. | `engine/weekly_preflight.py` and others |
| NPS-018 | Medium | PLANNED | 1 | Test suite is platform-dependent: one path assertion fails on Linux (Codex cloud). Tests must pass on Linux and Windows. | Codex cloud onboarding report, 2026-10-28 |
