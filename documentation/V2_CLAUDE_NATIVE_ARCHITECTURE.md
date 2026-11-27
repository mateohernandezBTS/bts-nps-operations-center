# NPS Operations Center V2 — Claude-native architecture

Status: **DRAFT for product-owner review** · Date: 2026-11-25 · Owner: Product owner (PE, BTS SELAM)

This document defines the architecture and incremental plan that replace the desktop
application (v1.0.2) with a Claude-native solution (skill + Cowork + connectors). It is the
reference for every V2 increment plan. Real client, project or person data never appears here.

---

## 1. Goals and non-goals

### Goals

1. Read upcoming deliveries **directly from Salesforce** instead of Salesforce e-mail
   subscriptions → Power Automate → OneDrive → HTML parsing.
2. Flexible selection: standard week, ±days, single day or range, search by project,
   client, country, facilitator or session type.
3. Create NPS surveys (Survey Sets) from Claude with mandatory preview, approval and
   idempotency.
4. Publish the Slack table to `#latam-nps` with QR and links already filled in.
5. Later: results review, data quality for PRO, facilitator follow-up, alerts.

### Non-goals (for now)

- No further investment in the desktop application. v1.0.2 keeps running on Mondays
  **only** until V2 proves equivalence in a parallel run.
- No markets beyond Argentina, Brazil (incl. Nexo) and Mexico. `#latam-nps` serves only
  these three countries today (PO decision 2026-11-25). Adding one later must be a
  configuration change, not a code change.
- No autonomous writes. Every write is previewed and approved until the PO enables a
  higher automation level per capability.

## 2. Architectural principles

| # | Principle | Consequence |
|---|---|---|
| P1 | **The engine decides, Claude executes.** | Business rules, eligibility, survey choice, language and idempotency are deterministic, tested Python. Claude orchestrates connectors and never applies business criteria of its own. |
| P2 | **Salesforce is the source of truth for state.** | "Already created" is read from `Survey_Set__c`, not from local run folders. Any selection is therefore safe to re-run. |
| P3 | **Read first; writes are plans.** | The engine emits a write *plan* (data). Claude executes exactly that plan after approval, then the engine reconciles the result. |
| P4 | **Reuse the certified core.** | The existing stages (`normalize`, `business_rules`, `worklist`, Slack rendering) run unchanged behind an anti-corruption adapter. The golden master keeps guarding them. |
| P5 | **Configuration over code for markets.** | Countries, Salesforce values, surveys, languages and Slack destinations live in one country registry. |
| P6 | **No real data in the repository.** | Fixtures stay synthetic. Snapshots of real runs live only in the session workspace and the audit store (§8). |

## 3. Context: why the engine cannot call Salesforce itself

Inside Claude, Salesforce, Slack, Outlook and Box are reachable **only through connectors
invoked by Claude** (MCP tools), with the user's identity. Python scripts in the skill run in
a sandbox without those credentials. The design therefore splits responsibilities:

```text
             ┌──────────────── Claude (orchestrator, Cowork session) ────────────────┐
             │  runs SOQL / create / Slack calls through connectors, shows previews, │
             │  asks for approval, moves JSON files between steps                    │
             └───────▲───────────────────────────────┬───────────────────────────────┘
                     │ JSON in / JSON out (files)    │ connector calls (user identity)
             ┌───────┴──────────────┐        ┌───────▼────────────────────────────┐
             │ nps engine (Python)  │        │ Salesforce (BTS) · Slack · Outlook │
             │ deterministic, tested│        │ · Box                              │
             └──────────────────────┘        └────────────────────────────────────┘
```

The engine also **generates the SOQL text** it needs (from the selection and the country
registry), so queries are code, not model improvisation.

## 4. Logical components (ports and adapters)

