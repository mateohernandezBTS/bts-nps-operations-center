# BTS SELAM NPS Operations Center

## Changelog

## 1.0.2 - Production Ready

### Fixed

- Added client-level `Copy for Slack` buttons to Slack HTML output.
- Weekly Output now renders Slack HTML in `QWebEngineView` with JavaScript and clipboard access enabled.

## 1.0.1 — Production Ready

Promoted to Production Ready after successful packaged operational validation.

### Fixed

- Weekly Run ID is now persisted during successful standalone Preflight.

## 1.0.0 — Production Ready

### Added

- `.eml` intake and Salesforce report parsing
- automatic report and country detection
- source inventory and weekly preflight
- record normalization and externalized business rules
- weekly processing lifecycle and orchestration
- SELAM aggregation, manifests, and summaries
- Excel, Slack HTML, and Manual Review deliverables
- Application Controller and environment-aware Session Manager
- PySide6 desktop UI with Dashboard, Weekly Run, Weekly Output, Manual Review, Run History, and Settings
- operational and execution logging
- duplicate-run protection, recovery controls, and explicit PRODUCTION safeguards
- packaged TEST/PRODUCTION path and session isolation
- reproducible PyInstaller onedir build
- independent release validator and portable distribution
- first production run checklist

### Fixed

- isolated TEST and PRODUCTION `current_session.json` persistence in source and frozen execution
- corrected POD whole-word matching to avoid false exclusions such as “Empoderamiento”

### Validated

- final packaged TEST E2E
- Python-independent packaged startup
- release cleanliness and executable identity
- TEST/PRODUCTION lifecycle and zero-PRODUCTION-write isolation during TEST
- regression suite: **64/64 PASS**
- source compilation: **PASS**

### Not included

- Salesforce API
- Slack API
- installer, signing, auto-update, or final icon work
