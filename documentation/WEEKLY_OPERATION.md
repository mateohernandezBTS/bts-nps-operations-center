# BTS SELAM NPS Automation

## Weekly Operation Guide

Version: 1.0.0 — Production Ready

---

## 1. Purpose

This guide describes the normal weekly operating procedure in the packaged
`BTS SELAM NPS Operations Center.exe` desktop application.

The current backend processes the following required reports:

- Argentina Upcoming
- Brazil Upcoming
- Mexico Upcoming

The weekly process is blocked if any required source is missing, duplicated, unknown, or requires report-detection review.

---

## 2. Weekly processing window

The process uses a Monday as the reference date.

The operational window starts on the following Tuesday and ends on the following Monday, inclusive.

Example:

```text
Reference Monday: 8/3/2026
Window start:     8/4/2026
Window end:       8/10/2026
```

---

## 3. Environment and input

The application starts in `TEST`. Select `PRODUCTION` explicitly only for an
authorized production operation. TEST and PRODUCTION data, session state,
outputs, lifecycle files, and logs are isolated.

Packaged paths:

```text
PRODUCTION: <application directory>/input, output, logs, runtime
TEST:       <application directory>/test_data/input, output, logs, runtime
```

Source/development paths:

```text
PRODUCTION: <repository>/input, output, logs, runtime
TEST:       <repository>/tests/input, output, logs, runtime
```

The paths shown in Settings are authoritative for the selected environment.

### Production input

Power Automate must save the three Upcoming report emails in:

```text
input/upcoming
```

Expected reports:

```text
Argentina Upcoming
Brazil Upcoming
Mexico Upcoming
```

Do not manually rename or modify the contents of the `.eml` files.

Before running the weekly process, verify that no unrelated files are present in the production input directory.

---

## 4. Preflight

In Weekly Run, select the environment, enter the reference Monday, verify the
displayed weekly window and source readiness, then run Preflight.

The preflight does not move, process, archive, or modify source files.

A successful preflight returns:

```text
STATUS
--------------------------------------------------------------------------------
READY_TO_PROCESS
```

The process must not continue when the preflight returns:

```text
BLOCKED
```

or:

```text
FAILED
```

---

## 5. Common blocking conditions

### Missing source

Example:

```text
Missing required source: Brazil upcoming
```

Action:

- confirm whether the email arrived;
- confirm whether Power Automate saved it;
- do not create a partial weekly run.

### Duplicate source

Example:

```text
Duplicate source: Mexico upcoming
```

Action:

- identify which file is the valid weekly report;
- preserve the duplicate outside `input/upcoming`;
- rerun the preflight.

### Unknown report

Example:

```text
Unknown or unconfigured reports detected: 1
```

Action:

- inspect the unexpected email;
- confirm whether it belongs to the weekly Upcoming process;
- do not modify configuration without validating the new source.

### Detection review

Example:

```text
Files require report-detection review: 1
```

Action:

- inspect the subject, sender, country and report type;
- do not force the weekly process until the file is correctly classified.

### Existing weekly run

Example:

```text
A weekly run already exists:
NPS_WEEK_YYYY-MM-DD_YYYY-MM-DD
```

Action:

- do not delete or overwrite the existing run without reviewing its status;
- confirm whether the run completed, failed or requires recovery.

### Invalid date

The reference date must be a Monday and must use:

```text
M/D/YYYY
```

---

## 6. Weekly execution

The normal operational entry point is:

```text
BTS SELAM NPS Operations Center.exe
```

1. Confirm the selected environment and reference Monday in Weekly Run.
2. Run Preflight and require `READY_TO_PROCESS`.
3. For PRODUCTION, complete the explicit production confirmation.
4. Run Weekly Process once.
5. Confirm completion and metrics on Dashboard and Weekly Run.
6. Inspect Weekly Output, Manual Review, and Run History.
7. Preserve the operational logs and manifests required for traceability.

Direct Python launchers are development/diagnostic interfaces, not the normal
weekly operating procedure. Do not execute `engine.process_weekly_run` directly
unless performing an approved technical diagnosis.