```text
nps_v2/
  domain/          pure types: Selection, ProjectSnapshot, SurveyKind, SurveyState,
                   SurveySetCommand, WritePlan, ExecutionResult
  selection/       Selection → date range + filters (presets, ±days, day, range, search)
  registry/        CountryRegistry loaded from config/countries.json
  salesforce/      query builders (SOQL text) + snapshot readers (connector JSON → domain)
  adapters/        LegacyRecordAdapter: ProjectSnapshot → raw record dict of the
                   certified engine contract (see §5)
  pipeline/        runs certified stages: normalize → business_rules → worklist
  surveys/         SurveyPolicy (country → survey + language), PlanBuilder, Reconciler
  outputs/         Slack table (reuses renderer), preview markdown, special-cases package
  cli.py           thin commands used by the skill (§6)
engine/            existing certified stages — reused, not modified in increment 1
```

Key design choices:

- **Anti-corruption layer (`LegacyRecordAdapter`).** Converts Salesforce values to the
  dialect the certified stages expect (dates `M/D/YYYY`, booleans `✔/✕`, project URL from
  which `extract_salesforce_id` reads the Id, `billing_office` = `Billing_Country__c`).
  This keeps `engine/stages` untouched and the golden master meaningful. Refactoring the
  stages to typed models is a later, separate step.
- **Strategy for survey policy.** `SurveyPolicy` resolves, per country, which surveys a
  project needs and in which language. Adding a market = adding registry data.
- **Command objects for writes.** Each `SurveySetCommand` carries `project_id`,
  `survey_id`, `survey_kind` (NPS | FACILITATORS_SP), `language`, `survey_nps` flag and an
  `idempotency_key` = `project_id + survey_id`. A `WritePlan` is a list of commands plus a
  SHA-256 `plan_hash` over its canonical JSON. Approval is bound to that hash.
- **Reconciler.** After execution, the engine re-reads Salesforce state and classifies each
  command as `CREATED`, `SKIPPED_ALREADY_EXISTS`, `FAILED` or `UNVERIFIED`.

### 4.1 Country registry (`config/countries.json`, proposed)

| Country | `Billing_Country__c` values | NPS survey (Id) | Language | Slack destination |
|---|---|---|---|---|
| Argentina | `Argentina` | Survey NPS (`0Kd7V000000KymySAC`) | `es` | `#latam-nps` · Argentina section |
| Brazil | `Brazil`, `Nexo` | Survey NPS BR (`0KdPP0000000PT30AM`) | `pt-BR` | `#latam-nps` · Brazil / Nexo section |
| Mexico | `Mexico` | Survey NPS (`0Kd7V000000KymySAC`) | `es` | `#latam-nps` · Mexico section |

All three also require **Facilitators SP** (`0KdPP0000000H450AE`) in the same language.
Survey Ids and languages were verified read-only on 2026-11-25. Italy, Spain and Netmind
exist in Salesforce but are out of scope.

## 5. Salesforce data contract

### 5.1 Projects (read)

Object `rosscrooke__Project__c`. Base filter: start date in selection range,
`Billing_Country__c IN (registry values)`. Report-equivalent filters (exclude `Cancelled`,
empty sub-type, `License`, others pending confirmation of the report filter panel) are
applied **in the engine**, not in SOQL, so every excluded row can be explained.

| Engine raw key | Salesforce field |
|---|---|
| `billing_office` | `Billing_Country__c` (formula; not groupable) |
| `start_date` / `end_date` | `rosscrooke__Start_Date__c` / `rosscrooke__End_Date__c` |
| `client_name` | `rosscrooke__Client_Name__c` |
| `project_name` | `Name` |
| `project_url` | built from `Id` |
| `project_sub_type` | `Project_Sub_Type__c` |
| `status` | `rosscrooke__Status__c` |
| `all_staffings` | `All_Staffings__c` |
| `ignore_reporting` | `rosscrooke__Ignore_Reporting__c` (boolean) |
| `survey_invitation` | `Survey_Invitation__c` (informational only) |

### 5.2 Survey state (read)

Object `Survey_Set__c` filtered by `Project__c IN (…)`, reading `Survey__c`,
`Survey_Language__c`, `SurveyNPS__c`, `Survey_Invitation_Link__c`, `QR_Code_URL__c`,
`CreatedDate`, `CreatedById`.

