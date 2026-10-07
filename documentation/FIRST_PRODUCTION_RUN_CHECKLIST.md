# First Production Run Checklist

Use this checklist during the first real PRODUCTION weekly run.

Do not execute the weekly process unless every required PRE-RUN and
PREFLIGHT item is satisfied.

Legend:

- [REQUIRED] Mandatory control.
- [HUMAN] Human validation required.
- [AUTOMATIC] Validated or enforced by the application.
- [ABORT] Stop the operation.
- [EVIDENCE] Preserve as certification evidence.

---

## 1. PRE-RUN

- [ ] [REQUIRED] Release validator result is `RELEASE VALIDATION PASSED`.
- [ ] [REQUIRED] Packaged TEST E2E certification is complete.
- [ ] [REQUIRED] Clean master release is preserved and has not been used for
  operational testing.
- [ ] [REQUIRED] Executable SHA-256 has been recorded and matches the certified
  master identity.
- [ ] [REQUIRED] This operation is running from an authorized copy of the master
  release; the master itself is never used for TEST or PRODUCTION operations.
- [ ] [REQUIRED] Packaged executable is being used:
  `BTS SELAM NPS Operations Center.exe`
- [ ] [REQUIRED] External `config/` folder is present beside the executable.
- [ ] [REQUIRED] Productive config files are present:
  `business_rules.json`, `operational_output.json`,
  `report_detection.json`, `report_sources.json`,
  `system_config.json`, `weekly_schedule.json`.
- [ ] [REQUIRED] PROD paths shown in Settings point to the packaged
  production tree, not to `test_data/` or source `tests/`.
- [ ] [REQUIRED] Weekly Run Environment is set to `PRODUCTION`.
- [ ] [HUMAN] Reference Monday is correct.
- [ ] [HUMAN] Weekly Window is correct: Tuesday through Monday.
- [ ] [REQUIRED] Correct Argentina Upcoming `.eml` is present in the
  productive `input/upcoming` consumed by the application.
- [ ] [REQUIRED] Correct Brazil Upcoming `.eml` is present in the
  productive `input/upcoming` consumed by the application.
- [ ] [REQUIRED] Correct Mexico Upcoming `.eml` is present in the
  productive `input/upcoming` consumed by the application.
- [ ] [HUMAN] No duplicate weekly source files are present.
- [ ] [HUMAN] No unrelated files are present in productive `input/upcoming`.
- [ ] [REQUIRED] No previous weekly run exists for the same weekly run ID
  under `output/weekly_runs/`.

If any PRE-RUN required item fails, stop before PREFLIGHT.

---

## 2. PREFLIGHT

- [ ] [REQUIRED] `PRODUCTION` is selected.
- [ ] [REQUIRED] Run Preflight.
- [ ] [AUTOMATIC] Preflight status is `READY_TO_PROCESS`.
- [ ] [AUTOMATIC] Expected sources = `3`.
- [ ] [AUTOMATIC] Matched sources = `3`.
- [ ] [AUTOMATIC] Missing required sources = `0`.
- [ ] [AUTOMATIC] Duplicates = `0`.
- [ ] [AUTOMATIC] Issues = none.
- [ ] [AUTOMATIC] Existing weekly run = false.
- [ ] [EVIDENCE] Preserve the production preflight log under
  `logs/preflight/`.

Only continue when status is:

```text
READY_TO_PROCESS
```

- [ ] [ABORT] If preflight returns `BLOCKED`, do not execute.
- [ ] [ABORT] If preflight returns `FAILED`, do not execute.

---

## 3. EXECUTION

- [ ] [REQUIRED] Start `Run Weekly Process` only after preflight is
  `READY_TO_PROCESS`.
- [ ] [REQUIRED] Production confirmation modal appears.
- [ ] [HUMAN] Modal shows `Environment: PRODUCTION`.
- [ ] [HUMAN] Modal Reference Monday matches the intended run.
- [ ] [HUMAN] Modal Weekly Window matches the intended run.
- [ ] [ABORT] Click `Cancel` if any modal value does not match.
- [ ] [REQUIRED] Click `Run Production` only after confirming all values.
- [ ] [REQUIRED] Do not close the application during processing.
- [ ] [REQUIRED] Do not move the packaged application folder during
  processing.
- [ ] [REQUIRED] Do not execute the same week twice.
- [ ] [AUTOMATIC] Application blocks concurrent operation attempts.
- [ ] [AUTOMATIC] Backend re-runs preflight before weekly processing.
- [ ] [AUTOMATIC] Backend blocks duplicate weekly runs.

---

## 4. OUTPUT VALIDATION

- [ ] [REQUIRED] Final status is `COMPLETED` or `COMPLETED_WITH_REVIEW`.
- [ ] [HUMAN] Dashboard READY count reviewed.
- [ ] [HUMAN] Dashboard REVIEW count reviewed.
- [ ] [HUMAN] Dashboard clients count reviewed.
- [ ] [REQUIRED] Excel package exists and opens.
- [ ] [REQUIRED] Slack HTML exists and renders.
- [ ] [REQUIRED] Manual Review CSV exists.
- [ ] [REQUIRED] Run History shows the production weekly run.
- [ ] [HUMAN] Results URLs / project URLs are present where expected.
- [ ] [HUMAN] Excel worklist is operationally plausible.
- [ ] [HUMAN] Slack HTML content is operationally plausible.
- [ ] [REQUIRED] If REVIEW > 0, human review/resolution is required before
  considering the operation closed.
