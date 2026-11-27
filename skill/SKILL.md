---
name: nps-operations-center
description: NPS Upcoming for BTS SELAM (AR, BR/Nexo, MX) from Salesforce: surveys to create, QR, exclusions, Slack cards; creates surveys after approval. Use for weekly NPS, "los NPS de la semana".
---

# NPS Operations Center — SELAM (V2-1 Upcoming read-only; V2-2 create surveys, pilot)

Use this skill when the user asks for the week's NPS (or "los NPS de la semana"), for
one day or a date range, to find sessions by client, project, facilitator or country,
to prepare #latam-nps, or for the scheduled Monday run.

This skill replaces the desktop app's Monday run. A deterministic engine (`nps_v2`,
with the certified rules of `engine/stages`) makes every decision; you only
orchestrate: run the commands, run in Salesforce **exactly** the queries the engine
prints, and present the results.

Talk to the user in the language they write in. The files the engine produces
(preview, Slack page, comparison) are in English.

## Non-negotiable rules

1. **Read-only by default.** Do not create, change or delete anything in Salesforce,
   Slack, Outlook or Box, and never post to Slack. The **only** exception is section
   8 (create surveys), and only after the user approves the exact plan code.
   Never delete anything, ever.
2. **The engine writes the queries.** Copy each `soql` as is into `salesforce_query`
   (BTS connector). Do not reformat or "improve" it, and do not write queries of
   your own to fill in data.
3. **The engine decides.** Do not apply your own judgement on eligibility,
   exclusions, surveys or language. If something looks odd, say so as an
   observation, without changing the result.
4. **On `"status": "error"`, stop.** Show the message as is, explain it in plain
   words and do not look for shortcuts. Single exception: on `ControlMismatchError`
   the data may have changed between queries; repeat the whole run **once** in a new
   folder. If it fails again, stop.
5. **Real data stays in the session.** The run folder goes in the session's
   workspace, never in a repository or anywhere else.

## How to run it

Set, once per run:

- `SKILL_DIR`: the folder that contains this `SKILL.md`.
- `RUN_DIR`: `<workspace>/nps-runs/<run-id>`, with a new, descriptive `run-id`, for
  example `V2-20261130-0915-week-30-11`. Never reuse a folder.
- The base command (Linux/macOS):

  ```bash
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$SKILL_DIR" python3 -m nps_v2 <command> ...
  ```

Every command prints JSON. Always read `status` before going on.

### 1. Selection

Turn the request into `select` arguments. If no date is given, use `--this-week`
(the standard week of today in Buenos Aires). If the request is ambiguous, ask one
question.

| Request | Arguments |
|---|---|
| "this week", "today's Monday run" | `--this-week` (window Tuesday → next Monday) |
| "the week of the 7th", "next week" | `--week-of <date>` (any day of that week) |
| "add/remove days" | also `--extend-start N` / `--extend-end N` (negative shrinks) |
| "only tomorrow", "Thursday the 3rd" | `--day <YYYY-MM-DD>` |
| "from the 1st to the 5th" | `--from <YYYY-MM-DD> --to <YYYY-MM-DD>` |
| "only Brazil" | `--country BR` (repeatable: AR, BR, MX; Brazil includes Nexo) |
| "client X", "that facilitator's sessions" | `--client`, `--project`, `--facilitator`, `--sub-type` (contains; ignores accents and case) |

```bash
... python3 -m nps_v2 select --run "$RUN_DIR" --week-of 2026-11-30
```

### 2. Projects

For each item of `queries` from the previous step (there are two: `projects` and
`projects_control`), run `salesforce_query` with its exact `soql`. Then:

```bash
... python3 -m nps_v2 capture --run "$RUN_DIR" --group projects
```

`capture` copies the responses from the session log, so you do not have to re-type
data. If it reports anything in `missing`, save the full response of that query
**by hand**, untouched, at the `save_as` path given, and repeat `capture` until
`missing` is empty.

### 3. Existing surveys

```bash
... python3 -m nps_v2 surveys --run "$RUN_DIR"
```

It checks the projects against the control. Run each query in `queries` (pairs
`survey_sets_NN` and `survey_sets_NN_control`; there may be none) and then
`capture --group survey_sets`, as in step 2.

### 4. Result

```bash
... python3 -m nps_v2 upcoming --run "$RUN_DIR"
```

With `"status": "ok"`, `outputs` holds:

- `preview_html`: the preview page (surveys to create, already created, manual review,
  excluded with reason, outside the report scope, special cases, data quality), with
  search and country tabs. `preview` is the same content as plain text (Markdown).
- `slack_html`: the Slack page (search, country tabs, one card per client with its
  sessions and QR codes, and a "Copy for Slack" button per client). Never rewrite or
  restyle it: all views come from the engine's shared UI kit.

### 5. What to show the user

1. A short table with the `summary`: surveys to create (sessions and surveys),
   already created, manual review, excluded, outside the report scope, special
   cases and data-quality notes.
2. The sessions with surveys to create (country, date, client, session, what is
   missing).
3. The special cases: say they need a personalised e-mail. The Slack page has a
   "Personalised e-mails" section with one e-mail per facilitator: the user clicks
   "Copy subject" and "Copy e-mail" and pastes them into a new Outlook message. Never
   send or draft that e-mail yourself. If a session there has no surveys yet, say so.