**Survey state is evaluated per survey kind.** `Project.Survey_Invitation__c` always points
to the NPS invitation, and on 2026-11-25 the 24–30/11 week had 27 NPS sets but only 21
Facilitators SP sets. A project is pending for a kind when no Survey Set of that kind exists;
the plan creates only what is missing.

**A kind is recognised by family, not by the registry survey Id** (finding 2026-11-25:
SELAM projects started Sep–Dec 2026 also carry client-specific NPS surveys and alternative
facilitator surveys). Rule decided by the PO on 2026-11-25 (D-V2-7); client-specific NPS
surveys are rare exceptions, but when present they count as the project's NPS:

- *NPS present* ⇔ the project has a Survey Set with `SurveyNPS__c = true`, whatever survey
  it uses (standard or client-specific).
- *Facilitators present* ⇔ the project has a Survey Set whose `Survey__c` belongs to the
  configured facilitator-survey family (`Facilitators SP` plus known regional variants).
- Any other Survey Set (`SurveyNPS__c = false`, not in the facilitator family) is reported as
  *other survey* and never satisfies or blocks a kind.

The registry survey Id is used only to **create** a missing kind, never to detect one.

### 5.3 Survey Sets (write)

Create `Survey_Set__c` with `Project__c`, `Survey__c`, `Survey_Language__c`,
`SurveyNPS__c` (true for NPS, false for SP), `IpAddress_Restricted__c = false`. Salesforce
automation fills invitation, link and QR in the same second. Only `Project__c` is required
at API level, so the engine always sets every field explicitly.

## 6. Runtime flows

### 6.1 Upcoming (read-only) — increment 1

1. Claude: `nps select --preset standard --date <d> [--add-days n] [--filter …]` →
   `selection.json` + SOQL text.
2. Claude runs the SOQL through the connector and saves raw JSON (`projects.json`,
   `survey_sets.json`).
3. Claude: `nps upcoming --run <dir>` → `worklist.json`, `review.json`, `excluded.json`,
   `already_created.json`, `slack_table.html`, `preview.md`.
4. Claude shows `preview.md`: pending / excluded with reason / manual review / already
   created / special-case warnings.

### 6.2 Create surveys — increment 2

Detailed plan, verified creation recipe and pilot protocol:
`documentation/plans/V2-2_create_surveys.md` (D-V2-13).

1. Steps 1–3 above, plus `write_plan.json` with `plan_hash`.
2. Preview with one row per project: client, session, date, facilitator, country, language,
   surveys to create. The PO may remove projects (`nps plan --exclude <ids>` → new hash).
3. PO approves the **hash shown**.
4. Re-check: Claude re-queries survey state; `nps plan --recheck` drops commands whose
   survey now exists. If anything changed, the new plan is shown again.
5. Claude executes each command with `salesforce_create`, one at a time, recording every
   response in `execution.json`. Stops at the first unexpected error.
6. Read-back query → `nps reconcile` → result table (created / skipped / failed, with links
   and QR) and the completed Slack table.

First run: pilot with **one** project, verifying `CreatedBy`, side effects (e-mails, flows)
and whether `SurveyNPS__c` is set by automation.

### 6.3 Publish to Slack — increment 3

Three levels: draft (DM to the PO) → confirmed (shows channel, canvas and content before
posting) → automatic (scheduled task). The warning row is never part of the published table
(fixes NPS-003 by design). The canvas lookup strategy is pending discovery of real canvases.

### 6.4 Special cases

A facilitator watch-list kept **outside the repository** (local or audit-store
configuration, never committed; the test suite uses synthetic names). Matching projects are
created normally, flagged in the preview, and get an ordered data package for a
personalised e-mail; optional Outlook draft (never sent automatically).

