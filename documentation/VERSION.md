# BTS SELAM NPS Operations Center

## Product information

- Product name: BTS SELAM NPS Operations Center
- Version: **1.0.2**
- Release status: **Production Ready**
- Windows file version: **1.0.2.0**

Version 1.0.2 is a production-ready patch. It enables the interactive
client-level Copy for Slack controls in Weekly Output.

## Certified capabilities

- deterministic backend processing of Upcoming `.eml` reports
- complete PySide6 desktop frontend
- report detection, preflight, normalization, and business rules
- weekly orchestration and SELAM aggregation
- Excel, Slack HTML, Manual Review, manifests, and summaries
- Session Manager, Run History, and operational logging
- backend and UI production safeguards
- packaged TEST/PRODUCTION data and session isolation
- reproducible PyInstaller onedir build and release validator
- portable distribution and Python-independent startup
- final packaged TEST E2E

## Supported environments

- TEST
- PRODUCTION

Both environments execute the same engine with independent paths, session state, inputs, outputs, and logs.

## Validation summary

```text
Regression:             69/69 PASS
Compileall:             PASS
Release validation:     PASS
Packaged TEST E2E:      PASS
Session isolation:      PASS
Portable startup:       PASS
```

## Version 1.0.0 scope exclusions

The following are not implemented capabilities of this release:

- Salesforce API
- Slack API
- final Power Automate integration
- installer, code signing, and final icon work
- auto-update
- separated external data root
- automatic retention
