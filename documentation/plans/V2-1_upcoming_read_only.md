# Execution Plan — V2-1 Upcoming + Slack table (read-only)

Status: **PLAN ONLY — awaiting product-owner approval.** Implementation is not authorized
by this document. Prepared 2026-11-25. Product owner: PE, BTS SELAM. Architect: Claude.

## 1. Purpose

Produce the weekly NPS worklist **directly from Salesforce** inside a Claude (Cowork)
session, with flexible selection, per-kind survey state and the Slack table with QR and
links filled in for surveys that already exist. Nothing is written anywhere. This is the
first increment of `documentation/V2_CLAUDE_NATIVE_ARCHITECTURE.md` and the basis for the
parallel run against desktop v1.0.2.

## 2. Context

- Architecture: `documentation/V2_CLAUDE_NATIVE_ARCHITECTURE.md` (§4 components, §5 data
  contract, §6.1 flow, §10 testing).
- Related ids: NPS-003 (warning row in Slack copy), NPS-005 (PODs), NPS-007 (weekly window
  in four places), NPS-013 (hardcoded countries), NPS-016 (existing survey), NPS-022
  (proposed: CRLF/LF provenance hashes).
- Reused certified code (unchanged):
  - `engine/stages/normalize.py` — `normalize_records(records)`; expects raw string values,
    dates `M/D/YYYY`, booleans `✔/✕`, status text.
  - `engine/stages/business_rules.py` — `apply_business_rules(records)` →
    `eligible / excluded / review`, config `config/business_rules.json`.
  - `engine/stages/worklist.py` — `generate_worklist(eligible, config, reference_monday)`;
    filters by weekly window unless `weekly_window.enabled` is `false` in the config passed
    in; extracts the project Id from `project_url`; builds `Link for Results`.
  - `engine/slack_canvas_renderer.py` — `generate_slack_canvas_html(directory)` reads
    `selam_worklist.csv` (+ optional `selam_weekly_summary.json`) from a directory.
- Current behavior being replaced: e-mail → `email_parser` → stages, one report per
  country, fixed weekly window, survey links always empty.
- Runtime facts (verified 2026-11-25, read-only): connector `salesforce_query` returns
  `{totalSize, done, records[]}` with an `attributes` object per record; dates as
  `YYYY-MM-DD`, datetimes as `YYYY-MM-DDThh:mm:ss.000+0000`, booleans as JSON booleans.
  The Cowork runtime has Python 3.13; the Windows clone targets 3.14.

## 3. Scope

In scope:
- New package `nps_v2/` (domain, selection, registry, salesforce query builders and
  readers, legacy adapter, pipeline, survey state, outputs, CLI) — architecture §4.
- New configuration `config/v2/countries.json` (country registry, survey families) and
  `config/v2/report_scope.json` (report-equivalent scope filter).
- New tests under `tests/v2/` with **synthetic** connector-shaped fixtures.
- Skill packaging: `skill/SKILL.md` + `scripts/build_skill.py` producing a self-contained
  skill folder (no PySide6, bs4, openpyxl or Windows paths).
- Operator runbook for the parallel run: `documentation/V2_PARALLEL_RUN.md`.

Out of scope (explicitly):
- Any write to Salesforce, Slack, Outlook or Box (V2-2, V2-3).
- Changes to `engine/`, `app/`, existing `config/*.json`, existing tests or the golden master.
- Business-rule changes: NPS-004, NPS-005, NPS-015 (tracked separately; see §10).
- Results, data quality, follow-up (V2-4, V2-5). Audit store (D-V2-2, needed for V2-2).
- Fixing NPS-003 in the reused HTML renderer (V2-3 publishes from its own table).

## 4. Constraints

- Behavior to preserve: all existing tests and the golden master unchanged; desktop v1.0.2
  untouched.
- AGENTS.md prohibitions especially relevant: no real data in the repo (fixtures, docs,
  snapshots); no new production dependency (stdlib only for `nps_v2`); no commits to
  `main`/`develop`.
- Python: code must run on 3.12–3.14 (no 3.14-only syntax).
- Determinism: the engine generates SOQL text and decides everything; Claude only runs the
  queries it prints and stores the raw JSON.
- Fail closed: an unreadable or unexpected connector response stops the run with a clear
  error; it never yields an empty "nothing pending" result.