**V2-5 step 1 (2026-11-27, D-V2-14/15).** The Slack page writes one e-mail per
watch-listed facilitator (subject `NPS week dd/mm/yy`, greeting, the Slack session
cards with day-first dates and the QR, closing), to copy and paste into Outlook.
Its language: the facilitator's office (`User.Department`, e.g. `MX-Mexico City`,
looked up read-only by the `facilitator_offices` query that `surveys` adds when the
watch-list matches someone) when it is a registry market; otherwise the language of
the countries of their sessions (billing office); templates `es`, `pt-BR`, `en-US`.
Salesforce has no nationality field: the office is the closest reliable signal
(10/10 checked users had it; `Country` and locale are mostly empty or `en_US`).

**Parked by the PO (2026-11-27): keep copy and paste; revisit later.** The notes
below are kept for that future discussion.

**Idea — sending the e-mails (V2-5 step 2/3).** Same safety model
as V2-2: a send plan page (recipient, subject, language, sessions), an approval code
typed by the user, one send per call, an audit in the run folder, and never from the
scheduled run. Open points before designing it:

- recipients: add `Email` to the office lookup (from `User`);
- the Microsoft 365 connector's draft tool rejects images in HTML, so the QR cannot
  travel embedded; options are a link to the hosted QR, a PNG attachment (if a tool
  allows attachments), or keeping copy and paste for the QR;
- send directly or create drafts for one click review (drafts first is safer);
- who signs (the operator; the Outlook signature is not added to API drafts).

### 6.5 Scheduled Monday run — increment 1 extension (read-only)

A scheduled task (a fresh Claude session each Monday, with the installed skill and the
BTS connector) asks for "the scheduled weekly run". The skill then runs, without
questions, exactly the standard week of today in Buenos Aires (`select --this-week`,
fixed offset UTC−3; no filters, no extra days) and delivers the summary, the preview
page and the Slack page in that session. Any error stops the run and is reported first.
Wider or filtered selections stay manual runs. Being read-only, it can run during the
parallel run; it replaces neither the PO's review nor the desktop run until sign-off.

### 6.6 Results into the Slack cards — increment 4 (design note, 2026-11-26)

Requested by the PO for a future version: a weekly scheduled task that finds sessions
whose results are available and fills them into the `#latam-nps` canvases.

1. **Find pending cards.** Read the canvases (`slack_read_canvas`) and collect the cards
   still showing `Results: NO`. The card's `Link for Results` link carries the Project ID,
   so cards are matched by project, never by session title.
2. **Check results.** For each project, query Salesforce; if the "results available" rule
   holds, generate the report with `survey-results-reports` (Box).
