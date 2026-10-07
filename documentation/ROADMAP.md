# BTS SELAM NPS Operations Center

## Product roadmap

Current release: **1.0.0 — Production Ready**

## Delivered in 1.0.0

- PySide6 desktop UI
- Dashboard, Weekly Run, environment selector, and source readiness
- Weekly Output, Manual Review, Run History, and Settings
- reproducible PyInstaller packaging and portable distribution
- operational logging and manifests
- PRODUCTION safeguards and explicit confirmation
- packaged TEST/PRODUCTION isolation

## Future integrations

### Salesforce API

- authentication and direct report retrieval
- project lookup and survey status
- automatic survey creation and related links/QR codes

### Slack API

- direct publication of generated operational content
- team notifications

### Power Automate final integration

- finalize and operationalize external email delivery into the packaged data tree

## Future distribution and operations

- installer
- code signing
- final application icon, if required
- auto-update
- separated external data root
- automatic retention

## Development principles

Every future change must preserve the deterministic backend, UI/controller separation, TEST/PRODUCTION isolation, external business rules, traceability, and regression coverage. Future items are not represented as implemented until independently validated.
