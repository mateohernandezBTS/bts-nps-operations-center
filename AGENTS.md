# AGENTS.md — BTS SELAM NPS Operations Center

Operational contract for coding agents working in this repository.
Read this file completely before any task. Detailed rules live in:

- `documentation/ENGINEERING_STANDARDS.md` — design, code and test standards
- `documentation/DEFINITION_OF_DONE.md` — completion checklist (mandatory)
- `documentation/DEVELOPMENT_ROADMAP.md` — phases, scope and known-issue register (NPS-xxx)
- `documentation/plans/PLAN_TEMPLATE.md` — execution plan format for multi-step work

## 1. Product in one paragraph

Windows desktop application (Python 3.14, PySide6) that ingests Salesforce NPS report
emails (`.eml`) captured by Power Automate, applies deterministic business rules, and
produces the weekly NPS worklist (Excel + Slack-ready HTML) for the SELAM region.
Version 1.0.2 is certified and used in production every Monday. It must never break.

## 2. Repository map

```text
app/            PySide6 UI. Presentation only. No business rules.
  controllers/  UIController (adapter to engine) and OperationWorker (QThread)
  views/        Screens. Each screen composes widgets.
  widgets/      Reusable visual components.
engine/         Application services and deterministic processing.
  stages/       Pipeline stages: email_parser, normalize, business_rules, worklist, slack_output
  paths.py      THE ONLY place allowed to resolve filesystem paths.
config/         External JSON configuration (business rules, sources, schedule, outputs).
packaging/      PyInstaller build and release validator.
tests/          Automated tests and TEST data root (generated data is git-ignored).
documentation/  Product, operation and engineering documentation.
```

Layering (dependencies only point downward):

```text
UI (app/views, app/widgets)
  -> UIController (app/controllers)
    -> NPSApplicationController (engine/application_controller.py)
      -> SessionManager / weekly pipeline (engine/*)
        -> stages (engine/stages/*) and config (config/*)
```

## 3. Hard prohibitions (never, unless the task text explicitly overrides the specific item)

1. Never read from, write to, run, move or delete anything in the operational installation
   `..\BTS SELAM NPS Operations Center\` or any OneDrive `NPS_AUTOMATION` folder.
2. Never kill processes (`Stop-Process`, `taskkill`, etc.) and never delete `.exe` files.
   If a running process blocks a file, STOP and ask the human to close it.
3. Never commit directly to `main` or `develop`, except when the task explicitly asks you
   to create the `develop` branch or a release tag. Work on the branch named in the task.
4. Never force-push, rewrite published history (`rebase`, `reset --hard`, `commit --amend`
   on pushed commits), or delete branches or tags. Push only what the task asks you to push.
5. Never change business behavior (anything in `config/business_rules.json`, eligibility,
   weekly window semantics, exclusion/review decisions, output columns) unless the task
   explicitly says so. Refactors must be behavior-preserving.
6. Never add real operational data to the repository: no real `.eml`, no Salesforce exports,
   no client/project/person names from production, no secrets. Fixtures must be synthetic.
7. Never add a production dependency without explicit approval in the task.
8. Never run `packaging/build_release.py` or PyInstaller unless the task asks for a build.
9. Never fix issues outside the task scope, even if you notice them. Report them instead
   (reference the NPS-xxx id from the roadmap register if it exists).

## 4. Environment and commands

Two execution environments exist:
- **Codex cloud (Linux container, preferred for code work).** Dependencies are installed
  by the environment setup script. Do not install anything else. Never attempt PyInstaller
  builds or Windows packaging here. In the cloud, ALWAYS run Python through the wrapper
  `/workspace/.setup/bts/headless.sh` (it uses `.venv`, sets the headless Qt variables and
  PYTHONPATH). Example: `/workspace/.setup/bts/headless.sh -m unittest discover -s tests -p "test*.py"`.
  GUI smoke check: `/workspace/.setup/bts/headless.sh /workspace/.setup/bts/smoke.py`.
  Cloud tasks start from `develop` (the repository default branch).
- **Local Windows clone** (`C:\dev\nps-operations-center`, outside OneDrive). Used for
  Windows-only work: packaging, packaged E2E, visual UI checks.

```bash
# environment (local Windows only; cloud is preinstalled)
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# validation (always run before declaring a task done; in the cloud replace
# `python` with /workspace/.setup/bts/headless.sh)
python -m compileall -q app engine packaging
python -m unittest discover -s tests -p "test*.py"   # current baseline runner

