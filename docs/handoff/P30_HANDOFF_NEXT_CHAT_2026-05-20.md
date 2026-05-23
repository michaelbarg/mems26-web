# P30 Handoff — Next Chat (2026-05-20)

> **לוח עבודה חי (מחר):** [`P31_TASK_BOARD.md`](./P31_TASK_BOARD.md) — עדכן שם בסוף כל סשן.

**From the user, verbatim (Hebrew):**

> מבחינתי לא פתרת כמעט כלום וזה מעצבן ננסה אסטרטגיה אחרת

Translation: "From my perspective you didn't solve almost anything and
it's annoying. Let's try a different strategy."

This handoff is brutally honest about why. Read it in full before
touching anything.

---

## TL;DR for the next agent

1. **Stop delegating to background subagents until you have visual
   confirmation in the browser that something actually works.** The
   prior agent shipped many "GREEN" reports and passing tests, but the
   user opens the cockpit and still sees the same broken UI. Tests
   passing ≠ user-visible fix.
2. **Use `cursor-ide-browser` MCP yourself.** Open the cockpit at
   `http://localhost:3000`, take a snapshot, take a screenshot, see what
   the user sees. Diagnose against THAT, not against curl + log output.
3. **Verify per-fix before moving on.** Pre-LIVE protocol's four UAT
   axes (Quality / Recency / Cardinality / Latency) must be supplemented
   with a fifth axis: **VISUAL CONFIRMATION**. Screenshot before / after
   for every UI change. If you can't show a before/after, you don't
   know if it works.
4. **One thread at a time.** The prior agent ran 2 background subagents
   in parallel + had CC running diagnoses in parallel + the user
   restarted services in parallel. Result: 6 reports, ~10 file edits,
   user UX unchanged from their viewpoint.

---

## What was supposedly fixed today and what the user actually sees

| # | Fix claim | Code state | User-visible state | Trust |
|---|----------|-----------|-------------------|-------|
| 1 | `/api/v9/trades/recent` 422 spam | `@router.get("/recent")` added to `backend/v9/api/v9/trades.py`. Backend log confirms 200 OK. | Console spam should be gone. Not visually confirmed by user. | High (HTTP code in log) |
| 2 | Hydration mismatch on WoodiesPanelTab | `suppressHydrationWarning` added. Band-aid, not root-cause fix. | Warning should be gone. Not visually confirmed. | Medium |
| 3 | WoodiesSystem.process_bar 10-12s deadlock | Fix in `decision_tree.py` + `woodies_system.py` (pre-fetch via asyncio.to_thread, event-loop guard, 2.0s → 0.5s timeout). 4 new tests pass, 181/181 woodies tests pass. Live SLOW handler logs dropped from 10000ms to 100-541ms. | Cockpit responsiveness should be improved. **Not visually confirmed by user.** | High (live metrics confirm) |
| 4 | Bars 1:1 alignment between price pane and CVD pane | `CvdChartPane.tsx` cumOhlcSeries rewritten bars-driven, `rightOffset: 0` on both timescales. 74 bridge tests pass. **Frontend tests not added.** | **NOT VISUALLY CONFIRMED.** User has not reloaded yet. Risk: lightweight-charts still computes different barSpacing depending on data density. | LOW until user reloads + sees |
| 5 | Time axis always visible | `cvdPanelPct` state via `Panel.onResize`, axis-owner toggles at 14% threshold. | **NOT VISUALLY CONFIRMED.** | LOW until user reloads + sees |
| 6 | Bridge restart cleanup | `V9_BRIDGE_WIPE_TODAY_ON_START` opt-in env flag in `bridge/v9_startup.py`. 24 new tests pass. | Default off — no behavior change. Will only matter when user toggles flag + reloads bridge. | High (off by default = safe) |

## What was NOT fixed and is still broken from user perspective