- [ ] [EVIDENCE] Preserve final Dashboard screenshot.
- [ ] [EVIDENCE] Preserve Weekly Output screenshot.
- [ ] [EVIDENCE] Preserve Run History screenshot.

---

## 5. TRACEABILITY

Preserve or verify these certified artifacts:

- [ ] [EVIDENCE] `output/weekly_runs/<weekly_run_id>/weekly_manifest.json`
- [ ] [EVIDENCE] `output/weekly_runs/<weekly_run_id>/selam_weekly_summary.json`
- [ ] [EVIDENCE] `logs/preflight/<timestamp>_READY_TO_PROCESS.json`
- [ ] [EVIDENCE] `logs/<execution_id>.json` for each processed source.
- [ ] [EVIDENCE] `output/runs/<execution_id>/execution_manifest.json`
  for each processed source.
- [ ] [EVIDENCE] `output/runs/<execution_id>/execution_summary.json`
  for each completed source.
- [ ] [EVIDENCE] `output/runs/<execution_id>/error_details.json`
  when applicable.
- [ ] [EVIDENCE] `runtime/sessions/current_session.json`
- [ ] [HUMAN] Confirm artifacts are under production paths, not `test_data/`.

---

## 6. POST-RUN

- [ ] [REQUIRED] Sources corresponding to the processed run no longer remain
  in productive `input/upcoming`.
- [ ] [REQUIRED] `input/processing` is empty for the completed run.
- [ ] [REQUIRED] Processed sources are present under `input/processed`.
- [ ] [REQUIRED] `input/error` is empty for a clean run.
- [ ] [REQUIRED] Weekly outputs are persisted under
  `output/weekly_runs/<weekly_run_id>/`.
- [ ] [REQUIRED] Execution logs are persisted under `logs/`.
- [ ] [REQUIRED] No unexpected TEST writes occurred under `test_data/`.
- [ ] [HUMAN] Manual Review disposition is recorded when REVIEW > 0.
- [ ] [EVIDENCE] Preserve processed source list.

---

## 7. RECOVERY / ABORT

### BLOCKED

- [ ] [ABORT] Do not execute weekly processing.
- [ ] [REQUIRED] Correct the input or blocking condition.
- [ ] [EVIDENCE] Preserve blocked preflight evidence.
- [ ] [REQUIRED] Repeat preflight after correction.
- [ ] [REQUIRED] Continue only after `READY_TO_PROCESS`.

Common BLOCKED causes:

- Missing Argentina, Brazil, or Mexico Upcoming source.
- Duplicate source.
- Unknown or unconfigured report.
- Report detection review.
- Existing weekly run.
- Invalid or unintended weekly window.

### FAILED

- [ ] [ABORT] Do not retry immediately.
- [ ] [REQUIRED] Review `runtime/sessions/current_session.json`.
- [ ] [REQUIRED] Review `logs/`.
- [ ] [REQUIRED] Review `error_details.json` when present.
- [ ] [REQUIRED] Review execution manifests.
- [ ] [REQUIRED] Determine whether partial outputs were generated.
- [ ] [REQUIRED] Identify root cause before any retry.
- [ ] [EVIDENCE] Preserve failed source `.eml` and diagnostics.

### DO NOT RETRY IF

- [ ] [ABORT] A weekly run already exists and its status has not been
  reviewed.
- [ ] [ABORT] `weekly_manifest.json` already exists for the same week and
  the recovery path is not approved.
- [ ] [ABORT] Partial production outputs exist and have not been reviewed.
- [ ] [ABORT] Failed source files have not been preserved.
- [ ] [ABORT] The duplicate/unknown/missing source condition still exists.
- [ ] [ABORT] The root cause of a failure is unknown.
- [ ] [ABORT] Manual Review impact is unresolved and REVIEW > 0.

---

## 8. CERTIFICATION EVIDENCE

Final evidence checklist:

- [ ] [EVIDENCE] Screenshot: Weekly Run with `PRODUCTION` selected.
- [ ] [EVIDENCE] Screenshot: preflight `READY_TO_PROCESS`.
- [ ] [EVIDENCE] Screenshot: production confirmation modal.
- [ ] [EVIDENCE] Screenshot: final Dashboard.
- [ ] [EVIDENCE] Screenshot: Weekly Output.
- [ ] [EVIDENCE] Screenshot: Run History.
- [ ] [EVIDENCE] `weekly_manifest.json`
- [ ] [EVIDENCE] `selam_weekly_summary.json`
- [ ] [EVIDENCE] Excel package.
- [ ] [EVIDENCE] Slack HTML.
- [ ] [EVIDENCE] Manual Review CSV.
- [ ] [EVIDENCE] Production preflight log.
- [ ] [EVIDENCE] `current_session.json`
- [ ] [EVIDENCE] Processed source list.
- [ ] [EVIDENCE] REVIEW disposition, if applicable.

Certification block:

```text
Weekly Run ID:
Reference Monday:
Weekly Window:
Final Status:
READY:
REVIEW:
Clients:
Human Validation Completed:
Operational Result:
```
