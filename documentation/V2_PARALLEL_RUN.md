# V2-1 Parallel Run — Operator Runbook

Status: active from Monday 2026-11-30 until V2-1 sign-off. Owner: product owner (PE).

V2-1 (the Claude skill `nps-upcoming-selam`) must prove, on real weeks, that it gives
the same worklist as desktop v1.0.2. During the parallel run the desktop app remains
the operational source; V2 is read-only and its outputs are compared, not used.

## 1. One-time setup

1. Build the skill from an up-to-date clone (or ask Claude to build it in the session):

   ```powershell
   python -m scripts.build_skill --out dist\skill --watchlist <path outside the repo>\watchlist.json --zip
   ```

   `dist/` is git-ignored. The watch-list (facilitators who need a personalised
   e-mail) holds real names and must live outside the repository; its format is
   `config/v2/watchlist.example.json`.
2. Upload `dist/skill/nps-upcoming-selam.zip` in Claude's skills settings.
3. Check that the BTS connector (Salesforce) is enabled in the Claude session.
4. Optional: a scheduled task runs V2 every Monday on its own ("Run the scheduled weekly
   NPS Upcoming"; the skill uses `select --this-week`). Each run opens its own session
   with the summary, `preview.md` and the Slack page.

## 2. Each Monday

| Step | Desktop v1.0.2 | V2 (Claude) |
|---|---|---|
| 1 | Run as usual after the subscribed reports arrive (~13:00 UTC). | In the same hour, ask Claude (in English or Spanish): "Run this week's NPS Upcoming", or open the session of the scheduled run. Claude follows the skill: select → queries → capture → surveys → upcoming. |
| 2 | Keep `selam_worklist.csv` of the weekly run. | Review `preview.md` and the Slack page. Do **not** use them operationally yet. |
| 3 | — | Attach the desktop `selam_worklist.csv` and ask Claude to compare: `python -m nps_v2 compare --run <run> --desktop selam_worklist.csv`. |
| 4 | — | Explain every remaining difference (section 3) and record the run (section 4). |

Running V2 as close as possible to the report e-mail time minimises differences caused
by Salesforce changes after the report was sent.

## 3. Explaining differences

| Where | Typical cause | How to confirm |
|---|---|---|
| Only on desktop, "V2: excluded / manual review / outside the report scope" | Data changed after the report, or report-scope rule differs (D-V2-1) | Read the reason in `compare.md`; check the record in Salesforce |
| Only on desktop, "Not in Salesforce for this selection" | Record deleted, or start date / billing country changed after the report | Open the project in Salesforce (history) |
| Only in V2, "To check" | Project created or modified after the report was sent | Check `CreatedDate` / `LastModifiedDate` in Salesforce |
| Same session, different survey state | Survey created between the report and the V2 run | Survey Set `CreatedDate` |

A difference is **unexplained** when none of the above holds. Any unexplained
difference blocks sign-off until it is understood and, if it is a V2 defect, fixed.

## 4. Run log

Keep one row per Monday (no client names; counts only):

| Monday | V2 run id | Matching | Only desktop | Only V2 | Unexplained | Notes |
|---|---|---|---|---|---|---|
| 2026-11-30 | | | | | | |
| 2026-12-07 | | | | | | |
| 2026-12-14 | | | | | | |

## 5. Exit criteria (V2-1 sign-off)

- 2–3 consecutive Mondays with **0 unexplained differences**.
- At least one run with a non-standard selection (single day or facilitator search).
- The Slack page used to fill a test canvas without manual corrections.
- Product-owner sign-off recorded in the V2-1 plan decision log.

After sign-off: V2-2 (create surveys with preview, approval and re-check) can start,
once Salesforce write permission and the audit store (D-V2-2) are settled.

## 6. If something fails

Claude must stop on any engine error and show the message (see the skill's
"Common problems"). Report persistent errors with the run id; the run folder
stays in the Claude session and is never committed.