---

## 7. Processing lifecycle

Successful files follow:

```text
input/upcoming
  ->
input/processing
  ->
input/processed
```

Failed files follow:

```text
input/upcoming
  ->
input/processing
  ->
input/error
```

After a successful run:

```text
input/upcoming
```

and

```text
input/processing
```

should be empty.

---

## 8. Technical outputs

Individual report outputs are created in:

```text
output/runs
```

Each source report receives its own execution directory and execution ID.

Weekly consolidated outputs are created in:

```text
output/weekly_runs/NPS_WEEK_YYYY-MM-DD_YYYY-MM-DD
```

Expected weekly files include:

```text
NPS_WEEK_YYYY-MM-DD_YYYY-MM-DD.xlsx
selam_slack_canvas.html
selam_worklist.csv
selam_manual_review.csv
selam_weekly_summary.json
weekly_manifest.json
```

---

## 9. Operational deliverables

### Excel

The Excel workbook is the primary weekly operational package.

It contains:

- Home
- Worklist
- Manual Review
- Manifest
- Issues

The output remains compatible with direct copy and paste into Slack.

### Slack Canvas HTML

The HTML contains the weekly NPS creation list grouped by:

```text
Country
  ->
Office
  ->
Client
  ->
Session
```

If manual review records exist, the HTML displays a warning indicating that the visible list is not yet the complete operational worklist.

### Manual Review

The file

```text
selam_manual_review.csv
```

must always be reviewed whenever:

```text
Review records > 0
```

---

## 10. Business rules

Current business rules:

- Status must be `Conf`.
- Ignore Reporting must be `False`.
- Mercado Libre and MELI do not receive NPS reports.
- Clients whose name starts with BTS do not receive NPS reports.
- POD exclusions use whole-word matching.
- Mariano Sioli/Scioli and Maider Santos require separate handling.
- Coaching sessions, PODs and 1:1 sessions are excluded.

No Salesforce status should be modified without prior approval from the assigned PE.

---

## 11. Error recovery

When processing fails, the source email is moved to:

```text
input/error
```

The execution directory contains:

```text
error_details.json
execution_manifest.json
```

The final execution log is written to:

```text
logs
```

Recovery procedure:

1. Inspect `error_details.json`.
2. Inspect the execution manifest.
3. Identify the root cause.
4. Preserve the failed `.eml`.
5. Correct the issue.
6. Return a copy of the file to `input/upcoming`.

Never delete a failed report before preserving diagnostic evidence.

---

## 12. Session state

The current application state is stored independently by environment.

Packaged PRODUCTION:

```text
runtime/sessions/current_session.json
```

Packaged TEST:

```text
test_data/runtime/sessions/current_session.json
```

In source/development execution, PRODUCTION uses `runtime/sessions/` and TEST
uses `tests/runtime/sessions/`.

Possible operational states:

```text
PREFLIGHT_RUNNING
READY_TO_PROCESS
BLOCKED
PROCESSING
COMPLETED
COMPLETED_WITH_REVIEW
FAILED
```

The session file is intended for the graphical interface and does not replace execution manifests or logs.

---

## 13. Repeated execution protection

The backend blocks a weekly process whenever the expected weekly output directory already exists.

The system never overwrites a previous weekly package automatically.

---

## 14. Production validation completed

The controlled production trial validated:

- production input paths;
- production lifecycle;
- technical outputs;
- weekly outputs;
- logs;
- session persistence;
- duplicate-run protection.

Certified production result:

```text
Environment: PRODUCTION
Status: COMPLETED

Ready records : 21
Review records: 1
Clients       : 10
```

A second execution was correctly blocked.

---

## 15. Certified packaged operation

The packaged TEST E2E validated Preflight, Weekly Process, the expected baseline,
Excel, Slack HTML, Manual Review, Run History, manifests, summaries, operational
logs, input lifecycle, environment-aware session state, repository independence,
Python-independent startup, and zero PRODUCTION writes.

Operational testing must use a copy of the clean master release. Never place
inputs in, or execute TEST/PRODUCTION operations from, the preserved master.