4. If `watchlist_configured` is `false`, say that the special-facilitator list is
   not installed and no special cases were flagged.
5. Deliver the preview page (`preview_html`) and the Slack page **as files**, never
   as text: the user must be able to open the page, not read its HTML. Use the file tool your
   environment has, in this order:
   - a tool that sends or presents files to the user (for example `SendUserFile` or
     `present_files`; copy the files to the outputs folder first if the tool needs it);
   - otherwise, publish the page as an artifact or attach it as a downloadable file.
   **Never paste the page's HTML (or the raw JSON) into the reply.** If no file tool is
   available, say so and give the file paths. Remind the user that the page opens
   best in Chrome or Edge, and that if the viewer blocks copying it opens the content
   selected for Ctrl+C.

### 6. Scheduled Monday run

A scheduled task can start this skill every Monday with nobody watching. When the
request says it is the scheduled weekly run:

- Do not ask questions. Use exactly `select --this-week`, with no filters or extra
  days, and the run id `V2-<YYYYMMDD>-weekly` (today in Buenos Aires; add `-retry` for the
  single retry).
- Follow steps 2–4 as usual. The rules above still apply: read-only, and stop on any
  error (with the single `ControlMismatchError` retry).
- End with the step 5 summary and deliver the preview page and the Slack page. If the run
  stopped, say so first, with the error and the step where it happened.

More days, another country or a filter are never added to the scheduled run: the
user asks for them in a normal (manual) run, with the arguments of step 1.

### 7. Parallel run (while the desktop app is still in use)

If the user attaches the desktop app's `selam_worklist.csv` for the same week:

```bash
... python3 -m nps_v2 compare --run "$RUN_DIR" --desktop <path of the attached CSV>
```

Deliver `compare_html` (the comparison page) as a file. "Only on desktop" differences
come explained by V2; "Only in V2" ones (marked "To check") are usually sessions
created or changed after the report e-mail: suggest checking them in Salesforce,
without writing anything.

### 8. Create surveys (V2-2 — pilot)

Only when the user **explicitly asks to create the surveys** of a finished Upcoming
run (step 4). During the pilot, create only for the sessions the user chooses
(`--only <project id>`, repeatable). The scheduled Monday run never creates anything.

1. **Plan:** `plan --run "$RUN_DIR" [--only <project id> ... | --exclude <project id> ...]`
   (`--only` keeps just those sessions; `--exclude` leaves those out; never both).
   Deliver `plan_html` as a file and show the summary: the list of sessions and
   surveys to create, so the user can check them against Salesforce. Ask the user to
   approve by replying with the `approval_code`. Do not suggest approving; wait for
   the user. If the user wants a session removed or added, run `plan` again and
   deliver the new page (the code changes).
2. **Approve:** only with the code the user typed:
   `approve --run "$RUN_DIR" --code <code>`. A different code is an error: show the
   plan again. Then run the re-check query exactly as printed and
   `capture --run "$RUN_DIR" --group creation_recheck`.
3. **Execute, one call at a time:** `execute --run "$RUN_DIR"` prints one `call`
   (`tool` + `input`). Run that connector tool with **exactly** that input — never
   edit, add or reorder fields — then `record --run "$RUN_DIR"`. `record` prints the
   next `call`; repeat until there is none. Never run a call twice and never run a
   write that the engine did not print. If `execute` says `plan_changed`, nothing was
   written: deliver the new plan and ask for approval of the new code.
4. **If the run stops** (`run_status: failed`), do not retry and do not write
   anything else. Go to step 5 and show the user the error.
5. **Reconcile:** `reconcile --run "$RUN_DIR"`; run the printed queries exactly,
   `capture --run "$RUN_DIR" --group creation_after`, then `reconcile` again.
   Deliver as files: `result_html`, `creation_log` (Excel), and the refreshed
   `slack_html` with the new links and QR codes. Summarise the counts (created,
   already existed, partial, failed, not run) and any notes.

If `record` cannot find the result in the session log, save the tool's result
exactly as returned to a file and run `record --run "$RUN_DIR" --response-file <file>`.

## Common problems

| Message | Meaning | What to do |
|---|---|---|
| `ControlMismatchError` | Saved data does not match the Salesforce counts | Repeat the whole run once in a new folder |
| `ReaderError ... done is not true` or `may be truncated` | Incomplete or too large a response | Narrow the selection (fewer days or one country) |
| `RunFolderError ... Missing response` | A response was not saved | Run that query and `capture` (or save it by hand) |
| `run 'surveys' again` | The survey queries do not match the saved projects | Repeat step 3 |
| `RegistryError` / `WatchlistError` / `ReasonTextsError` / `RecipeError` | Invalid skill configuration | Stop and say the skill must be reinstalled |
| `does not match the current plan` | The approval code is not the plan's code | Show the plan again; ask for approval |
| `no '...' call with exactly the printed input` | The tool was not run, or was run with a different input | Run it exactly as printed, then `record` again |
| `run_status: failed` | A step failed; the run stopped | No retries: `reconcile` and report |

## What is in this skill

`nps_v2/` (V2 engine), `engine/` (only the certified stages it uses: normalize,
business_rules, worklist and the renderer helpers), `config/` (business rules,
country registry, report scope, English rule labels; `config/v2/watchlist.json` only
if the special-case list was installed) and `BUILD_INFO.json` (version, commit and
fingerprints of every file). Built with `python -m scripts.build_skill` from the
repository.