3. **Plan.** The deterministic engine writes the edit plan ("canvas X, project Y:
   `Results: NO` → `Results: [Report](<Box link>)`") with a plan hash, like V2-2.
4. **Apply and verify.** Re-read the canvas right before writing (section ids change on
   every update), replace only that section (`slack_update_canvas`), read back. A card
   that no longer matches (edited by hand) is skipped and reported.
5. **Audit** every change in the audit store (D-V2-2).

Approval in two stages: first the scheduled task only proposes (notification with the
plan; the PO approves and it is applied); later, after clean weeks, the PO may allow
this narrow, reversible edit to apply on its own. Depends on V2-3 (canvas lookup,
D-V2-3). Open: D-V2-9 (definition of "results available": minimum responses, days after
the session) and D-V2-10 (what goes in the card: Box link or file; identity used to
write in Slack and Box).

### 6.7 User interface (all views)

Every HTML view a user sees or operates (the Slack page today; the survey-creation
preview and approval in V2-2; later views) is built on one shared kit,
`nps_v2/outputs/ui_kit.py` (D-V2-11):

- Ionic web components (`@ionic/core`, exact pinned version, iOS mode) loaded from the
  CDN when the page opens; nothing is installed in the repository or the skill.
- BTS theme through Ionic's CSS variables (magenta, charcoal, Inter) and the ACT &
  SURVEYS card look.
- Mandatory fallback: every `ion-*` element a view uses has a `:not(:defined)` rule,
  so a viewer that blocks the CDN still gets a working BTS page (tests enforce it).
- Shared behaviour (`window.BTSUI`): toast notices, clipboard with fallbacks, manual
  copy. What is copied or written elsewhere (Slack payload) never carries kit markup.
- Views on the kit: the Slack page; the Upcoming preview (`preview.html`) and the
  parallel-run comparison (`compare.html`), both with search and country tabs where
  useful (`nps_v2/outputs/review_pages.py`); the creation plan and result pages.
  `preview.md` and `compare.md` stay as plain-text copies of the same content.

## 7. Safety model

| Risk | Control |
|---|---|
| Duplicate surveys | per-kind state check + re-check right before writing + idempotency key per command |
| Wrong survey or language | `SurveyPolicy` from registry, unit-tested per country; preview shows both |
| Model improvisation | SOQL and plans generated by code; Claude executes only commands in an approved plan whose hash matches |
| Partial failure | sequential execution, stop on unexpected error, reconcile reports exactly what exists |
| Hidden automation side effects | single-project pilot; observe e-mails/flows before scaling |
| Untraceable writes | connector writes with the PO's identity (to confirm in pilot); `execution.json` stored in the audit store |
| Wrong Slack post | draft level first; table built by renderer, never free text |

## 8. Persistence and audit

The Cowork workspace is ephemeral. Each run produces a run folder (`selection.json`, raw
snapshots, plan, execution, reconcile, outputs). **Proposed:** keep the audit copy in a
restricted Box folder (Box is already used by `survey-results-reports`). Real data never goes
to the repository. *Decision pending (D-V2-2): not needed for V2-1, which is read-only and
keeps its run folders in the session workspace; required before V2-2 (first writes).*

## 9. Packaging and distribution

- Source of truth: this repository. New code under `nps_v2/`; skill definition under
  `skill/` (`SKILL.md` + build script that vendors `nps_v2/` and the needed
  `engine/stages` into the skill's `scripts/`, without PySide6, bs4 or Windows paths).
- Delivery: personal skill for the PO first; later the BTS organization plugin catalog.
- Scheduled tasks (Monday worklist, daily alerts, weekly results) are created only when the
  corresponding increment is certified. Exception: the read-only Monday run (§6.5) may
  be scheduled during the V2-1 parallel run.

## 10. Testing strategy

- Unit tests for selection, registry, adapter, survey policy, plan builder (hash stability),
  re-check, reconciler, SOQL builders.
- **Adapter equivalence test**: synthetic Salesforce JSON → adapter → certified stages must
  produce the same worklist as the equivalent synthetic `.eml` fixture.
- Golden master stays green; V2 adds its own snapshots under `tests/snapshots/v2/`.
- Live validation (outside the repo): parallel run against v1.0.2 for 2–3 Mondays, plus the
  pending "exactly at 13:00 UTC" equivalence check.
- Tests must pass on Linux (the skill runtime) and Windows. See NPS-022.

## 11. Incremental plan

| Inc. | Scope | Writes | Exit criteria |
|---|---|---|---|
| V2-1 | Upcoming + Slack table, read-only; selection; per-kind survey state; country registry; special-case flags | none | tests green on Linux; 2–3 Mondays of parallel run with 0 unexplained differences; PO sign-off |
| V2-2 | Create surveys: plan, preview, approval, re-check, execution, reconcile | Salesforce `Survey_Set__c` | Salesforce write permission confirmed with PRO; single-project pilot; then one full week |
| V2-3 | Slack publication levels + special-case e-mail drafts | Slack, Outlook drafts | canvas structure confirmed; draft level used ≥2 weeks |
| V2-4 | Results + Data Quality/PRO + alerts (scheduled) + `survey-results-reports` integration | optional Ignore Reporting fixes (approved) | PRO validation |
| V2-5 | Facilitator follow-up with language templates. **Step 1 done (2026-11-27); sending parked by the PO, copy and paste stays:** the Slack page writes the personalised e-mail of each watch-listed facilitator (subject, greeting and the same session cards with QR) for copy and paste into Outlook | Step 1: none (copy and paste). Next: Outlook drafts | PO approval of templates |
| V2-6 | Decommission desktop app and Power Automate | — | V2-1…V2-3 certified |

## 12. Open decisions and questions

| ID | Topic | Status |
|---|---|---|
| D-V2-1 | Report-equivalent sub-type exclusions (need the report filter panel) | open |
| D-V2-2 | Audit of each creation: the refreshed Slack page plus an Excel creation log delivered to the user; Salesforce `CreatedBy`/`CreatedDate` as the durable trace (V2-2 plan §5) | **decided 2026-11-26** |
| D-V2-3 | Canvas structure in `#latam-nps` (per project / per client; country sections) | open — read one canvas with PO permission |
| D-V2-4 | Salesforce write identity: the user operating the tool, through their own BTS connector (no fixed or technical account); permissions checked by a preflight `describe` | **decided 2026-11-26** |
| D-V2-5 | NPS-004 (`meli` substring) and NPS-015 (generic coaching / 1:1) | open, carried over |
| D-V2-6 | Days threshold for "Survey Invitation missing" alert | open (V2-4) |
| D-V2-7 | Survey-kind detection by family (§5.2) | **decided 2026-11-25** |
| D-V2-8 | Product language: English for everything users see or operate (preview, Slack page and cards, comparison, skill instructions); code is not translated; the certified engine's Spanish messages are worded in English by V2 (`nps_v2/reasons.py`, `config/v2/rule_labels.json`) without changing `engine/` | **decided 2026-11-26** |
| D-V2-9 | "Results available" rule for §6.6 (minimum responses, days after the session) | open (V2-4) |
| D-V2-10 | Results in the card: Box link or file; identity for Slack/Box writes | open (V2-4) |
| D-V2-11 | Every HTML view uses the shared Ionic + BTS kit (§6.7): Ionic 8.8.19, iOS mode, mandatory fallback | **decided 2026-11-26** |
| D-V2-12 | Approval mechanism for writes: the user confirms the plan hash in the chat (V2-2 plan §10) | proposed |
| D-V2-13 | Survey creation path: A, reproduce the UI screen flow via API (recipe verified 48/48 by reading), proven by a one-project pilot; B, an admin-built invocable flow, as fallback | **decided 2026-11-26** |
| D-V2-14 | Personalised e-mail for special cases: one per facilitator per run, subject `NPS week dd/mm/yy` (Monday of the report), short Spanish greeting, the Slack session cards (dates day-first) and a closing line; copied from the Slack page, never sent by the engine | proposed 2026-11-27 (PO to confirm the wording) |
| D-V2-15 | Language of the personalised e-mail: facilitator office (`User.Department` prefix = registry market) first, then the countries of their sessions; English template when no market matches | proposed 2026-11-27 (PO asked for nationality, then billing office; office is the closest field) |
| D-V2-16 | What the user gets: a run (manual or scheduled) delivers one page, the plan page (surveys to create with the approval code, plus the rest of the week); after creating, the Excel creation log and the Slack page. Preview, result page and the other files only on request | **decided 2026-11-27 (PO)** |
| — | `#latam-nps` scope = AR, BR (incl. Nexo), MX only | **decided 2026-11-25** |

## 13. Known issues affecting V2

- **NPS-022 (proposed):** golden-master provenance hashes raw bytes; files checked out with
  LF (Linux) do not match hashes recorded with CRLF (Windows), so `test_provenance` fails on
  Linux while all behavior snapshots pass. Proposed fix: normalise line endings before
  hashing and re-sign provenance (PO approval required). Not yet in
  `DEVELOPMENT_ROADMAP.md`.
- Desktop UI tests (PySide6/WebEngine) crash headless on Linux; they are irrelevant to the
  skill and should be marked as Windows/UI-only.
- NPS-001 fix is merged into the reused engine via F2-02b (Codex), independent of V2.
