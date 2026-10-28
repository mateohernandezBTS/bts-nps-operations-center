# Execution Plan — F0-02 Phase 0 tooling

## 1. Purpose
Correct the Phase 0 document layout and preserve the F0-01 verification evidence.
Add development tooling and measure existing debt without changing application behavior.

## 2. Context
- Related phase: Phase 0; register entries NPS-001 through NPS-019.
- Relevant files: AGENTS.md, documentation, requirements-dev.txt, pyproject.toml, .gitignore.
- Baseline: develop at 7931ec0; Windows unittest ran 69 tests, with 63 passing,
  no failures and six missing-fixture errors (F0-01L).

## 3. Scope
In scope:
- Move the four foundation documents with git mv.
- Update environment instructions, test artifact permissions and register evidence.
- Pin development tools, configure them and capture validation totals.
- Commit and push chore/phase-0-tooling; open no pull request.

Out of scope:
- Changes under app/, engine/, config/, packaging/ or tests/.
- Business changes, missing fixture creation, lint fixes and formatting changes.

## 4. Constraints
- Application behavior and production dependencies remain unchanged.
- TMP and TEMP point to the repository's .tmp. After confirming NPS-019, only the
  exact unittest and pytest commands may run outside the sandbox with explicit approval.
- Other commands stay inside the sandbox. No GUI launch, build, process termination
  or operational data access.
- Only tests may delete their own empty temporary .exe placeholders.

## 5. Steps
| # | Step | Files | Validation | Commit message |
|---|---|---|---|---|
| 1 | Move foundation documents | documentation/, documentation/plans/ | Rename-only diff | docs: move phase 0 documents to documentation folder |
| 2 | Document local-first setup and sandbox test rules | AGENTS.md | Review exact scope | docs(agents): local-first environment and temp test artifact exception |
| 3 | Record verified register evidence | documentation/DEVELOPMENT_ROADMAP.md, this plan | Check cited lines and discovery counts | docs(roadmap): record phase 0 verification evidence |
| 3b | Diagnose tempfile ACLs and document the approved exception | AGENTS.md, documentation/DEVELOPMENT_ROADMAP.md, this plan | Sandbox mkdir/mkdtemp probes, icacls and installed tempfile source | docs(agents): document sandbox test exception (NPS-019) |
| 4 | Add tooling and validate | requirements-dev.txt, pyproject.toml, .gitignore, this plan | compileall, unittest, pytest, ruff, mypy | build: add development tooling configuration |

## 6. Validation strategy
- Verify latest stable tool releases and Python 3.14 compatibility against PyPI.
- Run compileall and both test runners; compare against the F0-01 Windows baseline.
- Record ruff and mypy totals as debt, without fixing existing code.
- Review the final diff for prohibited directory changes and verify pushed branch state.

### Recorded results (2026-10-28)

- Python 3.14.6; Ruff 0.17.3, pytest 9.2.0, pytest-cov 7.1.0 and mypy 2.4.0.
- Pin selection used PyPI metadata: [Ruff](https://pypi.org/project/ruff/0.17.3/),
  [pytest](https://pypi.org/project/pytest/9.2.0/),
  [pytest-cov](https://pypi.org/project/pytest-cov/7.1.0/) and
  [mypy](https://pypi.org/project/mypy/2.4.0/). Each advertised Python 3.14 support.
- Compilation: passed inside the sandbox.
- Approved exact unittest command: 69 run, 63 passed, no failures, six errors,
  no skips; exit 1. This reproduces F0-01's Windows baseline.
- Approved exact pytest command: 69 cases, 63 passed, six failed, no skips;
  exit 1. The same six missing-fixture exceptions are classified as failures by
  pytest and errors by unittest. No additional tests or collection errors appeared;
  norecursedirs was not needed.
- Ruff check inside the sandbox: 152 violations; exit 1. No fixes applied.
- Mypy app/engine check inside the sandbox: 32 errors in 11 files, with 74 source
  files checked; exit 1. This is a debt baseline, not an enforced module scope.
- TOML parsing passed; pyproject.toml contains tool configuration only.
- No changes under app/, engine/, config/, packaging/ or tests/.
- The earlier sandbox run's permission failures are explained by NPS-019; the
  baseline above comes from the subsequently approved exact test commands.

## 7. Risks and mitigations
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Missing .eml fixtures | Known | Six tests cannot run their intended scenarios | Report the existing errors; do not create fixtures |
| Runner discovery differences | Possible | Counts may differ | Inspect collection and report discrepancies without changing tests |
| Sandbox tempfile ACL incompatibility (NPS-019) | Confirmed | Test runs inside sandbox produce permission errors | Limit approved escalation to the exact unittest and pytest commands |

## 8. Rollback
Keep changes isolated on chore/phase-0-tooling for review. If rollback is requested,
use new revert commits; do not rewrite published history or delete branches.

## 9. Progress
- [x] Step 1: documents moved with git mv (7d6e32a).
- [x] Step 2: agent instructions updated (696b6e0).
- [x] Step 3: register evidence recorded; recursive inventory confirms 11 of 29 files contribute cases.
- [x] Step 3b: NPS-019 diagnosed without escalation; test exception documented (86d0c6c).
- [x] Step 4: tooling installed and validation recorded; branch prepared for the final push.

## 10. Decision log
| Date | Decision | Reason | Decided by |
|---|---|---|---|
| 2026-10-28 | Keep existing application and test code unchanged | Explicit F0-02 scope | User |
| 2026-10-28 | Run tests only inside the sandbox with repository-local temporary files | Additional step 4b | User |
| 2026-10-28 | Replace the test escalation prohibition after confirming NPS-019; approve only exact unittest and pytest commands | Resume F0-02 supersedes the earlier test escalation prohibition | User |
| 2026-10-28 | Allow a scoped Git exception for staging, committing the requested files and pushing chore/phase-0-tooling | Sandbox denies .git/index.lock writes; user explicitly approved the scoped Git exception after automatic review rejected the initial escalation | User |