- Business decisions this plan depends on: `#latam-nps` scope AR / BR+Nexo / MX (decided
  2026-11-25); **D-V2-7** survey-kind detection by family (decided 2026-11-25, see §10).

## 5. Steps

Each step is independently verifiable and committed separately on a feature branch from
`develop` (`feature/v2-1-upcoming`). Delivery: Claude prepares and tests each step on
Linux and hands over a patch series; Codex applies, runs the Windows tests and commits.

| # | Step | Files | Validation | Commit message |
|---|---|---|---|---|
| 1 | Scaffolding: package skeleton, `tests/v2/` with `conftest.py`, pytest path so `pytest tests/v2` runs alone | `nps_v2/__init__.py`, `tests/v2/` | `pytest tests/v2` green (smoke test) | `chore(v2): scaffold nps_v2 package and tests` |
| 2 | Domain types (frozen dataclasses: `Selection`, `ProjectSnapshot`, `SurveySetSnapshot`, `SurveyKind`, `SurveyState`) and country registry loader with schema validation | `nps_v2/domain.py`, `nps_v2/registry.py`, `config/v2/countries.json` | unit tests: load, unknown country, duplicate `Billing_Country__c`, missing survey Id fail closed | `feat(v2): add domain types and country registry` |
| 3 | Selection: preset standard week (reference Monday → Tue..next Mon), ±days, single day, range, filters (project, client, country, facilitator, sub-type) | `nps_v2/selection.py` | table tests incl. any weekday → its Monday, month/year boundaries, negative ranges rejected | `feat(v2): add flexible selection` |
| 4 | SOQL builders: projects in range × registry values; survey sets by project Ids (chunked); string escaping; explicit field lists | `nps_v2/salesforce/queries.py` | golden-text tests of generated SOQL; injection/escaping tests; chunk boundaries | `feat(v2): generate SOQL for projects and survey sets` |
| 5 | Readers: connector JSON → snapshots; validate `done=true`, required fields, types | `nps_v2/salesforce/readers.py`, `tests/v2/fixtures/*.json` | synthetic fixtures; truncated (`done=false`) and malformed responses fail closed | `feat(v2): read connector snapshots` |
| 6 | Legacy adapter + pipeline: snapshot → raw record dialect → report-scope filter → `normalize_records` → `apply_business_rules` → `generate_worklist` (window disabled; selection already bounded the dates) | `nps_v2/adapters.py`, `nps_v2/pipeline.py`, `config/v2/report_scope.json` | **adapter equivalence test**: synthetic Salesforce JSON and the equivalent synthetic `.eml` fixture produce identical worklist rows | `feat(v2): run certified stages from Salesforce snapshots` |
| 7 | Survey state per kind (D-V2-7): NPS present / facilitators present / other; classify eligible projects as `PENDING_BOTH`, `PENDING_NPS`, `PENDING_SP`, `COMPLETE`; fill QR and links from existing sets; flag projects with several sets of one kind | `nps_v2/surveys/state.py` | table tests for every combination incl. client-specific NPS and duplicate sets | `feat(v2): derive per-kind survey state` |
| 8 | Outputs: run folder (`selection.json`, raw snapshots, `worklist.json`, `excluded.json`, `review.json`, `out_of_scope.json`, `survey_state.json`), `preview.md`, Slack HTML through the reused renderer (writes `selam_worklist.csv` + summary), special-case flags from a runtime watch-list file **outside the repo** | `nps_v2/outputs/` | snapshot tests on synthetic data (`tests/snapshots/v2/`); warning never inside the data rows of `preview.md` | `feat(v2): write run folder, preview and Slack table` |
| 9 | CLI: `python -m nps_v2 select …` (prints SOQL + writes `selection.json`) and `python -m nps_v2 upcoming --run <dir>` | `nps_v2/__main__.py`, `nps_v2/cli.py` | end-to-end test on a synthetic run folder; exit codes | `feat(v2): add select and upcoming commands` |
| 10 | Skill packaging: `SKILL.md` (orchestration steps, what Claude may and may not do) + build script vendoring `nps_v2/`, `engine/paths.py`, needed `engine/stages`, renderer and configs | `skill/SKILL.md`, `scripts/build_skill.py` | build test: output contains only allowed files; imports succeed without PySide6/bs4/openpyxl | `build(v2): package the Upcoming skill` |
| 11 | Docs: parallel-run runbook, roadmap entries (V2-1, NPS-022, NPS-023 proposals) | `documentation/V2_PARALLEL_RUN.md`, `documentation/DEVELOPMENT_ROADMAP.md` | PO review | `docs(v2): parallel-run runbook and roadmap entries` |

