---
name: nps-upcoming-selam
description: Runs the BTS SELAM NPS Upcoming (Argentina, Brazil with Nexo, Mexico) straight from Salesforce, read-only - which NPS and facilitator surveys still need to be created, which already exist (with QR and links), exclusions and manual reviews with their reason, special cases, and the page to copy session cards into the Slack canvas. Use when asked for the week's NPS (or "los NPS de la semana"), for one day or a date range, to find sessions by client, project, facilitator or country, or to prepare #latam-nps.
---

# NPS Upcoming SELAM (V2-1, read-only)

This skill replaces the desktop app's Monday run. A deterministic engine (`nps_v2`,
with the certified rules of `engine/stages`) makes every decision; you only
orchestrate: run the commands, run in Salesforce **exactly** the queries the engine
prints, and present the results.

Talk to the user in the language they write in. The files the engine produces
(preview, Slack page, comparison) are in English.

## Non-negotiable rules

1. **Read-only.** Do not create, change or delete anything in Salesforce, Slack,
   Outlook or Box. Do not post to Slack. (Creating surveys and publishing come in
   V2-2 and V2-3.)
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

Turn the request into `select` arguments. If no date is given, use **today in Buenos
Aires** for the standard week. If the request is ambiguous, ask one question.

| Request | Arguments |
|---|---|
| "this week", "Monday's NPS" | `--week-of <date>` (any day of that week; window Tuesday → next Monday) |
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

- `preview.md`: the preview (surveys to create, already created, manual review,
  excluded with reason, outside the report scope, special cases, data quality).
- `slack_html`: the Slack page (session cards with QR, one "Copy for Slack" button
  per client).

### 5. What to show the user

1. A short table with the `summary`: surveys to create (sessions and surveys),
   already created, manual review, excluded, outside the report scope, special
   cases and data-quality notes.
2. The sessions with surveys to create (country, date, client, session, what is
   missing).
3. The special cases: say they need a personalised e-mail.
4. If `watchlist_configured` is `false`, say that the special-facilitator list is
   not installed and no special cases were flagged.
5. Deliver `preview.md` and the Slack page with the file-sending tool (so they can
   be viewed in the panel). Remind the user that if the viewer blocks copying, the
   page opens the content selected for Ctrl+C, and that Chrome or Edge copy directly.

### 6. Parallel run (while the desktop app is still in use)

If the user attaches the desktop app's `selam_worklist.csv` for the same week:

```bash
... python3 -m nps_v2 compare --run "$RUN_DIR" --desktop <path of the attached CSV>
```

Deliver `compare.md`. "Only on desktop" differences come explained by V2; "Only in
V2" ones (marked "To check") are usually sessions created or changed after the
report e-mail: suggest checking them in Salesforce, without writing anything.

## Common problems

| Message | Meaning | What to do |
|---|---|---|
| `ControlMismatchError` | Saved data does not match the Salesforce counts | Repeat the whole run once in a new folder |
| `ReaderError ... done is not true` or `may be truncated` | Incomplete or too large a response | Narrow the selection (fewer days or one country) |
| `RunFolderError ... Missing response` | A response was not saved | Run that query and `capture` (or save it by hand) |
| `run 'surveys' again` | The survey queries do not match the saved projects | Repeat step 3 |
| `RegistryError` / `WatchlistError` / `ReasonTextsError` | Invalid skill configuration | Stop and say the skill must be reinstalled |

## What is in this skill

`nps_v2/` (V2 engine), `engine/` (only the certified stages it uses: normalize,
business_rules, worklist and the renderer helpers), `config/` (business rules,
country registry, report scope, English rule labels; `config/v2/watchlist.json` only
if the special-case list was installed) and `BUILD_INFO.json` (version, commit and
fingerprints of every file). Built with `python -m scripts.build_skill` from the
repository.
