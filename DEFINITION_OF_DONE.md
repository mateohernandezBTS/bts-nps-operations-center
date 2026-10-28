# Definition of Done

A task or release is not done until every applicable item is checked.
Agents must include this checklist, with results, in their final report.

## A. Task level (every branch / PR)

- [ ] Scope matches the task exactly; out-of-scope findings listed, not fixed.
- [ ] Work is on the correct branch; the agent ran no Git write operations.
- [ ] Behavior: preserved (refactor) or changed exactly as specified (fix/feature).
- [ ] Bug fixes include a test that failed before the fix and passes after it.
- [ ] Refactors: characterization / golden-master tests pass with identical outputs.
- [ ] `python -m compileall -q app engine packaging` passes.
- [ ] Full test suite passes; reported with counts (run / passed / failed / errors / skipped).
- [ ] `ruff check` and `ruff format --check` pass on changed files (once tooling exists).
- [ ] `mypy` passes on modules touched, if the module is already in the mypy scope.
- [ ] No real data, secrets or operational files added (`git status` and diff reviewed).
- [ ] No hard prohibition from `AGENTS.md` crossed.
- [ ] Documentation updated if operation, configuration or architecture changed.
- [ ] Changes committed with Conventional Commits (by Codex; by the human in GitHub Desktop
      only when Codex cannot); final report delivered in the AGENTS.md format.
- [ ] Human review completed (architect review + `/review` against `develop`).

## B. Release level (`develop` -> `main`)

- [ ] All task-level items satisfied for every merged change.
- [ ] Version updated consistently: `VERSION.md`, `CHANGELOG.md`, UI label,
      `packaging/windows_version_info.txt`.
- [ ] Documentation consistent (README, ARCHITECTURE, WEEKLY_OPERATION, ROADMAP).
- [ ] Release build produced by `packaging/build_release.py`; `validate_release.py` passes.
- [ ] Packaged TEST end-to-end run passes on synthetic fixtures.
- [ ] Parallel run: the candidate and the current production version process the same
      real weekly reports (locally, outside the repo); outputs compared and differences
      explained and approved.
- [ ] Rollback artifact of the previous version preserved.
- [ ] Explicit approval from the product owner (Mateo) recorded in the release PR.
- [ ] Tag `vX.Y.Z` created on `main` after merge and pushed (by Codex; otherwise in GitHub
      Desktop: History > right-click the merge commit > Create Tag..., then Push).
- [ ] Promotion to the operational installation done manually by the product owner,
      preserving `input/`, `output/`, `logs/`, `runtime/` and the operational `config/`.