## 6. Validation strategy

- Tests to add: everything under `tests/v2/` (unit, equivalence, snapshot, CLI, build).
  Target: ≥ 90 % line coverage of `nps_v2/`.
- Existing suite: must stay green on Windows; on Linux the known exceptions are the
  headless UI tests and `test_provenance` (NPS-022). V2 tests must pass on both.
- Golden-master impact: **none** (no change to `engine/`, `config/*.json` or fixtures).
- Product-owner checks (live, outside the repo):
  1. Monday parallel run ×2–3: V2 worklist vs desktop v1.0.2 worklist, every difference
     explained (time of extraction, report scope, survey state). Exit: 0 unexplained.
  2. One run with a non-standard selection (single day; facilitator search).
  3. Slack HTML pasted into a test canvas looks like today's.

## 7. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Adapter dialect drift (dates, booleans, URL) silently changes eligibility | Medium | High | equivalence test against `.eml` fixtures; adapter is the only translation point |
| Report-scope filter differs from the subscribed Salesforce reports (D-V2-1) | Medium | Medium | scope rows are listed, not hidden (`out_of_scope.json`); parallel run surfaces gaps |
| Custom NPS surveys misread as "pending" → future duplicates | Medium | High | detection by family (D-V2-7); "other survey" bucket shown in preview |
| Connector returns partial pages | Low | High | readers require `done=true`; queries bounded and chunked |
| Real data leaking into repo | Low | High | synthetic fixtures; watch-list file outside repo; run folders only in the session workspace |
| Runtime Python difference (3.13 vs 3.14) | Low | Low | CI-style check: tests run on both before each merge |

## 8. Rollback

Purely additive (`nps_v2/`, `config/v2/`, `tests/v2/`, `skill/`, `scripts/build_skill.py`,
docs). Revert the merge commit of `feature/v2-1-upcoming` on `develop`; nothing else
depends on it. No data is written during V2-1, so there is no data rollback.

## 9. Progress

- [x] Plan approved by PO (PR #12)
- [x] D-V2-7 decided (2026-11-25)
- [x] Steps 1–11 (step 11 adds `nps_v2 compare` for the parallel run)
- [ ] Parallel run #1 / #2 / #3
- [ ] PO sign-off

## 10. Decision log

| Date | Decision | Reason | Decided by |
|---|---|---|---|
| 2026-11-25 | `#latam-nps` scope = AR, BR (incl. Nexo), MX | Current operation | PO |
| 2026-11-25 | Audit store (D-V2-2) deferred to V2-2 | V2-1 writes nothing; run folders stay in the session workspace | Architect (proposal) |
| 2026-11-25 | Business-rule items NPS-004 / NPS-005 / NPS-015 not changed in V2-1 | Keep parity with v1.0.2 during the parallel run; apply afterwards as config changes with golden-master update | Architect (proposal) |
| 2026-11-26 | Special-case watch-list lives in the installed skill (`config/v2/watchlist.json`, git-ignored); the repository ships a synthetic template | Real names never in the repository | PO |
| 2026-11-26 | The Slack page has two layers: a BTS-styled preview (ACT & SURVEYS look) and a copy payload that never contains styles or notices. The QR is always an image, never a link, drawn in the browser (qrcodejs); "Copiar QR" copies a single QR image. `engine/` stays unchanged | External QR images did not load in the viewer | PO |
| 2026-11-26 | The copy payload is one card per session (title, date, facilitator, links, results and QR image) instead of a table: a Slack canvas table cannot hold images (tested by the PO: pasted QRs broke the table) | Send everything in one paste | PO |
| 2026-11-25 | D-V2-7: survey-kind detection by family (architecture §5.2). Any Survey Set with `SurveyNPS__c = true` counts as NPS; facilitator family is configuration | Client-specific NPS surveys are rare but exist; regional facilitator variants exist | PO |
