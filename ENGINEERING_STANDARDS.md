# Engineering Standards — BTS SELAM NPS Operations Center

Status: active from Phase 0 (development toward 1.0.3 and 1.1.0).
Audience: human developers and coding agents.

## 1. Quality goals, in priority order

1. **Correctness and operational safety.** The Monday run must produce the right worklist
   or fail visibly. Silent partial results are the worst possible outcome.
2. **Maintainability.** Code is read far more than written: clear names, small units,
   one responsibility each.
3. **Extensibility.** New countries, report types or modules (Results, Data Quality,
   Follow-up, Salesforce) must be added by extension and configuration, not by editing
   many unrelated files.
4. **Testability.** Every behavior that matters can be exercised without the UI, without
   OneDrive and without real data.
5. **Usability.** The UI tells the operator exactly what happened and what to do next.
6. **Performance.** Adequate for weekly volumes; optimize only with a measurement.

When goals conflict, the higher one wins.

## 2. Design principles applied to this codebase

| Principle | What it means here |
|---|---|
| Single Responsibility | A module/class has one reason to change. Parsing, normalizing, classifying, windowing, aggregating and rendering are separate units. |
| Open/Closed | Adding a country, report type, match type or output format should mean adding a class or a config entry, not editing `if/elif` chains. |
| Liskov | Implementations of an interface (e.g. renderers, rule matchers) are interchangeable without callers checking concrete types. |
| Interface Segregation | Small protocols (`typing.Protocol`) per need; the UI depends on narrow controller methods, not on engine internals. |
| Dependency Inversion | Application services receive collaborators (config, clock, filesystem roots) through constructors; no hidden globals or import-time path constants in new code. |
| DRY / single source of truth | One implementation per business concept. Duplication of *rules* is a defect; duplication of trivial code is acceptable if abstraction would obscure intent. |
| KISS / YAGNI | No abstraction without a current, concrete second use or a testability need. |
| Fail closed | Unknown or ambiguous data blocks the run or goes to REVIEW. |

## 3. Pattern catalog (use only when the trigger applies)

| Pattern | Trigger in this project | Candidate location |
|---|---|---|
| Strategy | Interchangeable algorithms selected by config | rule match types (`contains`, `word`, `regex`, `starts_with`); weekly window policy |
| Pipeline / Chain of stages | Ordered transformations with a common contract | parse -> normalize -> classify -> window -> worklist |
| Adapter | Isolating external formats or systems | Salesforce `.eml` HTML reader; future Salesforce API, Smartsheet |
| Repository | Persisting/reading domain state | weekly manifests, sessions, run history |
| Factory / Registry | Creating implementations from config keys | renderers, matchers, report parsers |
| Value Object | Immutable domain values with validation | `WeeklyWindow`, `ProjectId`, `ReportSource` |
| Result object | Operations that can partially fail | weekly processing result with per-source outcomes |
| Template Method | Only if several renderers share a fixed skeleton | output renderers (prefer composition first) |

Anti-patterns to avoid: god classes, deep inheritance, singletons/global state, business
logic in Qt widgets, stringly-typed statuses scattered across modules (use `Enum`),
broad `except Exception` that swallows errors, printing instead of logging in `engine/`.

## 4. Python conventions

- Python 3.14. `from __future__ import annotations` in every module.
- Type hints on all public functions, methods and dataclass fields. New code must pass
  `mypy` on the modules it touches (adoption is incremental, module by module).