# run the application from source
python -m app.nps_operations_center
```

Notes:
- Always run modules with `python -m ...` from the root. `python app/x.py` breaks imports.
- Tests must be platform-neutral (Linux and Windows). Platform-specific assertions are
  defects (NPS-018) unless explicitly marked and skipped on other platforms.
- Some tests print controlled failure messages ("PIPELINE FINALIZADO CON ERROR"). Judge
  success only by the final test-runner result.
- Network access may be disabled. If you need a package, stop and state exactly which
  package and version.

## 5. How to work

1. Restate the goal, scope and non-scope in 3–6 lines before acting.
2. Multi-step or risky work: write an execution plan using
   `documentation/plans/PLAN_TEMPLATE.md` and wait for approval if the task says
   "plan only".
3. Prefer the smallest change that fully solves the task. No speculative abstractions.
4. Characterization first: before refactoring a module, make sure tests pin its current
   behavior. If they do not exist, create them first in a separate commit.
5. Commit in small, coherent steps using Conventional Commits (`fix:`, `feat:`,
   `refactor:`, `test:`, `docs:`, `chore:`, `build:`). Report every commit hash.
6. Stop and ask when: a business decision is needed, a prohibition would be crossed,
   tests fail for reasons unrelated to the task, or the task is ambiguous.

## 5a. Git operations

- You perform the Git operations the task requires: create/switch branches, stage,
  commit, tag, and push the task branch (pushing needs network approval).
- In Codex cloud, commit your work on the task branch inside the environment; publishing
  (push / pull request) is done through the Codex interface. Pull requests target `develop`.
- Before editing files, check `git branch --show-current`. If you are not on the task
  branch, switch to it or create it from the base branch named in the task.
- If a Git operation fails or cannot be done by you (authentication or credential prompt,
  network denied, locked files, merge conflicts needing a decision), STOP. Do not try
  workarounds. Report it under HUMAN ACTIONS with exact GitHub Desktop steps.
- The human never uses the Git command line. Every human Git action (clone, switch
  branch, publish/push, pull request, merge, tag) is done in GitHub Desktop, so write
  instructions as GitHub Desktop menu paths (e.g. "Branch > New branch...",
  "Repository > Push", "History > right-click commit > Create Tag...").

## 6. Architecture rules (summary — details in ENGINEERING_STANDARDS.md)

- UI never imports from `engine/` except through `app/controllers/ui_controller.py`.
- All filesystem paths go through `engine/paths.py`. No `Path(__file__)` elsewhere in
  `app/` or `engine/`.
- Business rules live in `config/*.json` and `engine/stages/business_rules.py` only.
- One source of truth per concept (e.g. the weekly window must be computed in exactly
  one place once NPS-007 is resolved).
- TEST and PRODUCTION must stay isolated (paths, sessions, logs, outputs).
- Fail closed: ambiguous or unparseable input must block or go to REVIEW, never silently
  become eligible or be silently dropped.

## 7. Required final report (every task)

```text
SUMMARY        what was done, in 3–8 lines
BRANCH/COMMITS branch name, commit hashes and messages, what was pushed
FILES CHANGED  path — reason
BEHAVIOR       "unchanged" or exact description of the intended change
VALIDATION     commands executed and their final results (counts)
RISKS          anything uncertain or not verified
OUT OF SCOPE   issues noticed but not touched (with NPS-xxx ids)
HUMAN ACTIONS  "none", or exact GitHub Desktop steps the human must perform
```