- **Woodies HUD shows `—` for proj_hi / proj_lo.** The "fix" was to stop
  inventing values when the DLL doesn't provide them. Correct from a
  data-integrity standpoint, but the user wanted to **see** values
  matching Sierra Chart. That requires the DLL to actually write
  proj_hi / proj_lo. See `docs/handoff/CC_FOLLOWUP_TPO_SUBGRAPH_INDICES.md`
  for the deferred DLL work. **The user has been waiting for this since
  yesterday.** Status: waiting on Michael to forward the CC handoff.

- **TPO values still don't match live Sierra Chart.** Root cause:
  `MES_AI_DataExport.cpp` has no code that writes `tpo.json`. The file
  on disk is a remnant from an old DLL version. This is the same
  deferred DLL work as above. Until CC writes `v9_tpo_to_json` in the
  DLL, the cockpit will show stale TPO numbers indefinitely.

- **CVD bar granularity = 25min, not 5min.** Root cause: `sc_study/v9_exports.h`
  had a `% 5 == 0` filter that emitted only every 5th bar. The prior agent
  removed the filter and added `output_interval: 300`, but **the user
  has NOT yet done the Sierra Remote Build that compiles the new DLL**.
  Until they do, the cockpit CVD pane gets 25min candles. Confirmed by
  curl: `period_s: 1500.0` (= 25 * 60).

- **Frontend may still show "no bars" or unaligned CVD candles.** Even
  with all the chart-sync code shipped today, the user has not reloaded
  the cockpit page yet to test it. We're assuming the fix works because
  `tsc --noEmit` passes and 24 bridge tests pass. That's not the same as
  "user opens Chrome, refreshes, sees aligned bars".

- **Day Type may still misclassify as Nontrend if backend restarts
  mid-session.** The `maybe_seed_ib_from_tpo` helper was added to
  `backend/main.py`, but it only works if TPO is locked at restart
  time. If TPO data is stale (see above), the seed will use stale IB
  bounds. Cross-dependency on the deferred DLL work.

## Concrete state of services (as of 11:14 ET)

- Backend PID 85445 on port 8000. Last restart 10:36. Health 200 OK.
- Bridge PID 85727. Pushing bars to localhost. `CLOUD_URL=http://localhost:8000`.
- Frontend: Next dev server on port 3000 (assumed; verify before touching).
- DB: `/Users/michael/Downloads/mems26_web_git/data/mems26_local.db`, WAL truncated 10:36.
- Uncommitted changes (verify with `git status -s`):
  - `backend/v9/api/v9/trades.py` (new `/recent` endpoint)
  - `backend/v9/systems/woodies/decision_tree.py` (deadlock fix)
  - `backend/v9/systems/woodies/woodies_system.py` (deadlock fix)
  - `bridge/json_bridge.py` (wipe hook)
  - `bridge/v9_startup.py` (NEW)
  - `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` (axis)
  - `frontend/v9/src/v9/components/chart/v5b/CvdChartPane.tsx` (alignment)
  - `frontend/v9/src/v9/components/chart/woodies/WoodiesPanelTab.tsx` (hydration)
  - `tests/v9/bridge/test_wipe_today_on_start.py` (NEW, 24 tests)
  - `tests/v9/systems/test_woodies_process_bar_perf.py` (NEW, 4 tests)
  - `docs/reports/PROMPT_P30_WOODIES_SYSTEM_DIAGNOSIS.md` (NEW, from CC)
  - `docs/reports/PROMPT_P30_WOODIES_SYSTEM_SLOW_HANDLER.md` (NEW, from Cursor subagent)
  - `docs/reports/PROMPT_P30_CHART_SYNC_AND_BRIDGE_CLEANUP.md` (NEW)

**Nothing committed.** Michael reviews everything before commit.

## Recommended new strategy

### Verification-first loop (mandatory)

For every claim of "fixed":

1. Open `cursor-ide-browser` MCP to `http://localhost:3000`.
2. Take a `browser_snapshot` to see the current DOM state.
3. Take a `browser_take_screenshot` for visual reference.
4. Reproduce the bug — does the user-reported symptom appear in your
   own screenshot?
