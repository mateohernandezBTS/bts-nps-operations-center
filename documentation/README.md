# BTS SELAM NPS Operations Center

## Weekly NPS Automation Platform

## Current release

- Product version: **1.0.0**
- Release status: **Production Ready**
- Windows file version: **1.0.0.0**

## Overview

BTS SELAM NPS Operations Center is the packaged PySide6 desktop application for preparing, validating, and managing weekly SELAM NPS operations. The normal operational entry point is `BTS SELAM NPS Operations Center.exe`; Python commands are reserved for development and technical validation.

The portable PyInstaller onedir distribution contains the complete frontend and certified backend. Its reproducible build and independent release validator identify and verify the deployable artifact.

## Current capabilities

- `.eml` source intake and report detection
- weekly preflight and source-readiness validation
- normalization and externalized business rules
- weekly orchestration and SELAM aggregation
- Excel, Slack HTML, Manual Review, manifests, and summaries
- Dashboard, Weekly Run, Weekly Output, Manual Review, Run History, and Settings views
- environment-aware Session Manager and operational logging
- isolated TEST and PRODUCTION paths, state, lifecycle, outputs, and logs
- explicit production confirmation, duplicate-run protection, and recovery safeguards
- portable packaged execution without a Python installation

## Product architecture

```text
Desktop UI
  -> UIController
  -> Application Controller
  -> Session Manager / Engine
  -> Business Rules / Weekly Orchestrator / SELAM Aggregator
  -> Output Generation and Operational Logs
```

The UI contains no business logic. TEST and PRODUCTION use the same engine but resolve independent data and session paths through `engine/paths.py`.

## Source layout

```text
app/            PySide6 desktop frontend
engine/         deterministic processing and application services
config/         external operational and business configuration
packaging/      reproducible build and release validation
tests/          automated regression suite and source TEST data root
documentation/ product and operating documentation
```

Packaged writable data is beside the executable: PRODUCTION uses `input/`, `output/`, `logs/`, and `runtime/`; TEST uses the corresponding tree under `test_data/`.

## Documentation

| Document | Purpose |
|---|---|
| `VERSION.md` | Product version and certification state |
| `ARCHITECTURE.md` | System architecture and isolation model |
| `CHANGELOG.md` | Implemented release history |
| `ROADMAP.md` | Remaining future work |
| `WEEKLY_OPERATION.md` | Normal weekly operating procedure |
| `FIRST_PRODUCTION_RUN_CHECKLIST.md` | Controlled first-production checklist |

## Validation

- Regression suite: **64/64 PASS**
- Source compilation: **PASS**
- Packaged TEST E2E: **PASS**
- Release validator: **PASS**
- Portable/Python-independent startup: **validated**
- TEST/PRODUCTION output and session isolation: **validated**

## Future integrations

Salesforce API, Slack API, final Power Automate integration, installer/signing/icon work, auto-update, separated external data root, and automatic retention remain future scope. They are not claimed as Version 1.0.0 capabilities.

## Development principles

- deterministic, functionally frozen backend
- UI -> UIController -> Application Controller -> Session Manager / Engine
- external business rules and configuration
- strict TEST/PRODUCTION isolation
- complete operational traceability
- regression validation for approved changes
