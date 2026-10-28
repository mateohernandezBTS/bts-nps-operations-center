# Execution Plan — F0-02 Phase 0 tooling

## 1. Purpose
Correct the Phase 0 document layout and preserve the F0-01 verification evidence.
Add development tooling and measure existing debt without changing application behavior.

## 2. Context
- Related phase: Phase 0; register entries NPS-001 through NPS-018.
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
- Tests run inside the sandbox with TMP and TEMP pointing to the repository's .tmp.
- No test escalation, GUI launch, build, process termination or operational data access.
- Only tests may delete their own empty temporary .exe placeholders.

## 5. Steps
| # | Step | Files | Validation | Commit message |
|---|---|---|---|---|
| 1 | Move foundation documents | documentation/, documentation/plans/ | Rename-only diff | docs: move phase 0 documents to documentation folder |
| 2 | Document local-first setup and sandbox test rules | AGENTS.md | Review exact scope | docs(agents): local-first environment and temp test artifact exception |
| 3 | Record verified register evidence | documentation/DEVELOPMENT_ROADMAP.md, this plan | Check cited lines and discovery counts | docs(roadmap): record phase 0 verification evidence |
| 4 | Add tooling and validate | requirements-dev.txt, pyproject.toml, .gitignore, this plan | compileall, unittest, pytest, ruff, mypy | build: add development tooling configuration |

## 6. Validation strategy
- Verify latest stable tool releases and Python 3.14 compatibility against PyPI.
- Run compileall and both test runners; compare against the F0-01 Windows baseline.
- Record ruff and mypy totals as debt, without fixing existing code.
- Review the final diff for prohibited directory changes and verify pushed branch state.

## 7. Risks and mitigations
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Missing .eml fixtures | Known | Six tests cannot run their intended scenarios | Report the existing errors; do not create fixtures |
| Runner discovery differences | Possible | Counts may differ | Inspect collection and report discrepancies without changing tests |
| Sandbox permissions | Possible | Tests cannot complete | Keep temporary files in .tmp; stop and report if denied |

## 8. Rollback
Keep changes isolated on chore/phase-0-tooling for review. If rollback is requested,
use new revert commits; do not rewrite published history or delete branches.

## 9. Progress
- [x] Step 1: documents moved with git mv (7d6e32a).
- [x] Step 2: agent instructions updated (696b6e0).
- [x] Step 3: register evidence recorded; recursive inventory confirms 11 of 29 files contribute cases.
- [ ] Step 4: tooling installed, validation recorded and branch pushed.

## 10. Decision log
| Date | Decision | Reason | Decided by |
|---|---|---|---|
| 2026-10-28 | Keep existing application and test code unchanged | Explicit F0-02 scope | User |
| 2026-10-28 | Run tests only inside the sandbox with repository-local temporary files | Additional step 4b | User |
