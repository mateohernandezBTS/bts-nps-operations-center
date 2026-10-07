# BTS SELAM NPS Operations Center

## System Architecture

Version: **1.0.0 — Production Ready**

## 1. Product overview

BTS SELAM NPS Operations Center is a portable PySide6 desktop application built around a deterministic processing engine. Business rules remain isolated in the engine and external configuration; the UI presents state and delegates all operations.

## 2. Application layers

```text
UI
  -> UIController
  -> Application Controller
  -> Session Manager / Engine
```

- `app/`: PySide6 views, widgets, and the UIController boundary.
- `UIController`: translates UI intent and engine state without implementing business rules.
- `NPSApplicationController`: single orchestration entry point for preflight and weekly processing.
- `SessionManager`: persists one concrete environment-specific session file.
- `engine/`: detection, parsing, normalization, business rules, orchestration, aggregation, outputs, lifecycle, and logging.

## 3. Operational data flow

```text
Outlook / external input
  -> .eml
  -> Application Controller
  -> Preflight
  -> Processing Engine
  -> Business Rules
  -> Weekly Orchestrator
  -> SELAM Aggregator
  -> Output Generation
  -> Desktop UI
```

Preflight is read-only. Weekly processing controls the input lifecycle and produces per-execution and weekly artifacts. The desktop UI exposes source readiness, execution state, results, Manual Review, and history.

## 4. TEST/PRODUCTION path isolation

`engine/paths.py` centrally resolves persistent paths. It never uses PyInstaller `_MEIPASS` for writable operational or session data.

| Mode | PRODUCTION root | TEST root |
|---|---|---|
| Source | repository root | `repository/tests` |
| Frozen | executable data root | `executable data root/test_data` |
| `BTS_SELAM_DATA_ROOT` override | override root | `override root/test_data` |

Inputs, outputs, logs, runtime state, and `current_session.json` remain isolated. The Application Controller owns independent TEST and PRODUCTION Session Managers and selects one for the full operation. The UI always requests state for the currently selected environment.

## 5. Configuration and logging

Business rules and operational settings are external files under `config/`. The UI does not duplicate or mutate business rules. Execution logs, operational logs, manifests, and summaries provide traceability while session state provides the current UI-facing status.

## 6. Processing and outputs

The engine performs report detection, Salesforce HTML parsing, normalization, weekly-window filtering, deterministic business-rule evaluation, worklist generation, weekly orchestration, and SELAM aggregation.

Outputs include:

- weekly Excel workbook
- Slack Canvas HTML
- Manual Review artifacts
- weekly and execution summaries
- manifests and operational logs

Successful inputs move from `upcoming` to `processing` to `processed`; failed inputs move to `error`. Existing weekly output protection prevents silent overwrite.

## 7. Desktop application

The frontend is implemented in PySide6 and includes Dashboard, Weekly Run, Weekly Output, Manual Review, Run History, and Settings. Environment switching refreshes environment-specific session state and paths. PRODUCTION execution requires the certified safeguards and explicit confirmation.

## 8. Packaging

PyInstaller produces a reproducible Windows onedir distribution. The release is portable, starts without Python on `PATH`, carries external configuration, and is independently checked by `packaging/validate_release.py`. Operational execution occurs from copies; the master release remains clean and frozen.

## 9. Validation strategy

The automated suite covers engine behavior, controllers, UI state, lifecycle, safeguards, path resolution, and TEST/PRODUCTION session isolation in source and frozen modes.

```text
Regression:         64/64 PASS
Compileall:         PASS
Packaged TEST E2E:  PASS
```

## 10. Future integrations

Salesforce API, Slack API, final Power Automate integration, installer/signing/icon work, auto-update, separated external data root, and automatic retention remain outside Version 1.0.0.