- Formatting and linting with `ruff` (format + lint). No unused imports or variables.
- Naming: `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants.
  Names describe intent (`calculate_weekly_window`, not `calc`).
- Data: `@dataclass(frozen=True)` for value objects; `Enum`/`StrEnum` for statuses and
  decisions; avoid passing raw `dict[str, Any]` across module boundaries in new code.
- Paths: `pathlib.Path` only, resolved through `engine/paths.py`.
- Encoding: always explicit `encoding="utf-8"` (or `utf-8-sig` for CSV read).
- Errors: one exception hierarchy per package (`NPSError` base); raise specific
  exceptions with actionable messages; never swallow exceptions silently.
- Logging: `logging` module in `engine/`; `print` only in CLI entry points.
- Functions: aim for < 40 lines and a single level of abstraction; extract otherwise.
- Comments explain *why*, not *what*. Docstrings on public units (Google style).
- Language: code, identifiers, docstrings and commit messages in English. User-facing
  strings follow the existing UI language (English).

## 5. Module boundaries

- `app/` depends on `app/controllers/ui_controller.py` only for backend access.
- `engine/stages/*` are pure transformations: input data + config -> output data.
  They do not move files, write outputs, read environment variables or know about TEST/PROD.
- File lifecycle, manifests and sessions belong to application services, not stages.
- Configuration is loaded once per operation and passed explicitly (no import-time loads
  in new code).

## 6. Testing standards

- Runner: `unittest` today; `pytest` introduced in Phase 0 (it runs existing `unittest`
  tests unchanged). Coverage measured with `coverage`/`pytest-cov`.
- Every file named `test_*.py` must contain real test cases. Scripts that only print go
  to `tests/manual/` with a different prefix or are converted.
- Test pyramid:
  - Unit: stages, rules, window policy, renderers (fast, no filesystem when possible).
  - Characterization ("golden master"): full pipeline on synthetic `.eml` fixtures;
    outputs compared against approved snapshots. Mandatory before any refactor.
  - Integration: controller + session + lifecycle with temporary directories.
  - UI: smoke tests only (construction, signal wiring); no pixel assertions.
- Fixtures: synthetic, versioned under `tests/fixtures/`. They must reproduce the real
  Salesforce HTML structures (header variants, `Sum` suffix, Billing Office as `th`
  or `td`, grouped rows) with invented clients, projects and people.
- Real-data acceptance: optional, local only, in the git-ignored folder
  `local_acceptance/`. Never committed.
- Tests must not depend on execution order, wall-clock time (inject a clock), network,
  OneDrive or the operational installation.
- A bug fix starts with a failing test that reproduces it.

## 7. Configuration standards

- Every config file has a `version` field and is validated on load with clear errors.
- No duplicated settings across files (one owner per setting).
- Changes to `business_rules.json` are business changes: they require explicit approval,
  a test for each affected case and a CHANGELOG entry.

## 8. Versioning, branching and commits

- Git tooling: coding agents perform the Git operations their task requires (see
  AGENTS.md section 5a). When an agent cannot, the human performs them in GitHub Desktop.
  The human does not use the Git command line.

- SemVer. PATCH (`1.0.x`): fixes, no new capability. MINOR (`1.x.0`): refactors or
  backward-compatible capabilities. MAJOR: incompatible changes (e.g. V2 lifecycle).
- Branches: `main` (certified releases only, tagged `vX.Y.Z`), `develop` (integration),
  `feature/*`, `fix/*`, `refactor/*`, `chore/*`, `test/*` created from `develop`.
  Hotfixes for production: `hotfix/*` from `main`, merged back into `main` and `develop`.
- Conventional Commits: `type(scope): imperative summary` (scope = module, e.g.
  `fix(orchestrator): report failed sources as run failure`).
- Pull requests target `develop`; `develop` -> `main` only through a release PR that
  satisfies the release section of the Definition of Done.

## 9. Code review checklist

- Does the change do exactly what the task asked, and nothing more?
- Is behavior preserved where it should be (golden master unchanged)?
- Are responsibilities in the right layer? Any business logic in UI or stages doing I/O?
- Any new duplication of a business concept?
- Are errors visible to the operator? Any silent fallback introduced?
- Tests: added/updated, meaningful assertions, no real data.
- Names, types, docstrings and logs are clear.
- Documentation and CHANGELOG updated when behavior or operation changed.