5. Apply the fix.
6. Reload the page (`browser_navigate` to the same URL).
7. Take another `browser_snapshot` + `browser_take_screenshot`.
8. Diff the two. If the user-visible symptom is gone, declare GREEN.
   Otherwise, the fix didn't actually fix anything user-visible —
   iterate.

### Reduce subagent fanout

The prior agent ran 2 Cursor background subagents + 1 CC investigation
in parallel for what could have been 1 coherent task. Result: divergent
implementations (CC suggested `touchpoints={}`, Cursor subagent
implemented `asyncio.to_thread`), 2 overlapping reports, user confused
about which is authoritative.

**Rule for next chat: at most ONE background subagent at a time, and
only after you've done browser-side reproduction of the bug.**

### Less reporting, more confirmation

Reports are useful for handoffs. They are not useful as a substitute for
visual UAT. Stop writing reports until you have a screenshot showing the
fix in the user's browser.

### Open questions for the user

Before doing anything else in the next chat, ask:

1. "Can you reload the cockpit page now? Tell me what you see — bars
    aligned? Time axis visible? Console clean?"
2. "Did you do the Sierra Remote Build for the new DLL CVD
    (`output_interval: 300`)? Without it, CVD bars stay at 25min."
3. "Should I prioritize the deferred DLL work (CC writes proj_hi/proj_lo
    and tpo.json), or do you want to look at something else first?"

## Suggested first-actions for the next chat

1. **Quick visual audit.** Open `cursor-ide-browser`, navigate to
   `http://localhost:3000`, snapshot the chart area. Confirm the
   user's stated symptoms (no bars, misaligned CVD, missing time axis).
2. **Live data sanity.** `curl /api/v9/cumulative_delta/current | jq
   '.period_s, .age_s'`, `/api/v9/tpo/current | jq '.session_opened_ts'`,
   `/api/v9/woodies/chart?limit=1 | jq '.bars[-1] | {proj_hi, proj_lo}'`.
   Compare to user-claimed Sierra values.
3. **Page reload UAT.** Have the user reload, then have them describe
   what they see in their own words. Cross-check against the prior
   reports.
4. **If visual still broken** despite code claiming to be fixed: roll
   the suspect commit back and re-investigate from the browser side, not
   the test side.

## Files / reports / handoffs to read on context

Order of priority (read these first):

1. This handoff (you're reading it).
2. `/Users/michael/Downloads/mems26_web_git/CLAUDE.md` — the pre-LIVE protocol.
3. `/Users/michael/Downloads/mems26_web_git/.cursor/rules/mems26-pre-live-protocol.mdc` — detailed rules.
4. `docs/reports/PROMPT_P30_CHART_SYNC_AND_BRIDGE_CLEANUP.md` — last
   chart sync work.
5. `docs/reports/PROMPT_P30_WOODIES_SYSTEM_SLOW_HANDLER.md` — deadlock fix.
6. `docs/handoff/CC_FOLLOWUP_TPO_SUBGRAPH_INDICES.md` — deferred DLL work.
7. `docs/handoff/INVESTIGATE_TPO_VALUE_MISMATCH.md` — TPO investigation.
8. `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` — running TODO inbox.

## Hard constraints (inherited)

- `CLOUD_URL=http://localhost:8000` — NEVER push bridge to remote.
- LaunchAgent KeepAlive must stay conditional (`SuccessfulExit=false`).
- `V9_DISABLE_WATCHDOG=1` stays exported in the bridge LaunchAgent.
- No `git commit` without Michael's explicit OK.
- No service restart without Michael's explicit OK.
- No DLL changes (that's CC territory — write a handoff in `docs/handoff/`).
- No `*.pyc` / `__pycache__/` commits.

## Closing note from the prior agent

I shipped a lot of code today. Most of it is probably correct based on
tests + live curl metrics. None of it has been confirmed by the user in
their browser. **That's the gap.** The fix is to close that gap before
shipping anything else.

The user's frustration is fair. Take it seriously in the next chat.
